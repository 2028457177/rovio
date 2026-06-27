"""JWT 认证模块"""
import os
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "lc-course-secret-key-2025")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 72

# 管理员 IP 白名单，逗号分隔，在服务器环境变量或此处配置
# 例如: "192.168.1.100,10.0.0.5"
ADMIN_ALLOWED_IPS = os.getenv("ADMIN_ALLOWED_IPS", "").split(",") if os.getenv("ADMIN_ALLOWED_IPS") else []

security = HTTPBearer(auto_error=False)


def get_client_ip(request: Request) -> str:
    """从请求中提取客户端真实 IP"""
    return (
        request.headers.get("X-Real-IP")
        or (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        or (request.client.host if request.client else None)
        or "unknown"
    )


def create_access_token(user_id: int, username: str, role: str = "user") -> str:
    """生成 JWT access token"""
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """从 JWT token 中解析当前用户，并验证用户是否仍存在于数据库"""
    token = None
    if credentials:
        token = credentials.credentials
    else:
        # 也支持从 query string 获取 token
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="未提供认证令牌")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="令牌已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的认证令牌")

    user_id = payload["user_id"]

    # 验证用户是否仍然存在于数据库（防止已注销用户继续使用 token）
    from AIRAGAgent.database import get_user_by_id as _db_get_user_by_id
    import asyncio
    loop = asyncio.get_event_loop()
    existing = await loop.run_in_executor(None, _db_get_user_by_id, user_id)
    if existing is None:
        raise HTTPException(status_code=401, detail="用户不存在或已被注销")

    return {"id": user_id, "username": payload["username"], "role": payload.get("role", "user")}


async def get_admin_user(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    """验证当前用户是管理员，并检查 IP 白名单；否则返回 403"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    if ADMIN_ALLOWED_IPS:
        client_ip = get_client_ip(request)
        if client_ip not in ADMIN_ALLOWED_IPS:
            raise HTTPException(status_code=403, detail="无权访问管理后台")
    return user
