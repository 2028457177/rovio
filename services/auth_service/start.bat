@echo off
REM ====== auth_service 独立启动 ======
REM 服务已完全解耦，可单独拷贝本目录到任意位置运行（无需项目根）。
REM 环境变量可通过 deploy/backend/.env 或系统环境设置，未设置时用默认值。
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%..\..\.venv\Scripts\python.exe" (
    set PYTHON="%SCRIPT_DIR%..\..\.venv\Scripts\python.exe"
) else (
    set PYTHON=python
)
if "%AUTH_PORT%"=="" set AUTH_PORT=8001
if "%LOG_DIR%"=="" set LOG_DIR=%SCRIPT_DIR%logs

%PYTHON% -m uvicorn main:app --app-dir . --host 0.0.0.0 --port %AUTH_PORT% --log-level info
endlocal
