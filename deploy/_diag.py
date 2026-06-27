import paramiko

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
BACKEND_DIR = "/opt/lc-course/backend"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    return out, err

# Get last 50 log lines
print("=== Journal logs ===")
o, e = run("sudo journalctl -u lc-course --no-pager -n 50")
print(o)

# Try importing directly
print("\n=== Direct import test ===")
o, e = run(f"cd {BACKEND_DIR} && .venv/bin/python -c 'from AIRAGAgent.fastapi_app.main import app; print(app.title)'")
print("OUT:", o.strip())
if e.strip():
    print("ERR:", e.strip()[:500])

# Try running uvicorn manually briefly
print("\n=== Uvicorn test (3 seconds) ===")
o, e = run(f"cd {BACKEND_DIR} && timeout 5 .venv/bin/python -m uvicorn AIRAGAgent.fastapi_app.main:app --host 0.0.0.0 --port 8000 2>&1 || true")
print(o[-1000:])
if e.strip():
    print("ERR:", e.strip()[-500:])

ssh.close()
