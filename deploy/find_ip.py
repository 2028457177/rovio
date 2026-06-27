"""
上传 auth.py + 查看客户端 IP
"""
import paramiko
import os
import time

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
BACKEND_DIR = "/opt/lc-course/backend"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()

def sudo(cmd):
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'", get_pty=True)

# 上传 auth.py
local = r"c:\Users\nxt\PycharmProjects\lc-course\AIRAGAgent\fastapi_app\auth.py"
remote = f"{BACKEND_DIR}/AIRAGAgent/fastapi_app/auth.py"
print("上传 auth.py...")
sftp.put(local, remote)
print("[OK]")
sftp.close()

# 查看 nginx access log 获取最近访问IP
print("\n=== 最近的客户端 IP ===")
stdin, stdout, stderr = ssh.exec_command(
    "sudo tail -50 /var/log/nginx/access.log 2>/dev/null | grep -v '127.0.0.1' | grep -v '::1' | awk '{print $1}' | sort -u | tail -10",
    get_pty=True
)
out = stdout.read().decode().strip()
if out:
    for ip in out.split('\n'):
        print(f"  {ip}")
else:
    # 试其他路径
    stdin, stdout, stderr = ssh.exec_command(
        "sudo tail -50 /var/log/nginx/access.log 2>/dev/null | head -5",
        get_pty=True
    )
    print(stdout.read().decode()[:500])
    print("(没有找到外部访问记录)")

ssh.close()
