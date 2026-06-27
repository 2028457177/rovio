"""
查看服务器后端日志
"""
import paramiko

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

def sudo(cmd):
    full_cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out, err

# 查看最近日志
print("=== 最近的 systemd 日志 ===")
out, err = sudo("journalctl -u lc-course --no-pager -n 50")
print(out if out else err)

# 查看是否有日志文件
print("\n=== 检查日志文件 ===")
stdin, stdout, stderr = ssh.exec_command("ls -la /opt/lc-course/backend/AIRAGAgent/logs/ 2>/dev/null || echo 'No logs dir'", get_pty=True)
print(stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command("find /opt/lc-course/backend -name '*.log' -type f 2>/dev/null | head -10", get_pty=True)
print(stdout.read().decode())

ssh.close()
