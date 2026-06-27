"""验证部署状态"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('81.70.100.57', username='ubuntu', password='***REMOVED***', timeout=15)

def sudo(cmd):
    ssh.exec_command(f"echo '***REMOVED***' | sudo -S bash -c '{cmd}'", get_pty=True)

# 确保 uploads 目录存在
sudo("mkdir -p /opt/lc-course/backend/uploads /opt/lc-course/uploads && chown -R ubuntu:ubuntu /opt/lc-course/backend/uploads /opt/lc-course/uploads")
print("uploads 目录已创建")

# 验证 API
stdin, stdout, stderr = ssh.exec_command('curl -s http://127.0.0.1:8000/api/health', get_pty=True)
print('API Health:', stdout.read().decode().strip())

# 验证前端
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/', get_pty=True)
print('Frontend HTTP:', stdout.read().decode().strip())

# 验证上传接口
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/upload-word -X POST', get_pty=True)
print('Upload API:', stdout.read().decode().strip(), '(预期 422, 因未传文件)')

# 验证 backend 服务状态
stdin, stdout, stderr = ssh.exec_command('systemctl is-active lc-course', get_pty=True)
print('lc-course:', stdout.read().decode().strip())

ssh.close()
