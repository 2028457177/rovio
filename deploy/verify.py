"""Verify deployment"""
import paramiko
import os

HOST = os.environ.get("LC_SERVER_HOST", "81.70.100.57")
USER = os.environ.get("LC_SERVER_USER", "ubuntu")
PASSWORD = os.environ.get("LC_SERVER_PASSWORD")

if not PASSWORD:
    raise SystemExit("未设置 LC_SERVER_PASSWORD 环境变量。")

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    print(stdout.read().decode('utf-8', errors='replace'))

print("=== Nginx Frontend ===")
run("curl -s http://127.0.0.1/ | head -10")

print("=== API /api/conversations ===")
run("curl -s http://127.0.0.1/api/conversations")

print("=== Backend Direct ===")
run("curl -s -o /dev/null -w 'HTTP: %{http_code}\n' http://127.0.0.1:8000/")

print("=== API Docs ===")
run("curl -s -o /dev/null -w 'HTTP: %{http_code}\n' http://127.0.0.1:8000/docs")

ssh.close()
