@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

REM Optional: set RR_PUSH_ADMIN_KEY or RR_API_BASE; else Python reads backend\.env and uses rootrecord-primary.
if not defined RR_API_BASE set "RR_API_BASE=https://rootrecord-primary.rootrecord.workers.dev/api"

python "%~dp0broadcast_push.py" %*
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo Failed with exit code %EC%.
)
echo.
pause
exit /b %EC%
