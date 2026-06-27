"""验证远程 react_agent.py 包含本次修复"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import paramiko

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
REMOTE = "/opt/lc-course/backend/AIRAGAgent/agent/react_agent.py"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()

with sftp.open(REMOTE, 'r') as f:
    content = f.read().decode('utf-8')

checks = [
    ('tool call announcement with newlines', '正在调用工具: {tc_name}\\n'),
    ('raw reasoning delta (no 思考中 prefix)', '"content": reasoning'),
    ('tool completion with newlines', '工具 [{tool_name}] 执行完成\\n'),
    ('no result_preview', 'result_preview' not in content),
    ('no 思考中 prefix', '思考中:' not in content),
]

print("=== 远程文件验证 ===")
for label, cond in checks:
    if isinstance(cond, bool):
        ok = cond
    else:
        ok = cond in content
    print(f"[{'OK' if ok else 'FAIL'}] {label}")

# 显示关键代码段
print("\n=== 关键代码段 ===")
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if 130 <= i <= 185:
        print(f"{i:4d}: {line}")

sftp.close()
ssh.close()
