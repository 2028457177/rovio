@echo off
REM ====== admin_service 独立启动 ======
REM 服务已完全解耦，可单独拷贝本目录到任意位置运行（无需项目根）。
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%..\..\.venv\Scripts\python.exe" (
    set PYTHON="%SCRIPT_DIR%..\..\.venv\Scripts\python.exe"
) else (
    set PYTHON=python
)
if "%ADMIN_PORT%"=="" set ADMIN_PORT=8005
if "%LOG_DIR%"=="" set LOG_DIR=%SCRIPT_DIR%logs

%PYTHON% -m uvicorn main:app --app-dir . --host 0.0.0.0 --port %ADMIN_PORT% --log-level info
endlocal
