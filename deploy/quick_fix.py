"""快速上传修复"""
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
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'", get_pty=True)

local = r"c:\Users\nxt\PycharmProjects\lc-course\AIRAGAgent\database\models.py"
remote = f"{BACKEND_DIR}/AIRAGAgent/database/models.py"
print("上传 models.py...")
sftp.put(local, remote)
print("[OK]")
sftp.close()

print("重启服务...")
sudo("systemctl restart lc-course")
time.sleep(2)

stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
print(f"状态: {stdout.read().decode().strip()}")

# 验证
import json
stdin, stdout, stderr = ssh.exec_command(
    """curl -s -X POST http://127.0.0.1/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'""",
    get_pty=True
)
token = json.loads(stdout.read().decode())["token"]
stdin, stdout, stderr = ssh.exec_command(
    f"""curl -s http://127.0.0.1/api/admin/users -H 'Authorization: Bearer {token}'""",
    get_pty=True
)
print(f"\n结果: {stdout.read().decode()[:400]}")
ssh.close()
