"""快速上传修复"""
import paramiko, time
HOST, USER, PWD, BD = "81.70.100.57", "ubuntu", "***REMOVED***", "/opt/lc-course/backend"
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PWD, timeout=15)
sftp = ssh.open_sftp()
sftp.put(r"c:\Users\nxt\PycharmProjects\lc-course\AIRAGAgent\fastapi_app\main.py", f"{BD}/AIRAGAgent/fastapi_app/main.py")
sftp.put(r"c:\Users\nxt\PycharmProjects\lc-course\AIRAGAgent\fastapi_app\auth.py", f"{BD}/AIRAGAgent/fastapi_app/auth.py")
sftp.close()
ssh.exec_command(f"echo '{PWD}' | sudo -S bash -c 'systemctl restart lc-course'", get_pty=True)
time.sleep(2)
i,o,e = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
print(f"状态: {o.read().decode().strip()}")
ssh.close()
