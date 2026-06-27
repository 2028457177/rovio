"""上传前端文件到服务器"""
import paramiko, os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('81.70.100.57', username='ubuntu', password='***REMOVED***', timeout=15)
sftp = ssh.open_sftp()

FRONTEND_DIR = '/var/www/lc-course-frontend'

for root, dirs, files in os.walk('static'):
    rel_path = root.replace('\\', '/')
    if rel_path == 'static':
        remote_subdir = FRONTEND_DIR
    else:
        remote_subdir = FRONTEND_DIR + '/' + rel_path.replace('static/', '')
    
    try:
        sftp.stat(remote_subdir)
    except FileNotFoundError:
        ssh.exec_command(f"mkdir -p {remote_subdir}", get_pty=True)

    for f in files:
        local = os.path.join(root, f)
        remote = remote_subdir + '/' + f
        print(f'  {f}')
        sftp.put(local, remote)

print('Done - frontend updated')
sftp.close()
ssh.close()
