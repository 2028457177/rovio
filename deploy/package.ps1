# ====== 一键拆包脚本 ======
# 将项目拆分为前端包和后端包，输出到 deploy/dist/
param(
    [switch]$BuildFrontend = $true,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
Set-Location $Root

$OutDir = "$Root\deploy\dist"
$BackendDir = "$OutDir\backend"
$FrontendDir = "$OutDir\frontend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  自动化办公助手 - 拆包部署" -ForegroundColor Cyan
Write-Host "  输出目录: $OutDir" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 清理旧输出
if (Test-Path $OutDir) {
    Remove-Item -Recurse -Force $OutDir
}
New-Item -ItemType Directory -Force -Path $BackendDir | Out-Null
New-Item -ItemType Directory -Force -Path $FrontendDir | Out-Null

# ========== 1. 前端打包 ==========
Write-Host "`n[1/3] 前端打包..." -ForegroundColor Yellow

Push-Location "$Root\frontend"
try {
    if (-not $SkipBuild -and $BuildFrontend) {
        Write-Host "  安装依赖..." -ForegroundColor Gray
        npm install --silent 2>&1 | Out-Null
        
        Write-Host "  构建生产版本..." -ForegroundColor Gray
        npm run build 2>&1 | Out-Null
        
        if (-not (Test-Path "dist")) {
            throw "前端构建失败，dist 目录不存在"
        }
    }
    
    # 复制构建产物
    Copy-Item -Recurse "dist\*" $FrontendDir
    Write-Host "  前端构建产物 -> $FrontendDir" -ForegroundColor Green

    # 复制 nginx 配置
    Copy-Item "$Root\deploy\frontend\nginx.conf" "$OutDir\frontend-nginx.conf"
    Write-Host "  nginx 配置 -> $OutDir\frontend-nginx.conf" -ForegroundColor Green
    
} finally {
    Pop-Location
}

# ========== 2. 后端打包 ==========
Write-Host "`n[2/3] 后端打包..." -ForegroundColor Yellow

$BackendExclude = @(
    "frontend",
    "deploy",
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "*.pyc",
    "logs",
    ".langgraph_api"
)

Write-Host "  复制后端代码..." -ForegroundColor Gray

# 复制根目录文件
Get-ChildItem $Root -File | ForEach-Object {
    $skip = $false
    foreach ($pattern in $BackendExclude) {
        if ($_.Name -like $pattern) { $skip = $true; break }
    }
    if (-not $skip) {
        Copy-Item $_.FullName $BackendDir
    }
}

# 复制 AIRAGAgent 目录（排除不需要的）
$agentExclude = @("__pycache__", "*.pyc", "logs", ".langgraph_api", "*.log")
$agentExcludePattern = @()
foreach ($e in $agentExclude) {
    $agentExcludePattern += "-not -iname `"$e`""
}

# 使用 robocopy 或 Copy-Item 复制 AIRAGAgent
Copy-Item -Recurse "$Root\AIRAGAgent" $BackendDir -ErrorAction SilentlyContinue

# 清理 __pycache__ 和日志
Get-ChildItem -Recurse "$BackendDir\AIRAGAgent" -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse "$BackendDir\AIRAGAgent\logs" -File -Filter "*.log" | Remove-Item -Force -ErrorAction SilentlyContinue

# 复制 chroma_ab 向量数据库
if (Test-Path "$Root\chroma_ab") {
    Copy-Item -Recurse "$Root\chroma_ab" "$BackendDir\chroma_ab"
    Write-Host "  向量数据库已打包" -ForegroundColor Gray
}

# 复制部署启动脚本
Copy-Item "$Root\deploy\backend\start.sh" $BackendDir
Copy-Item "$Root\deploy\backend\start.bat" $BackendDir
Copy-Item "$Root\deploy\backend\.env.example" $BackendDir

Write-Host "  后端代码 -> $BackendDir" -ForegroundColor Green

# ========== 3. 完成 ==========
Write-Host "`n[3/3] 打包完成!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  部署文件已生成:" -ForegroundColor Cyan
Write-Host "    $FrontendDir" -ForegroundColor White
Write-Host "    $BackendDir" -ForegroundColor White
Write-Host "    $OutDir\frontend-nginx.conf" -ForegroundColor White
Write-Host ""
Write-Host "  [服务器部署步骤]" -ForegroundColor Yellow
Write-Host "  1. 上传 backend/* 到服务器 (如 /opt/lc-course/backend/)" -ForegroundColor White
Write-Host "  2. 上传 frontend/* 到服务器 (如 /var/www/lc-course-frontend/)" -ForegroundColor White
Write-Host "  3. 服务器: cd /opt/lc-course/backend && chmod +x start.sh && bash start.sh" -ForegroundColor White
Write-Host "  4. 安装 nginx，复制 nginx.conf 并修改域名" -ForegroundColor White
Write-Host "  5. nginx -s reload" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
