"""拉取服务器最近的 agent 日志，看实际 yield 了哪些事件"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('81.70.100.57', username='ubuntu', password='***REMOVED***', timeout=15)

# 列出日志文件
_, o, _ = ssh.exec_command('ls -lt /opt/lc-course/backend/AIRAGAgent/logs/ | head -5', get_pty=True)
print('--- log files ---')
print(o.read().decode(errors='replace'))

# 读取最新的日志文件末尾
_, o, _ = ssh.exec_command(
    "latest=$(ls -t /opt/lc-course/backend/AIRAGAgent/logs/*.log | head -1); "
    "echo \"FILE: $latest\"; tail -n 80 \"$latest\"",
    get_pty=True)
print('--- latest log tail ---')
print(o.read().decode(errors='replace'))

# 也看下 journalctl 最近的 supervisor 决策日志
_, o, _ = ssh.exec_command(
    "echo '***REMOVED***' | sudo -S journalctl -u lc-course -n 40 --no-pager | grep -iE 'supervisor|thinking|工具|调用|reasoning|chunk' | tail -30",
    get_pty=True)
print('--- journalctl filtered ---')
print(o.read().decode(errors='replace'))

ssh.close()
