"""修复 service 文件添加 ADMIN_ALLOWED_IPS"""
import paramiko
import time

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

def sudo(cmd):
    ssh.exec_command(f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'", get_pty=True)

new_service = """[Unit]
Description=lc-course Backend Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/lc-course/backend
Environment=SERVE_STATIC=false
Environment=ADMIN_ALLOWED_IPS=60.10.18.88
ExecStart=/opt/lc-course/backend/.venv/bin/python -m uvicorn AIRAGAgent.fastapi_app.main:app --host 0.0.0.0 --port 8000 --log-level info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target"""

sudo(f"cat > /etc/systemd/system/lc-course.service << 'EOF'\n{new_service}\nEOF")
sudo("systemctl daemon-reload")
sudo("systemctl restart lc-course")
time.sleep(3)

stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
print(f"状态: {stdout.read().decode().strip()}")

# 验证
stdin, stdout, stderr = ssh.exec_command("sudo cat /etc/systemd/system/lc-course.service", get_pty=True)
print(stdout.read().decode())

ssh.close()
