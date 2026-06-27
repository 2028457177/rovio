"""紧急修复 __init__.py"""
import paramiko

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
BD = "/opt/lc-course/backend"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()

print("上传 __init__.py...")
sftp.put(r"c:\Users\nxt\PycharmProjects\lc-course\AIRAGAgent\database\__init__.py", f"{BD}/AIRAGAgent/database/__init__.py")
sftp.close()

def sudo(cmd):
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'", get_pty=True)

import time
sudo("systemctl restart lc-course")
time.sleep(4)

stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
status = stdout.read().decode().strip()
print(f"状态: {status}")

# 测试
stdin, stdout, stderr = ssh.exec_command(
    """curl -s -X POST http://127.0.0.1:8000/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'""",
    get_pty=True
)
print(f"登录测试: {stdout.read().decode()[:200]}")

ssh.close()
