"""
上传管理员功能 v2（注销+重置密码）
"""
import paramiko
import os
import time

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
BACKEND_DIR = "/opt/lc-course/backend"
FRONTEND_DIR = "/var/www/lc-course-frontend"
PROJECT_ROOT = r"c:\Users\nxt\PycharmProjects\lc-course"

BACKEND_FILES = [
    "AIRAGAgent/database/__init__.py",
    "AIRAGAgent/database/models.py",
    "AIRAGAgent/fastapi_app/main.py",
]

print("=" * 60)
print("  上传管理员功能 v2")
print("=" * 60)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()

def sudo(cmd):
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'", get_pty=True)

# 上传后端
print("\n[1/2] 上传后端...")
for rel_path in BACKEND_FILES:
    local_path = os.path.join(PROJECT_ROOT, rel_path)
    remote_path = f"{BACKEND_DIR}/{rel_path}"
    sftp.put(local_path, remote_path)
    print(f"  [OK] {rel_path}")

# 上传前端
print("\n[2/2] 上传前端...")
sudo(f"rm -rf {FRONTEND_DIR}/*")
sudo(f"mkdir -p {FRONTEND_DIR}")
sudo(f"chown -R {USER}:{USER} {FRONTEND_DIR}")

STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
for root, dirs, files in os.walk(STATIC_DIR):
    rel = os.path.relpath(root, STATIC_DIR)
    remote_dir = FRONTEND_DIR if rel == "." else f"{FRONTEND_DIR}/{rel.replace(os.sep, '/')}"
    if rel != ".":
        sudo(f"mkdir -p {remote_dir}")
        sudo(f"chown -R {USER}:{USER} {remote_dir}")
    for fname in files:
        sftp.put(os.path.join(root, fname), f"{remote_dir}/{fname}")
        print(f"  [OK] {rel}/{fname}")

sftp.close()

# 重启
print("\n重启服务...")
sudo("systemctl restart lc-course")
time.sleep(3)

stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
print(f"状态: {stdout.read().decode().strip()}")

# 验证 API
import json
stdin, stdout, stderr = ssh.exec_command(
    """curl -s -X POST http://127.0.0.1/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'""",
    get_pty=True
)
token = json.loads(stdout.read().decode())["token"]

# 用户列表
stdin, stdout, stderr = ssh.exec_command(
    f"""curl -s http://127.0.0.1/api/admin/users -H 'Authorization: Bearer {token}'""",
    get_pty=True
)
data = json.loads(stdout.read().decode())
print(f"\n用户数: {len(data['users'])}")

# 前端
stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/", get_pty=True)
print(f"前端: {stdout.read().decode().strip()}")

ssh.close()
print("\n部署完成!")
