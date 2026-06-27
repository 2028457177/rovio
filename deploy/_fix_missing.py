import paramiko
import time

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
BACKEND_DIR = "/opt/lc-course/backend"
MIRROR = "https://pypi.tuna.tsinghua.edu.cn/simple"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    return out, err

# Install missing packages
missing = ["PyJWT", "python-multipart", "aiofiles", "httpx", "requests"]
for pkg in missing:
    print(f"Installing {pkg}...")
    o, e = run(f"cd {BACKEND_DIR} && .venv/bin/pip install {pkg} -i {MIRROR} --trusted-host pypi.tuna.tsinghua.edu.cn 2>&1")
    if "Successfully installed" in o:
        print(f"  OK")
    elif "already satisfied" in o.lower():
        print(f"  Already installed")
    else:
        print(f"  {o.strip()[-100:]}")

# Verify import
print("\nVerifying import...")
o, e = run(f"cd {BACKEND_DIR} && .venv/bin/python -c 'import jwt; print(\"jwt OK\")'")
print(o.strip())

# Try direct import of app
print("\nTesting app import...")
o, e = run(f"cd {BACKEND_DIR} && .venv/bin/python -c 'from AIRAGAgent.fastapi_app.main import app; print(\"App title:\", app.title)'")
print("OUT:", o.strip())
if e.strip():
    print("ERR:", e.strip()[-300:])

# Restart service
print("\nRestarting service...")
o, e = run(f"echo '{PASSWORD}' | sudo -S systemctl restart lc-course")
time.sleep(5)

# Check status
stdin, stdout, stderr = ssh.exec_command(
    f"echo '{PASSWORD}' | sudo -S systemctl status lc-course --no-pager",
    get_pty=True
)
status = stdout.read().decode(errors='replace')
print(status[:500])

# Verify endpoints
time.sleep(3)
stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/", get_pty=True)
print(f"\nBackend HTTP: {stdout.read().decode().strip()}")

ssh.close()
