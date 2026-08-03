---
name: "lc-course-local-run"
description: "本地启动 lc-course 项目进行开发调试：前端 Vite(5173) + 6 个微服务(8001-8006) + nginx 路由。当用户要求本地运行/跑一下/启动项目时调用。"
---

# lc-course 本地启动

在本地把 lc-course（自动化办公助手）跑起来用于开发调试。项目根目录 `c:\Users\nxt\Desktop\lc-course`，Windows + PowerShell 环境。

## 架构概览

项目已升级为微服务架构：6 个独立 FastAPI 进程 + nginx 按路径前缀路由。

| 组件 | 路径 | 端口 |
|------|------|------|
| 前端 (Vue3 + Vite) | `frontend/` | 5173，`/api/*` 代理到 nginx 或生产 |
| auth_service | `services/auth_service/main.py` | 8001（认证/登录设备/密保） |
| user_service | `services/user_service/main.py` | 8002（资料/头像/课表） |
| chat_service | `services/chat_service/main.py` | 8003（聊天/会话/Agent） |
| kb_service | `services/kb_service/main.py` | 8004（知识库） |
| admin_service | `services/admin_service/main.py` | 8005（管理员/看板） |
| file_service | `services/file_service/main.py` | 8006（文件上传下载） |

- **微服务**：每个服务独立数据库（lc_auth / lc_user / lc_chat / lc_kb / lc_admin），通过 HTTP+JWT 互调，事件统计走 Redis Pub/Sub。
- **chat_service / kb_service** 仍复用 `AIRAGAgent/` 内的 agent / rag / kb / infrastructure 核心逻辑（通过 db_patch 重定向数据库）。
- **本地路由**：前端 `/api/*` 需经 nginx 按 URL 前缀分发到各微服务端口；若无本地 nginx，可将 `VITE_API_TARGET` 指向生产 `http://81.70.100.57`。

---

## 第一步：前置依赖检查

启动前先确认依赖就绪（任一缺失会导致微服务起不来或功能异常）：

```powershell
# 1. MySQL 服务需 Running（5 个独立库：lc_auth/lc_user/lc_chat/lc_kb/lc_admin，配置在 deploy/backend/.env）
Get-Service -Name mysql* | Select-Object Name, Status

# 2. Ollama 需在 11434 监听，且已装 qwen3:4b + nomic-embed-text（chat_service 推理用）
$ol = Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue
if ($ol) { (Invoke-RestMethod "http://localhost:11434/api/tags").models | ForEach-Object { $_.name } } else { "Ollama 未运行" }

# 3. ChromaDB 持久化目录需存在（kb_service 向量库）
Test-Path "c:\Users\nxt\Desktop\lc-course\chroma_ab\chroma.sqlite3"

# 4. Python venv 存在（uv 管理，无 pip，装包用 uv pip install）
Test-Path "c:\Users\nxt\Desktop\lc-course\.venv\Scripts\python.exe"

# 5. 端口 8001-8006 空闲（6 个微服务）
Get-NetTCPConnection -LocalPort 8001,8002,8003,8004,8005,8006 -State Listen -ErrorAction SilentlyContinue
```

**说明：**
- Redis 可选，未启动时代码优雅降级（`is_redis_available()` 检查），不影响启动；但事件统计（Redis Pub/Sub）会降级。
- `.venv` 是 uv 管理的虚拟环境，**没有 pip**，缺包时用 `uv pip install <package>`（在项目根目录执行），切勿用 `pip`。
- 已知必装包：`python-multipart`（FastAPI 文件上传路由需要，缺失会启动报错 `Form data requires python-multipart`）。
- 首次运行需执行 `python services/migrate_to_microservices.py` 把原 `agent_records` 库拆分为 5 个独立库。

---

## 第二步：启动微服务后端

> 用一键启动脚本拉起 6 个微服务进程，各自绑定独立端口 8001-8006。

### 方案 A：启动全部微服务（默认，需要完整功能）

```powershell
$env:PYTHONPATH = "c:\Users\nxt\Desktop\lc-course"
& "c:\Users\nxt\Desktop\lc-course\deploy\backend\start_microservices.bat"
```

脚本会启动 6 个服务（各开一个新窗口）：auth(8001) / user(8002) / chat(8003) / kb(8004) / admin(8005) / file(8006)。

**关键点：**
- 用 **`run_in_background: true`** 后台运行（服务常驻），输出写到日志文件，需要时用 `Read` 读取。
- **启动成功标志**：每个窗口出现 `Uvicorn running on http://0.0.0.0:<port>` 且 `Application startup complete.`；chat_service 会打印「[SkillRegistry] 注册 skill: ...」共 7 个 Skill。
- 若 chat_service 崩溃（chromadb 原生扩展偶发 `0xC0000005`），单独重启该窗口即可。
- **停止全部微服务**（Linux）：`bash deploy/backend/stop_microservices.sh`；（Windows）关闭对应窗口即可。

### 方案 B：直连生产后端（仅调前端 UI）

无需启动本地微服务，让 Vite 直接代理到生产环境：

```powershell
$env:VITE_API_TARGET = "http://81.70.100.57"
cd c:\Users\nxt\Desktop\lc-course\frontend; npm run dev
```

---

## 第三步：启动前端

```powershell
npm run dev   # cwd 必须是 c:\Users\nxt\Desktop\lc-course\frontend
```

后台运行。启动成功标志：`Local: http://localhost:5173/`。

**端口占用处理**：若 5173 被旧 dev server 残留占用，Vite 会自动改用 5174，但旧进程跑的是旧代码会造成混淆。应先杀掉占用 5173 的旧 node 进程再重启：

```powershell
Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

---

## 第四步：验证

```powershell
# 1. 前端代理到后端的健康检查（应返回 status=ok）
Invoke-RestMethod -Uri "http://localhost:5173/api/health" | ConvertTo-Json -Compress
# 微服务: {"status":"ok","service":"auth_service",...}

# 2. 6 个微服务端口都在监听
Get-NetTCPConnection -LocalPort 8001,8002,8003,8004,8005,8006 -State Listen | Select-Object LocalPort, OwningProcess
```

**真实对话冒烟测试**（可选）：浏览器打开 http://localhost:5173，用已有测试账号 `localtest_51461` / `test123456` 登录（或自行注册），发一条消息。chat_service 首条回复约 10-20s（含 Ollama 模型加载），之后会快很多。

> 注意：本地无 nginx 时前端 `/api/*` 无法自动分发到各微服务端口。需配合 `deploy/nginx_microservices.conf` 部署本地 nginx，或用方案 B 直连生产。

---

## 停止服务

后台任务用 `StopCommand`（传 command_id）停止。若要按端口清理残留进程：

```powershell
foreach ($port in 5173,8001,8002,8003,8004,8005,8006) {
  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}
```

---

## 常见坑

| 现象 | 原因 / 解决 |
|------|------------|
| 微服务启动报 `Form data requires python-multipart` | `.venv` 缺包。`uv pip install python-multipart`（项目根目录执行） |
| 端口被占用 `bind on ('0.0.0.0', 800X)` | 查 PID：`Get-NetTCPConnection -LocalPort 800X -State Listen`，`Stop-Process -Id <pid> -Force` 后重启 |
| chat_service 崩溃 `process crashed; code=3221225477` | chromadb 原生扩展偶发崩溃。单独重启 chat_service 即可 |
| 用 `pip install` 报 `No module named pip` | `.venv` 是 uv 管理的，没有 pip。改用 `uv pip install <package>` |
| 前端打开是旧代码 / Vite 跑在 5174 | 5173 被旧 dev server 占用。杀掉旧进程后重启前端，让它占用标准端口 5173 |
| chat_service 对话回复「特殊符号 / 无法理解」 | agent 系统提示词定位为办公助手，对纯闲聊回复偏工具向，属正常表现，非 bug |
| Redis 相关告警 | Redis 未启动，代码优雅降级，可忽略；如需事件统计启用 Redis 服务即可 |

---

## 关键路径速查

- 项目根：`c:\Users\nxt\Desktop\lc-course`
- 微服务入口：`services/<service>_service/main.py`（6 个，端口 8001-8006）
- 一键启动脚本：`deploy/backend/start_microservices.bat`（Windows）/ `start_microservices.sh`（Linux）
- 微服务环境变量：`deploy/backend/.env`（从 `.env.microservices.example` 复制）
- Nginx 微服务路由配置：`deploy/nginx_microservices.conf`
- 后端配置：`AIRAGAgent/config/rag.yml`（DeepSeek/高德/Tavily key）、`AIRAGAgent/config/mysql.yml`
- 向量库：`chroma_ab/`
- 前端代理配置：`frontend/vite.config.js`（`/api` → `VITE_API_TARGET`，默认 `http://localhost:8000`）
