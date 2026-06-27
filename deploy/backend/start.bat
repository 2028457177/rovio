@echo off
REM ====== 后端启动脚本 (Windows) ======

cd /d "%~dp0"

REM 默认值
if "%SERVER_HOST%"=="" set SERVER_HOST=0.0.0.0
if "%SERVER_PORT%"=="" set SERVER_PORT=8000

echo ========================================
echo   自动化办公助手 - 后端服务
echo   监听: %SERVER_HOST%:%SERVER_PORT%
echo ========================================

REM 安装依赖
echo [1/2] 安装 Python 依赖...
where uv >nul 2>nul
if %ERRORLEVEL%==0 (
    uv sync --frozen
) else (
    pip install -e . --quiet
)

REM 启动服务
echo [2/2] 启动 FastAPI 服务...
python -m uvicorn AIRAGAgent.fastapi_app.main:app --host %SERVER_HOST% --port %SERVER_PORT% --log-level info --timeout-keep-alive 300
