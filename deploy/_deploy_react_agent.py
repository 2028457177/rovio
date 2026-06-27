"""
增量部署：仅上传 react_agent.py 并重启 lc-course 服务
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import paramiko

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
BACKEND_DIR = "/opt/lc-course/backend"
LOCAL_FILE = "AIRAGAgent/agent/react_agent.py"
REMOTE_FILE = f"{BACKEND_DIR}/AIRAGAgent/agent/react_agent.py"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()


def sudo(cmd):
    stdin, stdout, stderr = ssh.exec_command(
        f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'", get_pty=True
    )
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out, err


# 1) 上传文件
print(f"[1/3] 上传 {LOCAL_FILE} -> {REMOTE_FILE}")
sftp.put(LOCAL_FILE, REMOTE_FILE)
print("    上传完成")

# 2) 修正属主
print("[2/3] 修正文件属主")
out, err = sudo(f"chown ubuntu:ubuntu {REMOTE_FILE}")
print(f"    属主已设置")

# 3) 重启服务
print("[3/3] 重启 lc-course 服务")
out, err = sudo("systemctl restart lc-course")
print(out)
if err:
    print("STDERR:", err)

# 4) 检查状态
import time
time.sleep(2)
out, err = sudo("systemctl is-active lc-course")
print(f"服务状态: {out.strip()}")

sftp.close()
ssh.close()
print("\n部署完成")
