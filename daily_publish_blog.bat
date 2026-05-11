@echo off
setlocal

cd /d "%~dp0"

curl -s http://localhost:11434/api/tags >nul 2>nul
if errorlevel 1 (
  start "" /min ollama serve
  timeout /t 15 /nobreak >nul
)

python generate_blog.py >> daily_blog.log 2>&1
if errorlevel 1 (
  py -3 generate_blog.py >> daily_blog.log 2>&1
)

endlocal
