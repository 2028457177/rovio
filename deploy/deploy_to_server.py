"""
部署脚本：将打包好的文件上传到远程服务器并配置运行
"""
import paramiko
import os
import sys
import stat

# ====== 配置 ======
HOST = os.environ.get("LC_SERVER_HOST", "81.70.100.57")
USER = os.environ.get("LC_SERVER_USER", "ubuntu")
PASSWORD = os.environ.get("LC_SERVER_PASSWORD")
PORT = int(os.environ.get("LC_SERVER_PORT", "22"))

if not PASSWORD:
    raise SystemExit("未设置 LC_SERVER_PASSWORD 环境变量。请先注入：$env:LC_SERVER_PASSWORD='你的服务器密码'")

LOCAL_BACKEND = r"c:\Users\nxt\PycharmProjects\lc-course\deploy\dist\backend"
LOCAL_FRONTEND = r"c:\Users\nxt\PycharmProjects\lc-course\deploy\dist\frontend"
LOCAL_NGINX_CONF = r"c:\Users\nxt\PycharmProjects\lc-course\deploy\dist\frontend-nginx.conf"

REMOTE_BACKEND_DIR = "/opt/lc-course/backend"
REMOTE_FRONTEND_DIR = "/var/www/lc-course-frontend"


def ssh_connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)
    print(f"[OK] SSH 连接到 {HOST}")
    return client


def sudo_cmd(ssh, cmd):
    """执行需要 sudo 的命令"""
    full_cmd = f"echo '{PASSWORD}' | sudo -S {cmd}"
    print(f"  [sudo] {cmd}")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        print(f"    {out.strip()}")
    if err.strip():
        print(f"    [ERR] {err.strip()}")
    return out, err


def run_cmd(ssh, cmd):
    """执行普通命令"""
    print(f"  > {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip():
        print(f"    {out.strip()}")
    if err.strip():
        print(f"    [ERR] {err.strip()}")
    return out, err


def ensure_dir(ssh, sftp, remote_dir, owner=USER):
    """确保远程目录存在且有正确权限"""
    try:
        sftp.stat(remote_dir)
    except FileNotFoundError:
        sudo_cmd(ssh, f"mkdir -p {remote_dir}")
        sudo_cmd(ssh, f"chown -R {owner}:{owner} {remote_dir}")


def upload_file(sftp, local_path, remote_path):
    """上传单个文件"""
    try:
        sftp.put(local_path, remote_path)
        return True
    except Exception as e:
        print(f"    [ERROR] 上传失败 {local_path}: {e}")
        return False


def upload_directory(ssh, sftp, local_dir, remote_dir):
    """递归上传整个目录"""
    if not os.path.exists(local_dir):
        print(f"  [SKIP] 本地目录不存在: {local_dir}")
        return
    
    for root, dirs, files in os.walk(local_dir):
        rel_path = os.path.relpath(root, local_dir)
        if rel_path == ".":
            remote_path = remote_dir
        else:
            remote_path = f"{remote_dir}/{rel_path.replace(os.sep, '/')}"
        
        ensure_dir(ssh, sftp, remote_path)
        
        for fname in files:
            local_file = os.path.join(root, fname)
            remote_file = f"{remote_path}/{fname}"
            
            file_size = os.path.getsize(local_file)
            if file_size > 1024 * 1024:
                print(f"  上传 {rel_path}/{fname} ({file_size/1024/1024:.1f}MB)...")
            else:
                print(f"  上传 {rel_path}/{fname} ...")
            
            upload_file(sftp, local_file, remote_file)


print("=" * 50)
print("  lc-course 服务器部署")
print("=" * 50)

# 1. 连接
print("\n[1/6] 连接服务器...")
ssh = ssh_connect()
sftp = ssh.open_sftp()

# 2. 检查环境
print("\n[2/6] 检查服务器环境...")
run_cmd(ssh, "uname -a")
run_cmd(ssh, "cat /etc/os-release 2>/dev/null | head -4")
run_cmd(ssh, "python3 --version 2>&1")

# 3. 创建后端目录并授权
print("\n[3/6] 准备后端目录...")
sudo_cmd(ssh, f"rm -rf {REMOTE_BACKEND_DIR}")
sudo_cmd(ssh, f"mkdir -p {REMOTE_BACKEND_DIR}")
sudo_cmd(ssh, f"chown -R {USER}:{USER} {REMOTE_BACKEND_DIR}")

# 4. 上传后端
print("\n[4/6] 上传后端文件...")
upload_directory(ssh, sftp, LOCAL_BACKEND, REMOTE_BACKEND_DIR)
sudo_cmd(ssh, f"chmod +x {REMOTE_BACKEND_DIR}/start.sh")
sudo_cmd(ssh, f"chown -R {USER}:{USER} {REMOTE_BACKEND_DIR}")

# 5. 上传前端
print("\n[5/6] 上传前端文件...")
sudo_cmd(ssh, f"rm -rf {REMOTE_FRONTEND_DIR}")
sudo_cmd(ssh, f"mkdir -p {REMOTE_FRONTEND_DIR}")
sudo_cmd(ssh, f"chown -R {USER}:{USER} {REMOTE_FRONTEND_DIR}")
upload_directory(ssh, sftp, LOCAL_FRONTEND, REMOTE_FRONTEND_DIR)

# 6. 配置 nginx
print("\n[6/6] 配置 nginx...")
# 上传 nginx 配置
sftp.put(LOCAL_NGINX_CONF, "/tmp/lc-course-nginx.conf")

# 检测 nginx 配置目录结构
out, _ = run_cmd(ssh, "ls /etc/nginx/ 2>/dev/null")
print(f"  nginx 目录: {out.strip()}")

if "sites-available" in out:
    # Debian/Ubuntu 风格
    sudo_cmd(ssh, "cp /tmp/lc-course-nginx.conf /etc/nginx/sites-available/lc-course")
    sudo_cmd(ssh, "sed -i 's/your-domain.com/81.70.100.57/g' /etc/nginx/sites-available/lc-course")
    sudo_cmd(ssh, "ln -sf /etc/nginx/sites-available/lc-course /etc/nginx/sites-enabled/lc-course")
    sudo_cmd(ssh, "rm -f /etc/nginx/sites-enabled/default")
elif "conf.d" in out:
    # RHEL/CentOS 风格
    sudo_cmd(ssh, "cp /tmp/lc-course-nginx.conf /etc/nginx/conf.d/lc-course.conf")
    sudo_cmd(ssh, "sed -i 's/your-domain.com/81.70.100.57/g' /etc/nginx/conf.d/lc-course.conf")
else:
    # 直接放到 nginx 目录
    sudo_cmd(ssh, "cp /tmp/lc-course-nginx.conf /etc/nginx/lc-course.conf")
    sudo_cmd(ssh, "sed -i 's/your-domain.com/81.70.100.57/g' /etc/nginx/lc-course.conf")

# 创建 .env
print("\n创建 .env 配置...")
run_cmd(ssh, f"cp {REMOTE_BACKEND_DIR}/.env.example {REMOTE_BACKEND_DIR}/.env")

sftp.close()
ssh.close()

print("\n" + "=" * 50)
print("  文件上传完成！")
print("=" * 50)
print(f"""
接下来请在服务器上执行:

1. 编辑配置 (填写 API Key 等):
   ssh ubuntu@{HOST}
   sudo vim {REMOTE_BACKEND_DIR}/.env

2. 安装依赖并启动后端:
   cd {REMOTE_BACKEND_DIR}
   bash start.sh

3. 测试 nginx 并重载:
   sudo nginx -t
   sudo systemctl reload nginx

4. 访问: http://{HOST}/
""")
