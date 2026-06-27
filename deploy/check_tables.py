"""
查询服务器 MySQL 表结构
"""
import paramiko

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
MYSQL_PASSWORD = "***REMOVED***"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

# 查看所有表
stdin, stdout, stderr = ssh.exec_command(
    f"mysql -u root -p{MYSQL_PASSWORD} agent_records -e 'SHOW TABLES;'",
    get_pty=True
)
print("=== 数据库表 ===")
print(stdout.read().decode())

# 查看 user 表结构
stdin, stdout, stderr = ssh.exec_command(
    f"mysql -u root -p{MYSQL_PASSWORD} agent_records -e 'DESCRIBE user;'",
    get_pty=True
)
print("=== user 表结构 ===")
out = stdout.read().decode()
err = stderr.read().decode()
print(out if out else err)

# 查看 users 表结构
stdin, stdout, stderr = ssh.exec_command(
    f"mysql -u root -p{MYSQL_PASSWORD} agent_records -e 'DESCRIBE users;'",
    get_pty=True
)
print("=== users 表结构 ===")
out = stdout.read().decode()
err = stderr.read().decode()
print(out if out else err)

# 查看 user 表数据量
stdin, stdout, stderr = ssh.exec_command(
    f"mysql -u root -p{MYSQL_PASSWORD} agent_records -e 'SELECT COUNT(*) as cnt FROM user;'",
    get_pty=True
)
print("=== user 表行数 ===")
out = stdout.read().decode()
err = stderr.read().decode()
print(out if out else err)

# 查看 users 表数据量
stdin, stdout, stderr = ssh.exec_command(
    f"mysql -u root -p{MYSQL_PASSWORD} agent_records -e 'SELECT COUNT(*) as cnt FROM users;'",
    get_pty=True
)
print("=== users 表行数 ===")
out = stdout.read().decode()
err = stderr.read().decode()
print(out if out else err)

# 查看 user 表数据样例
stdin, stdout, stderr = ssh.exec_command(
    f"mysql -u root -p{MYSQL_PASSWORD} agent_records -e 'SELECT * FROM user LIMIT 5;'",
    get_pty=True
)
print("=== user 表样例数据 ===")
print(stdout.read().decode())

ssh.close()
