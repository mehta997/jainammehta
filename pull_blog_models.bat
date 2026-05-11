@echo off
setlocal

cd /d "%~dp0"

curl -s http://localhost:11434/api/tags >nul 2>nul
if errorlevel 1 (
  start "" /min ollama serve
  timeout /t 15 /nobreak >nul
)

echo [%date% %time%] Pulling qwen2.5:7b >> qwen_model_pull.log
ollama pull qwen2.5:7b >> qwen_model_pull.log 2>&1

echo [%date% %time%] Pulling qwen2.5:14b >> qwen_model_pull.log
ollama pull qwen2.5:14b >> qwen_model_pull.log 2>&1

echo [%date% %time%] Done >> qwen_model_pull.log

endlocal
