import paramiko

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    return stdout.read().decode(errors='replace')

print("Frontend:", run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/").strip())
print("Backend:", run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/").strip())
print("API:", run("curl -s http://127.0.0.1:8000/").strip()[:120])

o = run("curl -s http://127.0.0.1/ | grep -o '<title>.*</title>'")
print("\nFrontend title:", o.strip())

print("Service:", run("systemctl is-active lc-course").strip())

ssh.close()
