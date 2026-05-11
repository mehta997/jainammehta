@echo off
setlocal

set "TASK_NAME=Jainam Blog Publisher"
set "SCRIPT=%~dp0daily_publish_blog.bat"

schtasks /Create /F /SC ONLOGON /TN "%TASK_NAME%" /TR "\"%SCRIPT%\"" /RL LIMITED

echo.
echo Installed startup publisher task: %TASK_NAME%
echo It runs daily_publish_blog.bat whenever Windows logs in.
echo The generator is date-safe, so it will publish only one post per day.

endlocal
