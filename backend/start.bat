@echo off
REM Backend Startup Script for Windows

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
REM 注意：这里假设 requirements.txt 在 backend 目录下，如果在根目录则不需要修改
REM 如果 requirements.txt 在 backend 文件夹里，请改为: pip install -r backend\requirements.txt
pip install -r backend\requirements.txt

REM Set environment variables (optional)
if not defined LLM_API_KEY set LLM_API_KEY=sk-SVd4dIKfuIwhQ9kUlgCr9ZMpoIWp7PEzZxpVStjSRqeqNBLu
if not defined LLM_BASE_URL set LLM_BASE_URL=https://aicanapi.com/v1/chat/completions
if not defined LLM_MODEL set LLM_MODEL=gpt-4.1-mini
if not defined LATEX_BIN_DIR set LATEX_BIN_DIR=D:\apps\texlive\2025\bin\windows

REM Create data directories (将在项目根目录下创建 data 文件夹，结构更清晰)
if not exist data\uploads mkdir data\uploads
if not exist data\outputs mkdir data\outputs
if not exist data\terms mkdir data\terms

REM Start uvicorn server
echo Starting uvicorn server...
REM 现在我们在根目录，backend.app.main 路径就是正确的了
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

pause