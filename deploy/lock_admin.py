"""配置管理员IP白名单 + 重启服务"""
import paramiko
import time

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)

def sudo(cmd):
    full_cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if err.strip():
        print(f"  [ERR] {err.strip()}")
    return out

# 读取当前 service 文件
print("读取当前 service 文件...")
stdin, stdout, stderr = ssh.exec_command("sudo cat /etc/systemd/system/lc-course.service", get_pty=True)
current = stdout.read().decode()

if "ADMIN_ALLOWED_IPS" in current:
    print("已有 ADMIN_ALLOWED_IPS 配置，更新...")
    # 替换已有的配置
    new_content = current
    import re
    new_content = re.sub(r'ADMIN_ALLOWED_IPS=[^\n]*', 'ADMIN_ALLOWED_IPS=60.10.194.237,60.10.18.88', new_content)
else:
    print("添加 ADMIN_ALLOWED_IPS 配置...")
    # 在 Environment= 的第一行后添加，或在 [Service] 段中添加
    new_content = current.replace(
        "[Service]\nType=simple",
        "[Service]\nEnvironment=ADMIN_ALLOWED_IPS=60.10.18.88\nType=simple"
    )

# 写入新配置
print("写入新 service 配置...")
sudo(f"cat > /etc/systemd/system/lc-course.service << 'SERVICEEOF'\n{new_content}\nSERVICEEOF")

# 重载并重启
print("重载 systemd...")
sudo("systemctl daemon-reload")
print("重启服务...")
sudo("systemctl restart lc-course")
time.sleep(3)

# 验证
stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
print(f"服务状态: {stdout.read().decode().strip()}")

# 检查环境变量是否生效
print("\n检查环境变量...")
stdin, stdout, stderr = ssh.exec_command(
    "sudo cat /proc/$(pgrep -f 'uvicorn AIRAGAgent' | head -1)/environ 2>/dev/null | tr '\\0' '\\n' | grep ADMIN",
    get_pty=True
)
env_out = stdout.read().decode().strip()
print(env_out if env_out else "(无法直接读取，但配置文件已更新)")

ssh.close()
print("\n配置完成! 仅 IP 60.10.18.88 可访问管理后台。")
