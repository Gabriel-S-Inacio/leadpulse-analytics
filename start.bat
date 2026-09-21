@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
set "leadpulse_exit_code=%ERRORLEVEL%"

echo.
pause
exit /b %leadpulse_exit_code%
