"""验证管理员 API"""
import paramiko
import json

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

# 等待服务
import time
time.sleep(2)

# 登录
stdin, stdout, stderr = ssh.exec_command(
    """curl -s -X POST http://127.0.0.1/api/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}'""",
    get_pty=True
)
login_resp = stdout.read().decode()
print("Login:", login_resp[:200])

if login_resp.strip():
    token = json.loads(login_resp)["token"]
    
    # 测试 users API
    stdin, stdout, stderr = ssh.exec_command(
        f"""curl -s http://127.0.0.1/api/admin/users -H 'Authorization: Bearer {token}'""",
        get_pty=True
    )
    print("\nUsers:", stdout.read().decode()[:500])
    
    # 测试 conversations API
    stdin, stdout, stderr = ssh.exec_command(
        f"""curl -s http://127.0.0.1/api/admin/users/1/conversations -H 'Authorization: Bearer {token}'""",
        get_pty=True
    )
    print("\nConversations:", stdout.read().decode()[:500])

ssh.close()
