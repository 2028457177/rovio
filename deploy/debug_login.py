"""排查登录问题"""
import paramiko

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

# 服务状态
stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
print("lc-course:", stdout.read().decode().strip())

# 最近日志
print("\n=== 最近日志 ===")
stdin, stdout, stderr = ssh.exec_command("sudo journalctl -u lc-course --no-pager -n 30", get_pty=True)
print(stdout.read().decode())

# 测试 API
print("\n=== 测试登录 API ===")
stdin, stdout, stderr = ssh.exec_command(
    """curl -s -X POST http://127.0.0.1:8000/api/auth/login -H 'Content-Type: application/json' -d '{"username":"test123","password":"123456"}'""",
    get_pty=True
)
print(stdout.read().decode()[:300])

# 测试非 admin 登录
stdin, stdout, stderr = ssh.exec_command(
    """curl -s -X POST http://127.0.0.1/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'""",
    get_pty=True
)
print("\nAdmin登录:")
print(stdout.read().decode()[:300])

# nginx status
stdin, stdout, stderr = ssh.exec_command("systemctl is-active nginx", get_pty=True)
print("\nnginx:", stdout.read().decode().strip())

# 前端
stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/", get_pty=True)
print("前端HTTP:", stdout.read().decode().strip())

ssh.close()
