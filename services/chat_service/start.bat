@echo off
REM ====== chat_service 独立启动 ======
REM 依赖 AIRAGAgent 引擎：默认从项目根目录 (..\..) 引入，可用 AGENT_HOME 覆盖。
setlocal
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%..\..\.venv\Scripts\python.exe" (
    set PYTHON="%SCRIPT_DIR%..\..\.venv\Scripts\python.exe"
) else (
    set PYTHON=python
)

if "%AGENT_HOME%"=="" set AGENT_HOME=%SCRIPT_DIR%..\..
set PYTHONPATH=%AGENT_HOME%;%PYTHONPATH%

if "%CHAT_PORT%"=="" set CHAT_PORT=8003
if "%LOG_DIR%"=="" set LOG_DIR=%SCRIPT_DIR%logs

%PYTHON% -m uvicorn main:app --app-dir . --host 0.0.0.0 --port %CHAT_PORT% --log-level info
endlocal
