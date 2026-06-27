"""
测试管理员 API
"""
import paramiko

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

# 1. 先登录获取 token
print("=== 登录获取 token ===")
stdin, stdout, stderr = ssh.exec_command(
    """curl -s -X POST http://127.0.0.1/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'""",
    get_pty=True
)
login_resp = stdout.read().decode()
print(login_resp[:300])

# 检查是否有普通用户，尝试注册一个
print("\n=== 注册一个测试用户 ===")
stdin, stdout, stderr = ssh.exec_command(
    """curl -s -X POST http://127.0.0.1/api/auth/register -H 'Content-Type: application/json' -d '{"username":"testuser","password":"123456","display_name":"测试用户"}'""",
    get_pty=True
)
reg_resp = stdout.read().decode()
print(reg_resp[:300])

# 2. 用 admin token 调 admin API
import json
try:
    login_data = json.loads(login_resp)
    token = login_data.get("token", "")
    print(f"\nToken: {token[:50]}...")
    
    # 测试 admin users API
    print("\n=== 测试 /api/admin/users ===")
    stdin, stdout, stderr = ssh.exec_command(
        f"""curl -s http://127.0.0.1/api/admin/users -H 'Authorization: Bearer {token}'""",
        get_pty=True
    )
    users_resp = stdout.read().decode()
    print(users_resp[:500])
    
    # 测试获取某个用户的对话
    print("\n=== 测试 /api/admin/users/1/conversations ===")
    stdin, stdout, stderr = ssh.exec_command(
        f"""curl -s http://127.0.0.1/api/admin/users/1/conversations -H 'Authorization: Bearer {token}'""",
        get_pty=True
    )
    conv_resp = stdout.read().decode()
    print(conv_resp[:500])
    
except Exception as e:
    print(f"解析失败: {e}")

ssh.close()
