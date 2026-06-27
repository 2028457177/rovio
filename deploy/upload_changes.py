"""
Incremental upload: upload changed backend + frontend files, then restart service
"""
import paramiko
import os
import time

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

BACKEND_DIR = "/opt/lc-course/backend"
FRONTEND_DIR = "/var/www/lc-course-frontend"
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()

def sudo_cmd(cmd):
    full_cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)
    out = stdout.read().decode()
    if out.strip():
        print(out.strip())
    return out

def upload_file(local, remote):
    print(f"  Upload: {os.path.basename(local)} -> {remote}")
    sftp.put(local, remote)

print("=== Upload backend changes ===")

# Upload modified main.py
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
upload_file(
    os.path.join(base, "AIRAGAgent", "fastapi_app", "main.py"),
    f"{BACKEND_DIR}/AIRAGAgent/fastapi_app/main.py"
)
upload_file(
    os.path.join(base, "AIRAGAgent", "database", "models.py"),
    f"{BACKEND_DIR}/AIRAGAgent/database/models.py"
)
upload_file(
    os.path.join(base, "AIRAGAgent", "database", "connection.py"),
    f"{BACKEND_DIR}/AIRAGAgent/database/connection.py"
)
upload_file(
    os.path.join(base, "AIRAGAgent", "database", "__init__.py"),
    f"{BACKEND_DIR}/AIRAGAgent/database/__init__.py"
)

print("\n=== Upload frontend changes ===")
for fname in os.listdir(STATIC_DIR):
    local = os.path.join(STATIC_DIR, fname)
    remote = f"{FRONTEND_DIR}/{fname}"
    if os.path.isfile(local):
        upload_file(local, remote)
    elif os.path.isdir(local):
        sudo_cmd(f"mkdir -p {remote}")
        for root, dirs, files in os.walk(local):
            rel = os.path.relpath(root, local)
            if rel == ".":
                rdir = remote
            else:
                rdir = f"{remote}/{rel.replace(os.sep, '/')}"
                sudo_cmd(f"mkdir -p {rdir}")
            for f in files:
                upload_file(os.path.join(root, f), f"{rdir}/{f}")

sftp.close()

print("\n=== Restart backend ===")
sudo_cmd("systemctl restart lc-course")
time.sleep(4)

ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh2.connect(HOST, username=USER, password=PASSWORD, timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh2.exec_command(cmd, get_pty=True)
    return stdout.read().decode()

print(run("sudo systemctl status lc-course --no-pager 2>&1 | head -10"))
print("\n=== Test Auth API ===")
print(run("curl -s -X POST http://127.0.0.1:8000/api/auth/register -H 'Content-Type: application/json' -d '{\"username\":\"test123\",\"password\":\"test123456\"}'"))

ssh2.close()
print("\n[DONE]")
