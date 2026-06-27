"""验证修复"""
import paramiko
import json
import time

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

time.sleep(3)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
print("状态:", stdout.read().decode().strip())

stdin, stdout, stderr = ssh.exec_command(
    "curl -s -X POST http://127.0.0.1:8000/api/auth/login -H 'Content-Type: application/json' -d 'test_login.json' 2>/dev/null",
    get_pty=True
)
print(stdout.read().decode()[:200])

# 直接用 shell
stdin, stdout, stderr = ssh.exec_command(
    """curl -s http://127.0.0.1/api/health""",
    get_pty=True
)
print("Health:", stdout.read().decode()[:200])

ssh.close()
