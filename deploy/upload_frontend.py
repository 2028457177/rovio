"""增量上传前端文件到服务器"""
import paramiko
import os

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
FRONTEND_DIR = "/var/www/lc-course-frontend"
LOCAL_STATIC = os.path.join(os.path.dirname(__file__), "..", "static")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()

def sudo(cmd):
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'", get_pty=True)

# 确保前端目录权限正确
sudo(f"chown -R ubuntu:ubuntu {FRONTEND_DIR}")

# 上传所有静态文件
for root, dirs, files in os.walk(LOCAL_STATIC):
    for f in files:
        local_path = os.path.join(root, f)
        rel_path = os.path.relpath(local_path, LOCAL_STATIC).replace("\\", "/")
        remote_path = f"{FRONTEND_DIR}/{rel_path}"
        # 确保远程子目录存在
        remote_dir = os.path.dirname(remote_path)
        try:
            sftp.stat(remote_dir)
        except FileNotFoundError:
            ssh.exec_command(f"mkdir -p {remote_dir}", get_pty=True)
        print(f"Uploading: {rel_path}")
        sftp.put(local_path, remote_path)

# 重载 nginx
sudo("nginx -t && nginx -s reload")
print("\nNginx reloaded. Frontend updated successfully!")

sftp.close()
ssh.close()
