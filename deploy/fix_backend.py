"""
Fix backend: create venv and install dependencies
"""
import paramiko
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
PORT = 22

BACKEND_DIR = "/opt/lc-course/backend"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)
print(f"[OK] Connected to {HOST}")

def sudo_cmd(cmd):
    full_cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'"
    print(f"  [sudo] {cmd[:150]}")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        for line in out.strip().split('\n'):
            print(f"    {line[:200]}")
    if err.strip():
        print(f"    [ERR] {err.strip()[:200]}")
    return out, err

def run_cmd(cmd, timeout=120):
    print(f"  > {cmd[:150]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        for line in out.strip().split('\n'):
            print(f"    {line[:200]}")
    if err.strip():
        print(f"    [ERR] {err.strip()[:200]}")
    return out, err

print("\n[1/4] Creating virtual environment...")
run_cmd(f"cd {BACKEND_DIR} && python3 -m venv .venv")
run_cmd(f"ls -la {BACKEND_DIR}/.venv/bin/python 2>&1")

print("\n[2/4] Installing dependencies (this will take a few minutes)...")

deps = [
    "coloredlogs chromadb dashscope fastapi",
    "uvicorn[standard]",
    "langchain langchain-chroma langchain-community langchain-deepseek langchain-ollama",
    "langchain-tavily langgraph langgraph-cli numpy pandas",
    "pymysql python-docx python-dotenv streamlit openpyxl",
    "redis hiredis PyJWT",
    "prompt-toolkit",
]

for i, dep_batch in enumerate(deps):
    cmd = f"cd {BACKEND_DIR} && .venv/bin/pip install {dep_batch} 2>&1 | tail -5"
    print(f"\n  [{i+1}/{len(deps)}] Installing: {dep_batch[:80]}...")
    run_cmd(cmd, timeout=180)

print("\n[3/4] Verifying installs...")
run_cmd(f"cd {BACKEND_DIR} && .venv/bin/python -c 'import fastapi, jwt, pymysql; print(\"OK: fastapi, jwt, pymysql\")'")
run_cmd(f"cd {BACKEND_DIR} && .venv/bin/python -c 'import langchain; print(\"OK: langchain\")'")

print("\n[4/4] Restarting service...")
sudo_cmd("systemctl restart lc-course")
time.sleep(5)
run_cmd("sudo systemctl status lc-course --no-pager 2>&1 | head -15")
run_cmd("curl -s -o /dev/null -w 'Backend: HTTP %{http_code}\\n' http://127.0.0.1:8000/ 2>&1")
run_cmd("curl -s -o /dev/null -w 'Frontend: HTTP %{http_code}\\n' http://127.0.0.1/ 2>&1")

ssh.close()
print("\n[DONE] Backend fixed and started!")
