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

# Step 1: Remove broken venv and recreate with pip
print("Step 1: Recreating virtual environment...")
run(f"rm -rf {BACKEND_DIR}/.venv")
o, e = run(f"cd {BACKEND_DIR} && python3 -m venv .venv")
print(o)

# Step 2: Install pip + upgrade
print("Step 2: Installing pip (mirror: tsinghua)...")
o, e = run(f"cd {BACKEND_DIR} && .venv/bin/python -m ensurepip --upgrade")
o2, e2 = run(f"cd {BACKEND_DIR} && .venv/bin/pip install --upgrade pip -i {MIRROR} --trusted-host pypi.tuna.tsinghua.edu.cn")
print(o2[:200])

# Step 3: Install all packages
print("Step 3: Installing packages...")
packages = [
    "uvicorn[standard]",
    "fastapi",
    "coloredlogs",
    "chromadb",
    "dashscope",
    "langchain",
    "langchain-chroma",
    "langchain-community",
    "langchain-deepseek",
    "langchain-ollama",
    "langchain-tavily",
    "langgraph",
    "langgraph-cli",
    "numpy",
    "pandas",
    "pymysql",
    "python-docx",
    "python-dotenv",
    "streamlit",
    "openpyxl",
    "redis",
    "hiredis",
    "prompt-toolkit",
]

for pkg in packages:
    print(f"  Installing {pkg}...")
    o, e = run(f"cd {BACKEND_DIR} && .venv/bin/pip install '{pkg}' -i {MIRROR} --trusted-host pypi.tuna.tsinghua.edu.cn 2>&1")
    if "Successfully installed" in o:
        print(f"    OK")
    elif "already satisfied" in o.lower():
        print(f"    Already installed")
    else:
        last_line = o.strip().split('\n')[-1] if o.strip() else ''
        print(f"    {last_line[:200]}")

# Step 4: Verify uvicorn
print("\nStep 4: Verifying uvicorn...")
o, e = run(f"cd {BACKEND_DIR} && .venv/bin/python -c 'import uvicorn; print(uvicorn.__version__)'")
print(f"Uvicorn version: {o.strip()}")

# Step 5: Restart service
print("\nStep 5: Starting service...")
o, e = run(f"echo '{PASSWORD}' | sudo -S systemctl restart lc-course")
time.sleep(5)

# Check status
stdin, stdout, stderr = ssh.exec_command(
    f"echo '{PASSWORD}' | sudo -S systemctl status lc-course --no-pager",
    get_pty=True
)
print(stdout.read().decode(errors='replace')[:600])

# Step 6: Verify endpoints
print("\nStep 6: Verifying endpoints...")
time.sleep(3)

stdin, stdout, stderr = ssh.exec_command(
    "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/",
    get_pty=True
)
frontend_code = stdout.read().decode().strip()
print(f"Frontend: HTTP {frontend_code}")

stdin, stdout, stderr = ssh.exec_command(
    "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/",
    get_pty=True
)
backend_code = stdout.read().decode().strip()
print(f"Backend: HTTP {backend_code}")

ssh.close()
print("\nDone!")
