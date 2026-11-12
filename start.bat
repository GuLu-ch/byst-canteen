@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "ROOT=%~dp0"
set "PYTHONPATH=%ROOT%backend\.deps"
set "TEMP=%ROOT%.tmp"
set "TMP=%ROOT%.tmp"

rem 清空 DSH / 系统代理，避免 pip、npm、node 走到已关闭的代理上
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

cd /d "%ROOT%backend"
if not exist "data\byst.db" (
  echo [1/2] 初始化数据库与演示数据...
  python init_db.py
)

echo [2/2] 启动服务： http://127.0.0.1:8000
echo.
echo   用户端（手机）  http://127.0.0.1:8000
echo   管理端（PC）    http://127.0.0.1:8000/admin
echo   接口文档        http://127.0.0.1:8000/docs
echo.
echo 关闭窗口即可停止服务。
start "" cmd /c "timeout /t 2 >nul & start "" http://127.0.0.1:8000"

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
echo.
echo 服务已停止。
pause
