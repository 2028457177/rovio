import paramiko

HOST = '81.70.100.57'
USER = 'ubuntu'
PASSWORD = '***REMOVED***'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

cmd = f"echo '{PASSWORD}' | sudo -S bash -c 'nginx -t && nginx -s reload'"
stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print('STDOUT:', out)
print('STDERR:', err)
ssh.close()
