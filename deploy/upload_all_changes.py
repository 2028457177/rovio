"""
全量增量上传：上传所有修改的后端文件、前端构建产物，然后重启服务
"""
import paramiko
import os

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

BACKEND_DIR = "/opt/lc-course/backend"
FRONTEND_DIR = "/var/www/lc-course-frontend"
PROJECT_ROOT = r"c:\Users\nxt\PycharmProjects\lc-course"

# 所有修改的后端文件（相对于项目根目录）
BACKEND_FILES = [
    # agent
    "AIRAGAgent/agent/react_agent.py",
    "AIRAGAgent/agent/supervisor_agent.py",
    "AIRAGAgent/agent/tools/agent_tools.py",
    "AIRAGAgent/agent/tools/file_tools.py",
    "AIRAGAgent/agent/tools/middleware.py",
    "AIRAGAgent/agent/tools/search_tools.py",
    # app
    "AIRAGAgent/app.py",
    # config
    "AIRAGAgent/config/rag.yml",
    # database
    "AIRAGAgent/database/__init__.py",
    "AIRAGAgent/database/connection.py",
    "AIRAGAgent/database/models.py",
    # fastapi
    "AIRAGAgent/fastapi_app/main.py",
    "AIRAGAgent/fastapi_app/auth.py",
    "AIRAGAgent/fastapi_app/services/agent_service.py",
    # infrastructure
    "AIRAGAgent/infrastructure/session_cache.py",
    # model
    "AIRAGAgent/model/factory.py",
    # prompts
    "AIRAGAgent/prompts/identity_prompt.txt",
    "AIRAGAgent/prompts/main_prompt.txt",
    "AIRAGAgent/prompts/report_prompt.txt",
    "AIRAGAgent/prompts/tools_prompt.txt",
    # rag
    "AIRAGAgent/rag/rag_service.py",
    "AIRAGAgent/rag/vector_store.py",
    # skills
    "AIRAGAgent/skills/definitions.py",
    # utils
    "AIRAGAgent/utils/path_tool.py",
    # chroma
    "chroma_ab/chroma.sqlite3",
    # root files
    "pyproject.toml",
    "uv.lock",
    ".gitignore",
    # agent avatar (root level)
    "agent头像.jpg",
]

# 需要在服务器上删除的文件（本地已删除的）
DELETE_ON_SERVER = [
    "AIRAGAgent/model/local_factory.py",
]

STATIC_DIR = os.path.join(PROJECT_ROOT, "static")

print("=" * 60)
print("  全量增量上传 lc-course 到服务器")
print("=" * 60)

# 1. 连接服务器
print("\n[1/4] 连接服务器...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()
print("[OK] SSH 连接成功")

def sudo(cmd):
    full_cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if err.strip():
        print(f"    [ERR] {err.strip()}")
    return out

# 2. 上传后端文件
print("\n[2/4] 上传后端文件...")
success_count = 0
fail_count = 0

for rel_path in BACKEND_FILES:
    local_path = os.path.join(PROJECT_ROOT, rel_path)
    remote_path = f"{BACKEND_DIR}/{rel_path}"

    if not os.path.exists(local_path):
        print(f"  [SKIP] 文件不存在: {rel_path}")
        continue

    file_size = os.path.getsize(local_path)
    print(f"  上传 {rel_path} ({file_size/1024:.1f}KB)...")

    # 确保远程目录存在
    remote_parent = os.path.dirname(remote_path).replace("\\", "/")
    try:
        sftp.stat(remote_parent)
    except FileNotFoundError:
        sudo(f"mkdir -p {remote_parent}")
        sudo(f"chown -R {USER}:{USER} {remote_parent}")

    try:
        sftp.put(local_path, remote_path)
        print(f"    [OK]")
        success_count += 1
    except Exception as e:
        print(f"    [FAIL] {e}")
        fail_count += 1

# 删除服务器上不再需要的文件
print("\n  清理已删除的文件...")
for rel_path in DELETE_ON_SERVER:
    remote_path = f"{BACKEND_DIR}/{rel_path}"
    try:
        sftp.stat(remote_path)
        sudo(f"rm -f {remote_path}")
        print(f"  [DELETED] {rel_path}")
    except FileNotFoundError:
        print(f"  [SKIP] 服务器上不存在: {rel_path}")

# 3. 上传前端文件
print(f"\n[3/4] 上传前端文件...")

# 先清理前端目录
sudo(f"rm -rf {FRONTEND_DIR}/*")
sudo(f"mkdir -p {FRONTEND_DIR}")
sudo(f"chown -R {USER}:{USER} {FRONTEND_DIR}")

for root, dirs, files in os.walk(STATIC_DIR):
    rel = os.path.relpath(root, STATIC_DIR)
    if rel == ".":
        remote_dir = FRONTEND_DIR
    else:
        remote_dir = f"{FRONTEND_DIR}/{rel.replace(os.sep, '/')}"
        sudo(f"mkdir -p {remote_dir}")
        sudo(f"chown -R {USER}:{USER} {remote_dir}")

    for fname in files:
        local_file = os.path.join(root, fname)
        remote_file = f"{remote_dir}/{fname}"
        file_size = os.path.getsize(local_file)
        print(f"  上传 {rel}/{fname} ({file_size/1024:.1f}KB)...")
        try:
            sftp.put(local_file, remote_file)
            print(f"    [OK]")
        except Exception as e:
            print(f"    [FAIL] {e}")

sftp.close()

print(f"\n  后端文件: 成功 {success_count}, 失败 {fail_count}")

# 4. 重启服务
print("\n[4/4] 重启后端服务...")
sudo("systemctl restart lc-course")

import time
time.sleep(3)

# 5. 验证
print("\n验证服务状态...")
stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
status = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  lc-course: {status}")

# 测试 API
stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/", get_pty=True)
http_code = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  前端 HTTP: {http_code}")

stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/", get_pty=True)
http_code = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  后端 HTTP: {http_code}")

ssh.close()

print("\n" + "=" * 60)
print("  上传完成！")
print(f"  访问: http://{HOST}/")
print("=" * 60)
