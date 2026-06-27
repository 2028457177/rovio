"""在服务器上测试 deepseek-v4-flash 是否产生 reasoning_content"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko

TEST_SCRIPT = '''
import sys
sys.path.insert(0, "/opt/lc-course/backend")
from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import HumanMessage

model = ChatDeepSeek(model="deepseek-v4-flash", api_key="***REMOVED***", max_tokens=4096, temperature=0.7)

print("=== Streaming test: 你好 ===")
reasoning_found = False
content_found = False
chunk_count = 0
for chunk in model.stream([HumanMessage(content="你好")]):
    chunk_count += 1
    content = chunk.content or ""
    reasoning = (getattr(chunk, "additional_kwargs", None) or {}).get("reasoning_content", "")
    if reasoning:
        reasoning_found = True
        print(f"[REASONING chunk#{chunk_count}] {repr(reasoning[:120])}")
    if content:
        content_found = True
        print(f"[CONTENT chunk#{chunk_count}] {repr(content[:120])}")

print(f"\\n=== total chunks: {chunk_count} ===")
print(f"=== reasoning_found: {reasoning_found} ===")
print(f"=== content_found: {content_found} ===")
'''

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('81.70.100.57', username='ubuntu', password='***REMOVED***', timeout=15)

# 上传测试脚本
sftp = ssh.open_sftp()
with sftp.open('/tmp/_test_reasoning.py', 'w') as f:
    f.write(TEST_SCRIPT)
sftp.close()

# 用后端 venv 运行
print("运行模型测试...")
_, o, e = ssh.exec_command(
    "cd /opt/lc-course/backend && .venv/bin/python /tmp/_test_reasoning.py 2>&1",
    get_pty=True, timeout=60)
out = o.read().decode(errors='replace')
print(out)

err = e.read().decode(errors='replace')
if err.strip():
    print("--- stderr ---")
    print(err)

ssh.close()
