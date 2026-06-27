"""验证后端服务是否健康启动"""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('81.70.100.57', username='ubuntu', password='***REMOVED***', timeout=15)

# 轮询后端 HTTP 状态
for i in range(5):
    _, o, _ = ssh.exec_command(
        "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/", get_pty=True)
    s = o.read().decode(errors='replace').strip()
    print(f'backend try{i+1}: {s}')
    if s == '200':
        break
    time.sleep(5)

# 查看最近日志，确认无导入错误
_, o, _ = ssh.exec_command(
    "echo '***REMOVED***' | sudo -S journalctl -u lc-course -n 30 --no-pager",
    get_pty=True)
print('\n--- recent logs ---')
print(o.read().decode(errors='replace'))
ssh.close()
