"""
增量上传：上传改动的文件并重启后端服务
"""
import paramiko
import os
import sys

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

BACKEND_DIR = "/opt/lc-course/backend"
FRONTEND_DIR = "/var/www/lc-course-frontend"
PROJECT_ROOT = r"c:\Users\nxt\PycharmProjects\lc-course"

# 修改的文件列表（根据 git status）
BACKEND_FILES = [
    "AIRAGAgent/agent/tools/agent_tools.py",
]

# 前端 static 目录
STATIC_DIR = "static"

print("=" * 50)
print("  增量上传 lc-course 到服务器")
print("=" * 50)

# 1. 连接
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
        print(f"  [ERR] {err.strip()}")
    return out

# 2. 上传后端文件
print("\n[2/3] 上传后端文件...")
for rel_path in BACKEND_FILES:
    local_path = os.path.join(PROJECT_ROOT, rel_path)
    remote_path = f"{BACKEND_DIR}/{rel_path}"
    
    if not os.path.exists(local_path):
        print(f"  [SKIP] 文件不存在: {local_path}")
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
    except Exception as e:
        print(f"    [FAIL] {e}")

# 3. 重启后端服务
print("\n重启后端服务...")
sudo("systemctl restart lc-course")
print("[OK] lc-course 服务已重启")

# 5. 验证
print("\n验证服务状态...")
stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
status = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  lc-course 状态: {status}")

sftp.close()
ssh.close()

print("\n" + "=" * 50)
print("  增量上传完成！")
print("=" * 50)
