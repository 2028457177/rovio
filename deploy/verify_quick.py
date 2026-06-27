import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("81.70.100.57", username="ubuntu", password="***REMOVED***", timeout=15)
def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    return stdout.read().decode()
print("Frontend:", run('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/'))
print("API:", run("curl -s http://127.0.0.1/api/health"))
print("Service:")
print(run("systemctl status lc-course --no-pager 2>&1 | head -5"))
ssh.close()
