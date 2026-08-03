@echo off
REM ====== 微服务多进程启动脚本 (Windows) ======
REM 一键启动 6 个微服务进程，各自绑定独立端口
REM 每个服务从自身目录以 uvicorn main:app --app-dir . 方式启动（已完全解耦）

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..\..\
cd /d "%PROJECT_ROOT%"

REM 加载环境变量
if exist "%SCRIPT_DIR%.env" (
    for /f "usebackq tokens=*" %%a in (`type "%SCRIPT_DIR%.env" ^| findstr /v "^#"`) do set %%a
)

echo ========================================
echo   lc-course 微服务启动（独立目录模式）
echo   项目根: %PROJECT_ROOT%
echo ========================================

if exist "%PROJECT_ROOT%.venv\Scripts\python.exe" (
    set PYTHON=%PROJECT_ROOT%.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

REM chat/kb 需要引入项目根目录的 AIRAGAgent 引擎
set PYTHONPATH=%PROJECT_ROOT%;%PYTHONPATH%

REM 端口（可用 .env 中的 *_PORT 覆盖）
if "%AUTH_PORT%"=="" set AUTH_PORT=8001
if "%USER_PORT%"=="" set USER_PORT=8002
if "%CHAT_PORT%"=="" set CHAT_PORT=8003
if "%KB_PORT%"==""   set KB_PORT=8004
if "%ADMIN_PORT%"=="" set ADMIN_PORT=8005
if "%FILE_PORT%"=="" set FILE_PORT=8006

echo 启动 6 个微服务进程...

start "auth_service  :%AUTH_PORT%" /D "%PROJECT_ROOT%services\auth_service" %PYTHON% -m uvicorn main:app --app-dir . --host 0.0.0.0 --port %AUTH_PORT% --log-level info
start "user_service  :%USER_PORT%" /D "%PROJECT_ROOT%services\user_service" %PYTHON% -m uvicorn main:app --app-dir . --host 0.0.0.0 --port %USER_PORT% --log-level info
start "chat_service  :%CHAT_PORT%" /D "%PROJECT_ROOT%services\chat_service" %PYTHON% -m uvicorn main:app --app-dir . --host 0.0.0.0 --port %CHAT_PORT% --log-level info
start "kb_service    :%KB_PORT%" /D "%PROJECT_ROOT%services\kb_service" %PYTHON% -m uvicorn main:app --app-dir . --host 0.0.0.0 --port %KB_PORT% --log-level info
start "admin_service :%ADMIN_PORT%" /D "%PROJECT_ROOT%services\admin_service" %PYTHON% -m uvicorn main:app --app-dir . --host 0.0.0.0 --port %ADMIN_PORT% --log-level info
start "file_service  :%FILE_PORT%" /D "%PROJECT_ROOT%services\file_service" %PYTHON% -m uvicorn main:app --app-dir . --host 0.0.0.0 --port %FILE_PORT% --log-level info

echo.
echo 全部服务已在新窗口启动。关闭对应窗口即可停止。
echo nginx 配置见 deploy/nginx_microservices.conf
endlocal
