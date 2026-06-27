"""验证远程文件确实包含本次修改"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('81.70.100.57', username='ubuntu', password='***REMOVED***', timeout=15)

# 1. 远程 react_agent.py：检查 result_preview 是否已移除
print("=== [1] 远程 react_agent.py ===")
_, o, _ = ssh.exec_command(
    "grep -n 'result_preview\\|_truncate_content\\|执行完成' /opt/lc-course/backend/AIRAGAgent/agent/react_agent.py",
    get_pty=True)
print(o.read().decode(errors='replace'))

# 2. 远程 index.html 引用的 ChatView 文件名
print("=== [2] 远程 index.html 引用 ===")
_, o, _ = ssh.exec_command("cat /var/www/lc-course-frontend/index.html", get_pty=True)
print(o.read().decode(errors='replace'))

# 3. 远程 assets 目录里的 ChatView 文件
print("=== [3] 远程 ChatView 文件 ===")
_, o, _ = ssh.exec_command("ls -la /var/www/lc-course-frontend/assets/ | grep -i chatview", get_pty=True)
print(o.read().decode(errors='replace'))

# 4. 检查新的 ChatView JS 是否还包含 supervisor_thinking
print("=== [4] 新 ChatView JS 是否含 supervisor ===")
_, o, _ = ssh.exec_command(
    "for f in /var/www/lc-course-frontend/assets/ChatView-*.js; do echo \"-- $f --\"; grep -c 'supervisor' \"$f\"; done",
    get_pty=True)
print(o.read().decode(errors='replace'))

ssh.close()
