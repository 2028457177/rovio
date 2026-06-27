"""上传软删除修改"""
import paramiko, os, time

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
BD = "/opt/lc-course/backend"
FD = "/var/www/lc-course-frontend"
ROOT = r"c:\Users\nxt\PycharmProjects\lc-course"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()

def sudo(cmd):
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'", get_pty=True)

# 上传后端
for f in ["AIRAGAgent/database/connection.py", "AIRAGAgent/database/models.py"]:
    print(f"上传 {f}...")
    sftp.put(os.path.join(ROOT, f), f"{BD}/{f}")

# 上传前端
sudo(f"rm -rf {FD}/*")
sudo(f"mkdir -p {FD}")
sudo(f"chown -R {USER}:{USER} {FD}")
static = os.path.join(ROOT, "static")
for root, dirs, files in os.walk(static):
    rel = os.path.relpath(root, static)
    rd = FD if rel == "." else f"{FD}/{rel.replace(os.sep, '/')}"
    if rel != ".": 
        sudo(f"mkdir -p {rd}")
        sudo(f"chown -R {USER}:{USER} {rd}")
    for fn in files:
        sftp.put(os.path.join(root, fn), f"{rd}/{fn}")
        print(f"  [OK] {rel}/{fn}")

sftp.close()
print("\n重启服务...")
sudo("systemctl restart lc-course")
time.sleep(3)
i, o, e = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
print(f"状态: {o.read().decode().strip()}")
ssh.close()
print("部署完成!")
