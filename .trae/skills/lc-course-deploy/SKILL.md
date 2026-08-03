---
name: "lc-course-deploy"
description: "将 lc-course（自动化办公助手）项目部署或更新到远程服务器 81.70.100.57。支持全新部署和增量更新。当用户要求部署/上传/更新此项目到服务器时调用。"
---

# lc-course 项目部署

将 lc-course（自动化办公助手）Vue + FastAPI 项目一键部署到 Ubuntu 服务器（81.70.100.57）。

## 部署架构

微服务架构：6 个 FastAPI 进程 + nginx 按路径前缀路由。

| 组件 | 路径 | 端口 |
|------|------|------|
| 前端 (Vue SPA) | `/var/www/lc-course-frontend/` | nginx:80 |
| auth_service | `/opt/lc-course/backend/` | 8001 |
| user_service | `/opt/lc-course/backend/` | 8002 |
| chat_service | `/opt/lc-course/backend/` | 8003 |
| kb_service | `/opt/lc-course/backend/` | 8004 |
| admin_service | `/opt/lc-course/backend/` | 8005 |
| file_service | `/opt/lc-course/backend/` | 8006 |
| MySQL | 本地 | 3306 |
| API 代理 | nginx 按路径前缀路由 `/api/*` → 对应微服务 | - |

## 服务器信息

- IP: 81.70.100.57
- 用户: ubuntu
- 密码: 通过环境变量 `LC_SERVER_PASSWORD` 注入（勿硬编码）
- MySQL root 密码: 通过环境变量 `LC_MYSQL_PASSWORD` 注入（勿硬编码）
- 数据库: lc_auth / lc_user / lc_chat / lc_kb / lc_admin（5 个独立库）

---

## 部署步骤

### 第一步：打包项目

将前后端文件复制到 `deploy/dist/` 目录：

```powershell
# 创建输出目录
Remove-Item -Recurse -Force "deploy\dist" -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path "deploy\dist\backend" | Out-Null
New-Item -ItemType Directory -Force -Path "deploy\dist\frontend" | Out-Null

# 复制前端（已构建的 static 目录）
Copy-Item -Recurse "static\*" "deploy\dist\frontend\"

# 复制后端
Copy-Item -Recurse "AIRAGAgent" "deploy\dist\backend\"
Copy-Item -Recurse "services" "deploy\dist\backend\"
Copy-Item -Recurse "chroma_ab" "deploy\dist\backend\"
Copy-Item "pyproject.toml" "deploy\dist\backend\"
Copy-Item "uv.lock" "deploy\dist\backend\"
Copy-Item "langgraph.json" "deploy\dist\backend\"

# 清理缓存
Get-ChildItem -Recurse "deploy\dist\backend\AIRAGAgent" -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse "deploy\dist\backend\services" -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse "deploy\dist\backend\AIRAGAgent\logs" -File -Filter "*.log" | Remove-Item -Force -ErrorAction SilentlyContinue
```

### 第二步：上传文件到服务器

**注意：** Windows 环境下 SSH/SCP 不支持密码管道输入，使用 Python paramiko 通过 SFTP 上传。

Python 上传脚本核心逻辑：

```python
import paramiko
import os

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = os.environ["LC_SERVER_PASSWORD"]  # 运行前注入环境变量，勿硬编码

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()

# 创建远程目录并授权
def sudo_cmd(cmd):
    full_cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'"
    ssh.exec_command(full_cmd, get_pty=True)

# 前端目录
sudo_cmd("mkdir -p /var/www/lc-course-frontend")
sudo_cmd("chown -R ubuntu:ubuntu /var/www/lc-course-frontend")

# 后端目录
sudo_cmd("rm -rf /opt/lc-course/backend")
sudo_cmd("mkdir -p /opt/lc-course/backend")
sudo_cmd("chown -R ubuntu:ubuntu /opt/lc-course/backend")

# 递归上传文件（sftp.put）
# 前端: deploy/dist/frontend/* → /var/www/lc-course-frontend/
# 后端: deploy/dist/backend/* → /opt/lc-course/backend/
```

### 第三步：安装服务器环境

在服务器上执行：

```bash
# 1. 安装 nginx
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y nginx

# 2. 安装 MySQL
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server

# 3. 安装 Python pip + venv
sudo apt-get install -y python3-pip python3-venv
```

### 第四步：配置 Nginx

使用微服务版 nginx 配置（按路径前缀路由到 6 个微服务端口）。配置文件见项目内的 `deploy/nginx_microservices.conf`，将其部署到服务器：

```bash
# 部署主配置
sudo cp /opt/lc-course/backend/deploy/nginx_microservices.conf /etc/nginx/sites-available/lc-course

# 部署代理片段（SSE / 长连接 / 通用代理头）
sudo mkdir -p /etc/nginx/snippets
sudo cp /opt/lc-course/backend/deploy/microservice_proxy.conf /etc/nginx/snippets/microservice_proxy.conf

# 启用配置
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/lc-course /etc/nginx/sites-enabled/lc-course
sudo nginx -t
sudo systemctl restart nginx
```

### 第五步：配置 MySQL

```bash
# 设置 root 密码
sudo mysql -e "ALTER USER root@localhost IDENTIFIED VIA mysql_native_password USING PASSWORD('<MYSQL_ROOT_PASSWORD>'); FLUSH PRIVILEGES;"

# 创建 5 个独立数据库（微服务各自独立库）
sudo mysql -e "CREATE DATABASE IF NOT EXISTS lc_auth CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE DATABASE IF NOT EXISTS lc_user CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE DATABASE IF NOT EXISTS lc_chat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE DATABASE IF NOT EXISTS lc_kb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
sudo mysql -e "CREATE DATABASE IF NOT EXISTS lc_admin CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 首次部署：从旧 agent_records 库拆分数据到 5 个独立库
cd /opt/lc-course/backend
.venv/bin/python services/migrate_to_microservices.py
```

### 第六步：安装 Python 依赖

```bash
cd /opt/lc-course/backend

# 创建虚拟环境
python3 -m venv .venv

# 安装依赖
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install coloredlogs chromadb dashscope fastapi "uvicorn[standard]" -q
.venv/bin/pip install langchain langchain-chroma langchain-community langchain-deepseek langchain-ollama -q
.venv/bin/pip install langchain-tavily langgraph langgraph-cli numpy pandas -q
.venv/bin/pip install pymysql python-docx python-dotenv streamlit openpyxl -q
.venv/bin/pip install redis hiredis prompt-toolkit -q
```

### 第七步：创建 systemd 服务

为每个微服务创建独立的 systemd unit（或用 start_microservices.sh 脚本管理）。以下是批量创建 6 个服务的示例：

```bash
SERVICES=("auth:8001" "user:8002" "chat:8003" "kb:8004" "admin:8005" "file:8006")
for entry in "${SERVICES[@]}"; do
  name="${entry%%:*}"
  port="${entry##*:}"
  cat > /tmp/lc-course-${name}.service << EOF
[Unit]
Description=lc-course ${name}_service
After=network.target mysql.service redis.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/lc-course/backend
EnvironmentFile=/opt/lc-course/backend/deploy/backend/.env
ExecStart=/opt/lc-course/backend/.venv/bin/python -m uvicorn services.${name}_service.main:app --host 0.0.0.0 --port ${port} --log-level info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
  sudo cp /tmp/lc-course-${name}.service /etc/systemd/system/
done

sudo systemctl daemon-reload
for entry in "${SERVICES[@]}"; do
  name="${entry%%:*}"
  sudo systemctl enable lc-course-${name}
  sudo systemctl start lc-course-${name}
done
```

### 第八步：防火墙与验证

```bash
# 开放端口（前端 80，微服务端口仅内部访问无需开放）
sudo ufw allow 80/tcp

# 验证
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/           # 前端，期望 200
curl -s http://127.0.0.1/api/health                                  # API，期望 status=ok
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8003/api/health  # chat_service，期望 200
```

---

---

## 增量更新（修改代码后快速上传）

当只修改了部分源码文件，不需要走完整部署流程。根据修改类型选择对应操作：

### 判断修改类型

| 修改了什么 | 需要做什么 |
|-----------|-----------|
| 只改 Python 后端代码 | 上传改动文件 → 重启对应微服务 |
| 只改前端代码 (Vue) | 本地构建 → 上传 static/ → nginx 重载 |
| 新增了 Python 依赖包 | 上传改动文件 → 安装新依赖 → 重启对应微服务 |
| 改了 config/*.yml 配置 | 上传配置 → 重启 chat_service / kb_service |
| 改了 nginx 配置 | 上传配置 → nginx -t → nginx 重载 |

### 通用增量更新脚本

用一个 Python 脚本完成"上传指定文件 → 重启服务"：

```python
import paramiko
import os

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = os.environ["LC_SERVER_PASSWORD"]  # 运行前注入环境变量，勿硬编码
BACKEND_DIR = "/opt/lc-course/backend"
FRONTEND_DIR = "/var/www/lc-course-frontend"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()

def sudo(cmd):
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'", get_pty=True)

# ==== 上传后端文件 ====
# 示例：上传改动的 Python 文件
sftp.put("AIRAGAgent/agent/supervisor_agent.py", f"{BACKEND_DIR}/AIRAGAgent/agent/supervisor_agent.py")
sftp.put("services/chat_service/main.py", f"{BACKEND_DIR}/services/chat_service/main.py")

# 如果新增了依赖包
# ssh.exec_command(f"cd {BACKEND_DIR} && .venv/bin/pip install 新包名", get_pty=True)

# ==== 上传前端文件 ====
# 如果改了前端且已完成构建
# for f in os.listdir("static"):
#     sftp.put(f"static/{f}", f"{FRONTEND_DIR}/{f}")

# ==== 上传配置文件 ====
# sftp.put("AIRAGAgent/config/rag.yml", f"{BACKEND_DIR}/AIRAGAgent/config/rag.yml")

# ==== 重启受影响的微服务 ====
sudo("systemctl restart lc-course-chat")   # 改了 agent/chat 相关
# sudo("systemctl restart lc-course-kb")   # 改了 kb 相关
# sudo("systemctl restart lc-course-auth") # 改了 auth 相关
print("Backend restarted")

# 可选：重载 nginx
# sudo("nginx -t && nginx -s reload")
```

### 无需重启的情况

以下更改**不需要**重启服务：
- 修改静态资源文件（图片、CSS、JS）→ nginx 直接服务，无需重启
- 修改前端 `static/` 目录 → 只需上传覆盖即可

### 上传根目录文件（非 AIRAGAgent 内）

如果改了 `pyproject.toml`、`uv.lock`、`langgraph.json` 等根目录文件：
```python
sftp.put("pyproject.toml", f"{BACKEND_DIR}/pyproject.toml")
# 如果改了依赖，需要重新安装
ssh.exec_command(f"cd {BACKEND_DIR} && .venv/bin/pip install -r requirements.txt 或逐个安装", get_pty=True)
sudo("systemctl restart lc-course-chat lc-course-kb")
```

---

## 关键注意事项

1. **API Key 配置在 `AIRAGAgent/config/rag.yml`**，不在 `.env` 环境变量中
   - `api_key`: DeepSeek API Key
   - `gaode_api_key`: 高德地图 API Key

2. **服务器 Python 版本 3.12**，项目要求 `>=3.13`，但 3.12 可正常运行

3. **`pip install -e .` 不可用**（缺少 setuptools 构建配置），需要逐个 `pip install` 包

4. **Ollama 未在服务器安装**，本地模型预热会跳过，远程模型（DeepSeek）正常工作

5. **MySQL 认证方式**需要从默认的 `auth_socket` 改为 `mysql_native_password`

6. **端口 80 冲突**：服务器可能已有其他 http 服务占用 80 端口，使用 `sudo fuser -k 80/tcp` 释放

7. **Windows SSH 限制**：无法通过管道传递密码，必须使用 Python paramiko 库进行远程操作

8. **微服务环境变量**：`deploy/backend/.env`（从 `.env.microservices.example` 复制），含 5 个数据库名、6 个端口、JWT 共享密钥

---

## 常用管理命令

```bash
# 微服务（以 chat_service 为例，其余同理：auth/user/kb/admin/file）
sudo systemctl status lc-course-chat       # 查看状态
sudo systemctl restart lc-course-chat      # 重启
sudo journalctl -u lc-course-chat -f       # 查看日志

# 一次性重启全部微服务
for svc in auth user chat kb admin file; do
  sudo systemctl restart lc-course-$svc
done

# Nginx
sudo systemctl status nginx
sudo nginx -t && sudo nginx -s reload    # 重载配置

# MySQL
mysql -u root -p               # 登录（回车后输入密码，勿写在命令行）
```

## 部署脚本

项目中有现成的部署辅助脚本（使用 Python paramiko）：

- `deploy/deploy_to_server.py` — 打包 + 上传文件
- `deploy/fix_mysql.py` — 修复 MySQL 权限和 nginx 端口
- `deploy/verify.py` — 验证部署状态
