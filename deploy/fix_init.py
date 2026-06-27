"""快速上传 init.py 修复"""
import paramiko
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
    full_cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)
    out = stdout.read().decode('utf-8', errors='replace')
    return out

# 上传 __init__.py
print("上传 __init__.py...")
local = r"c:\Users\nxt\PycharmProjects\lc-course\AIRAGAgent\database\__init__.py"
remote = f"{BACKEND_DIR}/AIRAGAgent/database/__init__.py"
sftp.put(local, remote)
print("[OK]")

sftp.close()

# 重启服务
print("重启服务...")
sudo("systemctl restart lc-course")
time.sleep(3)

# 验证
stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
status = stdout.read().decode().strip()
print(f"服务状态: {status}")

# 测试 API
token_resp = ssh.exec_command(
    """curl -s -X POST http://127.0.0.1/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'""",
    get_pty=True
)[1].read().decode()
import json
token = json.loads(token_resp)["token"]

stdin, stdout, stderr = ssh.exec_command(
    f"""curl -s http://127.0.0.1/api/admin/users -H 'Authorization: Bearer {token}'""",
    get_pty=True
)
print(f"\nAdmin Users API: {stdout.read().decode()[:300]}")

ssh.close()
