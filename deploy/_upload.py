import paramiko
import os
import time

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
BACKEND_DIR = "/opt/lc-course/backend"
FRONTEND_DIR = "/var/www/lc-course-frontend"
LOCAL_FRONTEND = os.path.join(os.path.dirname(__file__), "dist", "frontend")
LOCAL_BACKEND = os.path.join(os.path.dirname(__file__), "dist", "backend")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()

def sudo(cmd):
    full = f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'"
    stdin, stdout, stderr = ssh.exec_command(full, get_pty=True)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    return out, err

def upload_dir(local_dir, remote_dir, skip_venv=True):
    """Recursively upload a directory via SFTP."""
    for root, dirs, files in os.walk(local_dir):
        if skip_venv and '.venv' in dirs:
            dirs.remove('.venv')
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')

        rel_path = os.path.relpath(root, local_dir)
        remote_path = os.path.join(remote_dir, rel_path).replace('\\', '/')

        # Create remote directory
        try:
            sftp.stat(remote_path)
        except FileNotFoundError:
            try:
                sftp.mkdir(remote_path)
            except:
                pass

        for f in files:
            local_file = os.path.join(root, f)
            remote_file = os.path.join(remote_path, f).replace('\\', '/')
            try:
                sftp.put(local_file, remote_file)
                print(f"  Uploaded: {rel_path}/{f}" if rel_path != '.' else f"  Uploaded: {f}")
            except Exception as e:
                print(f"  FAILED: {rel_path}/{f} - {e}")

# ====== Step 1: Upload Frontend ======
print("=== Uploading Frontend ===")
sudo("mkdir -p /var/www/lc-course-frontend")
sudo("chown -R ubuntu:ubuntu /var/www/lc-course-frontend")
upload_dir(LOCAL_FRONTEND, FRONTEND_DIR)

# ====== Step 2: Upload Backend ======
print("\n=== Uploading Backend ===")
# Clear old backend and re-upload
sudo("rm -rf /opt/lc-course/backend")
sudo("mkdir -p /opt/lc-course/backend")
sudo("chown -R ubuntu:ubuntu /opt/lc-course/backend")
upload_dir(LOCAL_BACKEND, BACKEND_DIR)

# ====== Step 3: Install dependencies (if needed) ======
print("\n=== Checking Python environment ===")
stdin, stdout, stderr = ssh.exec_command(
    f"cd {BACKEND_DIR} && [ -d .venv ] && echo 'VENV_EXISTS' || echo 'NO_VENV'",
    get_pty=True
)
venv_status = stdout.read().decode().strip()

if 'NO_VENV' in venv_status:
    print("Creating virtual environment...")
    ssh.exec_command(f"cd {BACKEND_DIR} && python3 -m venv .venv", get_pty=True)
    print("Installing dependencies (this may take a minute)...")
    cmd = (
        f"cd {BACKEND_DIR} && .venv/bin/pip install --upgrade pip -q && "
        f".venv/bin/pip install coloredlogs chromadb dashscope fastapi 'uvicorn[standard]' -q && "
        f".venv/bin/pip install langchain langchain-chroma langchain-community langchain-deepseek langchain-ollama -q && "
        f".venv/bin/pip install langchain-tavily langgraph langgraph-cli numpy pandas -q && "
        f".venv/bin/pip install pymysql python-docx python-dotenv streamlit openpyxl -q && "
        f".venv/bin/pip install redis hiredis prompt-toolkit -q"
    )
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    stdout.read()
    print("Dependencies installed.")
else:
    print("Virtual environment exists, checking for new packages...")
    # Quick pip install to catch any new dependencies from updated pyproject.toml
    cmd = (
        f"cd {BACKEND_DIR} && "
        f".venv/bin/pip install coloredlogs chromadb dashscope fastapi 'uvicorn[standard]' langchain langchain-chroma langchain-community langchain-deepseek langchain-ollama langchain-tavily langgraph langgraph-cli numpy pandas pymysql python-docx python-dotenv streamlit openpyxl redis hiredis prompt-toolkit -q 2>&1"
    )
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    stdout.read()
    print("Packages checked.")

# ====== Step 4: Restart Backend ======
print("\n=== Restarting backend service ===")
out, err = sudo("systemctl restart lc-course")
print("Backend restarted.")
time.sleep(2)

# Check status
stdin, stdout, stderr = ssh.exec_command("sudo systemctl status lc-course --no-pager -l", get_pty=True)
status = stdout.read().decode(errors='replace')
print(status[:500])

# ====== Step 5: Reload Nginx ======
print("\n=== Reloading Nginx ===")
out, err = sudo("nginx -t && nginx -s reload")
print(out)

# ====== Step 6: Verify ======
print("\n=== Verification ===")
time.sleep(2)

stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/", get_pty=True)
frontend_code = stdout.read().decode().strip()
print(f"Frontend HTTP status: {frontend_code}")

stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/", get_pty=True)
backend_code = stdout.read().decode().strip()
print(f"Backend HTTP status: {backend_code}")

sftp.close()
ssh.close()
print("\n=== Upload Complete ===")
