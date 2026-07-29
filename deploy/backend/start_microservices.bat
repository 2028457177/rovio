@echo off
REM ====== 微服务多进程启动脚本 (Windows) ======
REM 一键启动 6 个微服务进程，各自绑定独立端口

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..\..\
cd /d "%PROJECT_ROOT%"

REM 加载环境变量
if exist "%SCRIPT_DIR%.env" (
    for /f "usebackq tokens=*" %%a in (`type "%SCRIPT_DIR%.env" ^| findstr /v "^#"`) do set %%a
)

echo ========================================
echo   lc-course 微服务启动
echo   项目根: %PROJECT_ROOT%
echo ========================================

if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

echo 启动 6 个微服务进程...

start "auth_service  :8001" /D "%PROJECT_ROOT%" %PYTHON% -m uvicorn services.auth_service.main:app --host 0.0.0.0 --port 8001 --log-level info
start "user_service  :8002" /D "%PROJECT_ROOT%" %PYTHON% -m uvicorn services.user_service.main:app --host 0.0.0.0 --port 8002 --log-level info
start "chat_service  :8003" /D "%PROJECT_ROOT%" %PYTHON% -m uvicorn services.chat_service.main:app --host 0.0.0.0 --port 8003 --log-level info
start "kb_service    :8004" /D "%PROJECT_ROOT%" %PYTHON% -m uvicorn services.kb_service.main:app --host 0.0.0.0 --port 8004 --log-level info
start "admin_service :8005" /D "%PROJECT_ROOT%" %PYTHON% -m uvicorn services.admin_service.main:app --host 0.0.0.0 --port 8005 --log-level info
start "file_service  :8006" /D "%PROJECT_ROOT%" %PYTHON% -m uvicorn services.file_service.main:app --host 0.0.0.0 --port 8006 --log-level info

echo.
echo 全部服务已在新窗口启动。关闭对应窗口即可停止。
echo nginx 配置见 deploy/nginx_microservices.conf
endlocal
