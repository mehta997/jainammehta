@echo off
setlocal

cd /d "%~dp0"

python -c "import boto3" >nul 2>&1
if errorlevel 1 (
  echo [%date% %time%] boto3 not found, installing... >> daily_blog.log 2>&1
  python -m pip install boto3 >> daily_blog.log 2>&1
  if errorlevel 1 (
    py -3 -m pip install boto3 >> daily_blog.log 2>&1
  )
)

python generate_blog.py >> daily_blog.log 2>&1
if errorlevel 1 (
  py -3 generate_blog.py >> daily_blog.log 2>&1
)

endlocal
