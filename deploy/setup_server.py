"""
Server setup - lc-course (final working version)
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
FRONTEND_DIR = "/var/www/lc-course-frontend"


def ssh_connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)
    print(f"[OK] Connected to {HOST}")
    return client


def sudo_cmd(ssh, cmd):
    full_cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'"
    print(f"  [sudo] {cmd[:130]}{'...' if len(cmd)>130 else ''}")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        print(f"    {out.strip()}")
    if err.strip():
        print(f"    [ERR] {err.strip()}")
    return out, err


def run_cmd(ssh, cmd):
    print(f"  > {cmd[:130]}{'...' if len(cmd)>130 else ''}")
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        print(f"    {out.strip()}")
    if err.strip():
        print(f"    [ERR] {err.strip()}")
    return out, err


print("=" * 50)
print("  lc-course Server Setup")
print("=" * 50)

ssh = ssh_connect()

# 1. Fix nginx - proper restart
print("\n[1/4] Fixing nginx...")
# Stop any running nginx processes
sudo_cmd(ssh, "pkill nginx 2>/dev/null; sleep 1; systemctl stop nginx 2>/dev/null; true")
# Ensure our config is in place
sudo_cmd(ssh, "cp /tmp/lc-course-nginx.conf /etc/nginx/sites-available/lc-course")
sudo_cmd(ssh, "sed -i 's/your-domain.com/81.70.100.57/g' /etc/nginx/sites-available/lc-course")
sudo_cmd(ssh, "rm -f /etc/nginx/sites-enabled/default")
sudo_cmd(ssh, "ln -sf /etc/nginx/sites-available/lc-course /etc/nginx/sites-enabled/lc-course")
# Start nginx
run_cmd(ssh, "sudo nginx -t")
sudo_cmd(ssh, "systemctl start nginx")
time.sleep(2)
run_cmd(ssh, "curl -s -o /dev/null -w 'HTTP: %{http_code}' http://127.0.0.1/")

# 2. Install Python dependencies via pip (since pip install -e . fails without setuptools config)
print("\n[2/4] Installing Python dependencies (this may take a few minutes)...")

deps = [
    "coloredlogs",
    "chromadb",
    "dashscope",
    "fastapi",
    "uvicorn[standard]",
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
]

# Install in batches to avoid timeout
batch_size = 5
for i in range(0, len(deps), batch_size):
    batch = deps[i:i+batch_size]
    cmd = f"cd {BACKEND_DIR} && .venv/bin/pip install {' '.join(batch)} -q 2>&1 | tail -3"
    run_cmd(ssh, cmd)

# Verify install
run_cmd(ssh, f"cd {BACKEND_DIR} && .venv/bin/python -c 'import fastapi; print(\"fastapi OK\")'")
run_cmd(ssh, f"cd {BACKEND_DIR} && .venv/bin/python -c 'import langchain; import langgraph; print(\"langchain/langgraph OK\")'")

# 3. Update systemd service
print("\n[3/4] Configuring systemd service...")
service_content = f'''[Unit]
Description=lc-course Backend Service
After=network.target

[Service]
Type=simple
User={USER}
WorkingDirectory={BACKEND_DIR}
ExecStart={BACKEND_DIR}/.venv/bin/python -m uvicorn AIRAGAgent.fastapi_app.main:app --host 0.0.0.0 --port 8000 --log-level info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
'''
run_cmd(ssh, f"cat > /tmp/lc-course.service << 'SERVICEEOF'\n{service_content}\nSERVICEEOF")
sudo_cmd(ssh, "cp /tmp/lc-course.service /etc/systemd/system/lc-course.service")
sudo_cmd(ssh, "systemctl daemon-reload")

# 4. Start backend
print("\n[4/4] Starting backend...")
sudo_cmd(ssh, "systemctl enable lc-course")
sudo_cmd(ssh, "systemctl restart lc-course")
time.sleep(5)
run_cmd(ssh, "sudo systemctl status lc-course --no-pager 2>&1 | head -20")
run_cmd(ssh, "curl -s -o /dev/null -w 'Backend: HTTP %{http_code}' http://127.0.0.1:8000/ 2>&1")
run_cmd(ssh, "sudo journalctl -u lc-course --no-pager -n 20 2>&1")

ssh.close()

print("\n" + "=" * 50)
print("  Deployment Complete!")
print("=" * 50)
print(f"""
Frontend: http://{HOST}/
Backend:  http://{HOST}:8000/

Management commands:
  sudo systemctl status lc-course
  sudo systemctl restart lc-course
  sudo journalctl -u lc-course -f
  sudo nginx -t && sudo nginx -s reload
""")
