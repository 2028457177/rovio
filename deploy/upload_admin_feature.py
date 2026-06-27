"""
上传管理员功能改动到服务器
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

# 本次改动的后端文件
BACKEND_FILES = [
    "AIRAGAgent/database/connection.py",
    "AIRAGAgent/database/models.py",
    "AIRAGAgent/fastapi_app/auth.py",
    "AIRAGAgent/fastapi_app/main.py",
]

STATIC_DIR = os.path.join(PROJECT_ROOT, "static")

print("=" * 60)
print("  上传管理员功能到服务器")
print("=" * 60)

# 1. 连接服务器
print("\n[1/3] 连接服务器...")
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
print("\n[2/3] 上传后端文件...")
for rel_path in BACKEND_FILES:
    local_path = os.path.join(PROJECT_ROOT, rel_path)
    remote_path = f"{BACKEND_DIR}/{rel_path}"

    if not os.path.exists(local_path):
        print(f"  [SKIP] 文件不存在: {rel_path}")
        continue

    file_size = os.path.getsize(local_path)
    print(f"  上传 {rel_path} ({file_size / 1024:.1f}KB)...")

    try:
        sftp.put(local_path, remote_path)
        print(f"    [OK]")
    except Exception as e:
        print(f"    [FAIL] {e}")

# 3. 上传前端 static 文件
print(f"\n[3/3] 上传前端文件...")

# 清理并重建前端目录
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
        print(f"  上传 {rel}/{fname} ({file_size / 1024:.1f}KB)...")
        try:
            sftp.put(local_file, remote_file)
        except Exception as e:
            print(f"    [FAIL] {e}")

sftp.close()

# 4. 重启后端服务
print("\n重启后端服务...")
sudo("systemctl restart lc-course")
print("  等待服务启动...")
time.sleep(3)

# 5. 验证
print("\n验证服务状态...")
stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
status = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  lc-course 状态: {status}")

# 测试前端
stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/", get_pty=True)
http_code = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  前端 HTTP 状态码: {http_code}")

# 测试后端 API
stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/", get_pty=True)
http_code = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  后端 HTTP 状态码: {http_code}")

# 测试 admin API
stdin, stdout, stderr = ssh.exec_command(
    """curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/api/health""",
    get_pty=True
)
health_code = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  Health API 状态码: {health_code}")

ssh.close()

print("\n" + "=" * 60)
print("  部署完成！")
print(f"  访问地址: http://{HOST}/")
print(f"  管理员账号: admin / admin123")
print("=" * 60)
