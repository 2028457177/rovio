"""快速上传 main.py"""
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

local = r"c:\Users\nxt\PycharmProjects\lc-course\AIRAGAgent\fastapi_app\main.py"
remote = f"{BACKEND_DIR}/AIRAGAgent/fastapi_app/main.py"
print("上传 main.py...")
sftp.put(local, remote)
print("[OK]")
sftp.close()

print("重启服务...")
sudo("systemctl restart lc-course")
time.sleep(3)

stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
print(f"状态: {stdout.read().decode().strip()}")
ssh.close()
print("完成!")
