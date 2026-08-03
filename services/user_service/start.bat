@echo off
REM ====== user_service 独立启动 ======
REM 服务已完全解耦，可单独拷贝本目录到任意位置运行（无需项目根）。
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%..\..\.venv\Scripts\python.exe" (
    set PYTHON="%SCRIPT_DIR%..\..\.venv\Scripts\python.exe"
) else (
    set PYTHON=python
)
if "%USER_PORT%"=="" set USER_PORT=8002
if "%LOG_DIR%"=="" set LOG_DIR=%SCRIPT_DIR%logs
if "%UPLOAD_DIR%"=="" set UPLOAD_DIR=%SCRIPT_DIR%data\uploads

%PYTHON% -m uvicorn main:app --app-dir . --host 0.0.0.0 --port %USER_PORT% --log-level info
endlocal
