@echo off
REM Backend TEST Startup Script for Windows
REM 用于本地开发测试，使用 8001 端口 + --reload，不影响 8000 端口的正式服务
setlocal enabledelayedexpansion

REM ========================================================
REM 切换到脚本所在目录的上一级 (项目根目录)
cd /d "%~dp0.."
REM ========================================================

echo ============================================================
echo   [TEST MODE] LaTeXTrans Backend - Port 8001
echo   正式服务运行在 8000 端口，本测试实例运行在 8001 端口
echo   代码修改后会自动热重载，测试完毕后按 Ctrl+C 关闭即可
echo ============================================================
echo.
echo Current Working Directory: %cd%

REM ========================================================
REM Load environment variables from .env file if it exists
REM ========================================================
if exist backend\.env (
    echo Loading environment variables from backend\.env...
    for /f "usebackq eol=# tokens=1,* delims==" %%a in ("backend\.env") do (
        if not "%%a"=="" if not "%%b"=="" (
            set "%%a=%%b"
        )
    )
) else (
    echo [WARN] backend\.env not found, using default values
)

REM Set fallback environment variables
if not defined LATEX_BIN_DIR set LATEX_BIN_DIR=D:\apps\texlive\2025\bin\windows

REM Check Supabase configuration
if not defined SUPABASE_URL echo [WARN] SUPABASE_URL not configured
if not defined SUPABASE_ANON_KEY echo [WARN] SUPABASE_ANON_KEY not configured

echo.
echo Starting uvicorn TEST server on port 8001 with --reload...
echo Test API docs: http://localhost:8001/docs
echo.
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload --log-level info

endlocal
pause
