---
name: "lc-course-deploy"
description: "将 lc-course（自动化办公助手）项目部署或更新到远程服务器 81.70.100.57。支持全新部署和增量更新。当用户要求部署/上传/更新此项目到服务器时调用。"
---

# lc-course 项目部署

将 lc-course（自动化办公助手）Vue + FastAPI 项目一键部署到 Ubuntu 服务器（81.70.100.57）。

## 部署架构

| 组件 | 路径 | 端口 |
|------|------|------|
| 前端 (Vue SPA) | `/var/www/lc-course-frontend/` | nginx:80 |
| 后端 (FastAPI) | `/opt/lc-course/backend/` | uvicorn:8000 |
| MySQL | 本地 | 3306 |
| API 代理 | nginx `/api/*` → `127.0.0.1:8000` | - |

## 服务器信息

- IP: 81.70.100.57
- 用户: ubuntu
- 密码: ***REMOVED***
- MySQL root 密码: ***REMOVED***
- 数据库: agent_records

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
Copy-Item -Recurse "chroma_ab" "deploy\dist\backend\"
Copy-Item "pyproject.toml" "deploy\dist\backend\"
Copy-Item "uv.lock" "deploy\dist\backend\"
Copy-Item "langgraph.json" "deploy\dist\backend\"

# 清理缓存
Get-ChildItem -Recurse "deploy\dist\backend\AIRAGAgent" -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse "deploy\dist\backend\AIRAGAgent\logs" -File -Filter "*.log" | Remove-Item -Force -ErrorAction SilentlyContinue
```

### 第二步：上传文件到服务器

**注意：** Windows 环境下 SSH/SCP 不支持密码管道输入，使用 Python paramiko 通过 SFTP 上传。

Python 上传脚本核心逻辑：

```python
import paramiko

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

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

创建 `/etc/nginx/sites-available/lc-course`：

```nginx
server {
    listen 80;
    server_name 81.70.100.57;

    root /var/www/lc-course-frontend;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;
    gzip_min_length 1024;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /assets/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
        chunked_transfer_encoding on;
    }
}
```

启用配置：

```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/lc-course /etc/nginx/sites-enabled/lc-course
sudo nginx -t
sudo systemctl restart nginx
```

### 第五步：配置 MySQL

```bash
# 设置 root 密码
sudo mysql -e "ALTER USER root@localhost IDENTIFIED VIA mysql_native_password USING PASSWORD('***REMOVED***'); FLUSH PRIVILEGES;"

# 创建数据库
sudo mysql -e "CREATE DATABASE IF NOT EXISTS agent_records CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
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

创建 `/etc/systemd/system/lc-course.service`：

```ini
[Unit]
Description=lc-course Backend Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/lc-course/backend
ExecStart=/opt/lc-course/backend/.venv/bin/python -m uvicorn AIRAGAgent.fastapi_app.main:app --host 0.0.0.0 --port 8000 --log-level info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable lc-course
sudo systemctl start lc-course
```

### 第八步：防火墙与验证

```bash
# 开放端口
sudo ufw allow 80/tcp
sudo ufw allow 8000/tcp

# 验证
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/        # 前端，期望 200
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/   # 后端，期望 200
curl -s http://127.0.0.1/api/conversations                       # API，期望 "[]"
```

---

---

## 增量更新（修改代码后快速上传）

当只修改了部分源码文件，不需要走完整部署流程。根据修改类型选择对应操作：

### 判断修改类型

| 修改了什么 | 需要做什么 |
|-----------|-----------|
| 只改 Python 后端代码 | 上传改动文件 → 重启 lc-course |
| 只改前端代码 (Vue) | 本地构建 → 上传 static/ → nginx 重载 |
| 新增了 Python 依赖包 | 上传改动文件 → 安装新依赖 → 重启 lc-course |
| 改了 config/*.yml 配置 | 上传配置 → 重启 lc-course |
| 改了 nginx 配置 | 上传配置 → nginx -t → nginx 重载 |

### 通用增量更新脚本

用一个 Python 脚本完成"上传指定文件 → 重启服务"：

```python
import paramiko

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
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
sftp.put("AIRAGAgent/fastapi_app/main.py", f"{BACKEND_DIR}/AIRAGAgent/fastapi_app/main.py")
sftp.put("AIRAGAgent/agent/supervisor_agent.py", f"{BACKEND_DIR}/AIRAGAgent/agent/supervisor_agent.py")

# 如果新增了依赖包
# ssh.exec_command(f"cd {BACKEND_DIR} && .venv/bin/pip install 新包名", get_pty=True)

# ==== 上传前端文件 ====
# 如果改了前端且已完成构建
# for f in os.listdir("static"):
#     sftp.put(f"static/{f}", f"{FRONTEND_DIR}/{f}")

# ==== 上传配置文件 ====
# sftp.put("AIRAGAgent/config/rag.yml", f"{BACKEND_DIR}/AIRAGAgent/config/rag.yml")

# ==== 重启服务 ====
sudo("systemctl restart lc-course")
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
sudo("systemctl restart lc-course")
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

---

## 常用管理命令

```bash
# 后端服务
sudo systemctl status lc-course          # 查看状态
sudo systemctl restart lc-course         # 重启
sudo journalctl -u lc-course -f          # 查看日志

# Nginx
sudo systemctl status nginx
sudo nginx -t && sudo nginx -s reload    # 重载配置

# MySQL
mysql -u root -p***REMOVED***               # 登录
```

## 部署脚本

项目中有现成的部署辅助脚本（使用 Python paramiko）：

- `deploy/deploy_to_server.py` — 打包 + 上传文件
- `deploy/setup_server.py` — 安装环境（nginx、pip、venv、systemd）
- `deploy/fix_mysql.py` — 修复 MySQL 权限和 nginx 端口
- `deploy/verify.py` — 验证部署状态
