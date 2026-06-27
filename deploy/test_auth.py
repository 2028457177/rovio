"""Final verification"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("81.70.100.57", username="ubuntu", password="***REMOVED***", timeout=15)
sftp = ssh.open_sftp()

script = """#!/bin/bash
echo "=== Login test ==="
curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test123","password":"test123456"}'

echo ""
echo "=== Login via nginx ==="
curl -s -X POST http://127.0.0.1/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test123","password":"test123456"}'

echo ""
echo "=== Frontend HTML ==="
curl -s http://127.0.0.1/ | head -5

echo ""
echo "=== API health via nginx ==="
curl -s http://127.0.0.1/api/health
"""

with sftp.open("/tmp/test.sh", "w") as f:
    f.write(script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command("bash /tmp/test.sh", get_pty=True)
print(stdout.read().decode())

ssh.close()
