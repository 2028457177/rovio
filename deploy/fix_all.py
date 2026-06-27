"""一次性上传所有改动"""
import paramiko, time

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
BD = "/opt/lc-course/backend"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()

files = [
    "AIRAGAgent/database/__init__.py",
    "AIRAGAgent/database/models.py",
    "AIRAGAgent/database/connection.py",
    "AIRAGAgent/fastapi_app/main.py",
    "AIRAGAgent/fastapi_app/auth.py",
]
ROOT = r"c:\Users\nxt\PycharmProjects\lc-course"
for f in files:
    print(f"上传 {f}...")
    sftp.put(f"{ROOT}/{f}", f"{BD}/{f}")

sftp.close()

def sudo(cmd):
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'", get_pty=True)

print("重启...")
sudo("systemctl restart lc-course")
time.sleep(5)

stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
print(f"状态: {stdout.read().decode().strip()}")

stdin, stdout, stderr = ssh.exec_command(
    "curl -s -X POST http://127.0.0.1:8000/api/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin123\"}'",
    get_pty=True
)
print(f"登录: {stdout.read().decode()[:200]}")

ssh.close()
