"""部署思考栏修复：上传后端 react_agent.py + 前端 dist，重启服务"""
import paramiko
import os

HOST = "81.70.100.57"
USER = "ubuntu"
PASSWORD = "***REMOVED***"
BACKEND_DIR = "/opt/lc-course/backend"
FRONTEND_DIR = "/var/www/lc-course-frontend"
PROJECT_ROOT = r"c:\Users\nxt\PycharmProjects\lc-course"
DIST_DIR = os.path.join(PROJECT_ROOT, "frontend", "dist")

print("=" * 50)
print("  部署思考栏修复（后端 + 前端）")
print("=" * 50)

print("\n[1/5] 连接服务器...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
sftp = ssh.open_sftp()
print("[OK] SSH 连接成功")


def sudo(cmd):
    full_cmd = f"echo '{PASSWORD}' | sudo -S bash -c '{cmd}'"
    stdin, stdout, stderr = ssh.exec_command(full_cmd, get_pty=True)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if err.strip() and 'password' not in err.lower():
        print(f"  [ERR] {err.strip()}")
    return out


# 2. 上传后端文件
print("\n[2/5] 上传后端 react_agent.py...")
backend_file = "AIRAGAgent/agent/react_agent.py"
local_path = os.path.join(PROJECT_ROOT, backend_file)
remote_path = f"{BACKEND_DIR}/{backend_file}"
print(f"  上传 {backend_file} ({os.path.getsize(local_path)/1024:.1f}KB)...")
sftp.put(local_path, remote_path)
print("    [OK]")

# 3. 上传前端（先清空 assets 目录避免旧哈希文件残留）
print("\n[3/5] 清空远程 assets 目录并上传前端...")
sudo(f"rm -rf {FRONTEND_DIR}/assets && mkdir -p {FRONTEND_DIR}/assets")
sudo(f"chown -R {USER}:{USER} {FRONTEND_DIR}")

uploaded = 0
for root, dirs, files in os.walk(DIST_DIR):
    rel = os.path.relpath(root, DIST_DIR).replace("\\", "/")
    remote_subdir = FRONTEND_DIR if rel == "." else f"{FRONTEND_DIR}/{rel}"
    try:
        sftp.stat(remote_subdir)
    except FileNotFoundError:
        sudo(f"mkdir -p {remote_subdir}")
        sudo(f"chown -R {USER}:{USER} {remote_subdir}")
    for f in files:
        local = os.path.join(root, f)
        remote = f"{remote_subdir}/{f}"
        sftp.put(local, remote)
        uploaded += 1
print(f"  [OK] 已上传 {uploaded} 个前端文件")

# 4. 重启后端服务
print("\n[4/5] 重启后端服务...")
sudo("systemctl restart lc-course")
print("[OK] lc-course 服务已重启")

# 5. 验证
print("\n[5/5] 验证服务状态...")
stdin, stdout, stderr = ssh.exec_command("systemctl is-active lc-course", get_pty=True)
status = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  lc-course 状态: {status}")

stdin, stdout, stderr = ssh.exec_command(
    "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/", get_pty=True)
fe_status = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  前端 HTTP 状态: {fe_status}")

stdin, stdout, stderr = ssh.exec_command(
    "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/", get_pty=True)
be_status = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  后端 HTTP 状态: {be_status}")

sftp.close()
ssh.close()

print("\n" + "=" * 50)
print("  部署完成！刷新浏览器即可验证思考栏")
print("=" * 50)
