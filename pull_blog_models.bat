@echo off
setlocal

cd /d "%~dp0"

echo [%date% %time%] AWS Bedrock does not require local model pulls. >> qwen_model_pull.log 2>&1

echo [%date% %time%] No action required. >> qwen_model_pull.log 2>&1

endlocal
