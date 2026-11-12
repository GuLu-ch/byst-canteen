@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "ROOT=%~dp0"
set "TEMP=%ROOT%.tmp"
set "TMP=%ROOT%.tmp"
set "npm_config_cache=%ROOT%.tmp\npm-cache"

set "HTTP_PROXY="
set "HTTPS_PROXY="
set "http_proxy="
set "https_proxy="
set "ALL_PROXY="
set "all_proxy="
set "NO_PROXY="
set "no_proxy="
set "NODE_USE_ENV_PROXY="

if not exist "%ROOT%.tmp" mkdir "%ROOT%.tmp"

echo 启动前端开发服务器（/api 会代理到 http://127.0.0.1:8000）
echo 记得另开一个窗口运行 start.bat 里的后端。
echo.
cd /d "%ROOT%frontend"
call "D:\software\node\npm.cmd" run dev
pause
