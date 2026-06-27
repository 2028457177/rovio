"""修复：上传 static 文件到后端目录 - 先处理权限"""
import paramiko
import os

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

BACKEND_DIR = "/opt/lc-course/backend"
LOCAL_STATIC = r"c:\Users\nxt\PycharmProjects\lc-course\static"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()

def sudo(cmd):
    full_cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if err.strip():
        print(f"  [ERR] {err.strip()}")
    return out

print("准备目录并设置权限...")
remote_static = f"{BACKEND_DIR}/static"

# 先确保整个 backend 目录归属正确
sudo(f"mkdir -p {remote_static}")
sudo(f"chown -R {USER}:{USER} {BACKEND_DIR}")

print("上传 static 到后端目录...")
for root, dirs, files in os.walk(LOCAL_STATIC):
    rel_path = os.path.relpath(root, LOCAL_STATIC)
    if rel_path == ".":
        remote_dir = remote_static
    else:
        remote_dir = f"{remote_static}/{rel_path.replace(os.sep, '/')}"
    
    # 创建远程子目录
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        sftp.mkdir(remote_dir)
    
    for fname in files:
        local_file = os.path.join(root, fname)
        remote_file = f"{remote_dir}/{fname}"
        try:
            sftp.put(local_file, remote_file)
            label = f"static/{rel_path}/{fname}" if rel_path != "." else f"static/{fname}"
            print(f"  [OK] {label}")
        except Exception as e:
            print(f"  [FAIL] {fname}: {e}")

# 重启服务
print("\n重启后端服务...")
sudo("systemctl restart lc-course")

import time
time.sleep(4)

stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
status = stdout.read().decode('utf-8', errors='replace').strip()
print(f"lc-course 状态: {status}")

# 快速检查日志有无报错
stdin, stdout, stderr = ssh.exec_command("echo '***REMOVED***' | sudo -S journalctl -u lc-course --no-pager -n 10", get_pty=True)
print("\n最近日志:")
print(stdout.read().decode('utf-8', errors='replace'))

sftp.close()
ssh.close()
print("完成！")
