"""上传 file_tools.py 修复并重启"""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('81.70.100.57', username='ubuntu', password='***REMOVED***', timeout=15)
sftp = ssh.open_sftp()

def sudo(cmd):
    ssh.exec_command("echo '***REMOVED***' | sudo -S bash -c '" + cmd + "'", get_pty=True)

# 上传修复后的 file_tools.py
sftp.put('AIRAGAgent/agent/tools/file_tools.py', '/opt/lc-course/backend/AIRAGAgent/agent/tools/file_tools.py')
print('file_tools.py 已更新')

# 重启服务
sudo('systemctl restart lc-course')
stdin, stdout, stderr = ssh.exec_command('systemctl is-active lc-course', get_pty=True)
print('lc-course status:', stdout.read().decode().strip())

sftp.close()
ssh.close()
