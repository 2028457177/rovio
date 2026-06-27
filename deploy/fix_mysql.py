"""
Fix MySQL + nginx port 80
"""
import paramiko
import time

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
MYSQL_PW = "***REMOVED***"
BACKEND_DIR = "/opt/lc-course/backend"


def ssh_connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=22, username=USER, password=PASSWORD, timeout=15)
    return client


def run(ssh, cmd, sudo=False):
    if sudo:
        cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'"
    print(f"  >> {cmd[:130]}")
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        print(f"      {out.strip()}")
    if err.strip():
        print(f"      [ERR] {err.strip()}")
    return exit_code, out, err


ssh = ssh_connect()
print("[OK] Connected")

# 1. Fix MySQL root auth
print("\n=== 1. Fix MySQL root password ===")
run(ssh, 'sudo mysql -e "ALTER USER root@localhost IDENTIFIED VIA mysql_native_password USING PASSWORD(\'***REMOVED***\'); FLUSH PRIVILEGES;"')
run(ssh, "sudo mysql -e \"CREATE DATABASE IF NOT EXISTS agent_records CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\"")
run(ssh, "mysql -u root -p***REMOVED*** -e 'SELECT 1 AS test;'")

# 2. Fix port 80 conflict
print("\n=== 2. Fix port 80 ===")
run(ssh, "sudo ss -tlnp | grep ':80 '")
run(ssh, "sudo fuser -k 80/tcp 2>/dev/null; sleep 2; echo 'port 80 freed'", sudo=True)

# 3. Restart nginx
print("\n=== 3. Restart nginx ===")
run(ssh, "sudo nginx -t")
run(ssh, "sudo systemctl restart nginx")
time.sleep(2)
run(ssh, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/; echo")

# 4. Start backend
print("\n=== 4. Start backend ===")
run(ssh, "sudo systemctl stop lc-course 2>/dev/null; echo stopped")
run(ssh, "sudo systemctl start lc-course")
time.sleep(8)
run(ssh, "sudo systemctl status lc-course --no-pager | head -15")
run(ssh, "curl -s -o /dev/null -w 'Backend: HTTP %{http_code}' http://127.0.0.1:8000/; echo")
run(ssh, "sudo journalctl -u lc-course --no-pager -n 10 2>&1")

# 5. Firewall
print("\n=== 5. Firewall ===")
run(ssh, "sudo ufw status 2>/dev/null || echo 'ufw not active'")
run(ssh, "sudo ufw allow 80/tcp 2>/dev/null; sudo ufw allow 8000/tcp 2>/dev/null; echo 'done'")

ssh.close()
print("\nDone!")
