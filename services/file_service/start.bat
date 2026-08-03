@echo off
REM ====== file_service 独立启动 ======
REM 服务已完全解耦，可单独拷贝本目录到任意位置运行（无需项目根）。
REM 注意：UPLOAD_DIR / WORKSPACE_DIR 默认指向本服务 data/ 下，
REM 生产环境（nginx 共享）请显式设置两个环境变量。
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%..\..\.venv\Scripts\python.exe" (
    set PYTHON="%SCRIPT_DIR%..\..\.venv\Scripts\python.exe"
) else (
    set PYTHON=python
)
if "%FILE_PORT%"=="" set FILE_PORT=8006
if "%LOG_DIR%"=="" set LOG_DIR=%SCRIPT_DIR%logs
if "%UPLOAD_DIR%"=="" set UPLOAD_DIR=%SCRIPT_DIR%data\uploads
if "%WORKSPACE_DIR%"=="" set WORKSPACE_DIR=%SCRIPT_DIR%data\workspace

%PYTHON% -m uvicorn main:app --app-dir . --host 0.0.0.0 --port %FILE_PORT% --log-level info
endlocal
