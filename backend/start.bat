@echo off
REM Backend Startup Script for Windows
setlocal enabledelayedexpansion

REM ========================================================
REM [关键修复] 切换到脚本所在目录的上一级 (项目根目录)
REM %~dp0 代表脚本所在目录，.. 代表上一级
cd /d "%~dp0.."
REM ========================================================

echo Current Working Directory: %cd%
echo Starting LaTeXTrans Backend...

REM Check Python version
python --version

REM Install/update dependencies
echo Installing dependencies...
pip install -r backend\requirements.txt

REM ========================================================
REM Load environment variables from .env file if it exists
REM ========================================================
if exist backend\.env (
    echo Loading environment variables from backend\.env...
    for /f "usebackq eol=# tokens=1,* delims==" %%a in ("backend\.env") do (
        if not "%%a"=="" if not "%%b"=="" (
            set "%%a=%%b"
            echo   Set %%a
        )
    )
) else (
    echo [WARN] backend\.env not found, using default values
)

REM Set fallback environment variables (only if not already set)
if not defined LLM_API_KEY set LLM_API_KEY=sk-SVd4dIKfuIwhQ9kUlgCr9ZMpoIWp7PEzZxpVStjSRqeqNBLu
if not defined LLM_BASE_URL set LLM_BASE_URL=https://aicanapi.com/v1/chat/completions
if not defined LLM_MODEL set LLM_MODEL=gpt-4.1-mini
if not defined LATEX_BIN_DIR set LATEX_BIN_DIR=D:\apps\texlive\2025\bin\windows

REM Check Supabase configuration (纯 RLS 模式只需要 URL 和 ANON_KEY)
if not defined SUPABASE_URL echo [WARN] SUPABASE_URL not configured - user settings will not persist
if not defined SUPABASE_ANON_KEY echo [WARN] SUPABASE_ANON_KEY not configured - user authentication disabled

REM Create data directories (将在项目根目录下创建 data 文件夹，结构更清晰)
if not exist data\uploads mkdir data\uploads
if not exist data\outputs mkdir data\outputs
if not exist data\terms mkdir data\terms

REM Start uvicorn server
echo Starting uvicorn server...
REM 现在我们在根目录，backend.app.main 路径就是正确的了
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

endlocal
pause