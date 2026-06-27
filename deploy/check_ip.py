"""
查询当前访问服务器的公网IP
"""
import paramiko

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

# 查看最近的访问日志获取IP
print("=== 最近访问服务器 API 的 IP ===")
stdin, stdout, stderr = ssh.exec_command(
    "sudo journalctl -u lc-course --no-pager -n 200 | grep -oP 'X-Real-IP.*?\\.' | tail -5",
    get_pty=True
)
print(stdout.read().decode())

# 也查看 nginx access log
print("=== nginx access log 最近记录 ===")
stdin, stdout, stderr = ssh.exec_command(
    "sudo tail -20 /var/log/nginx/access.log 2>/dev/null || echo 'no access log'",
    get_pty=True
)
print(stdout.read().decode())

ssh.close()
