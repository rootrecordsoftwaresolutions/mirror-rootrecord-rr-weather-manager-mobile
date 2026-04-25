@echo off
setlocal EnableExtensions
cd /d "%~dp0.."

REM --- Edit or set in environment before running ---
if not defined RR_PUSH_ADMIN_KEY (
  echo ERROR: RR_PUSH_ADMIN_KEY is not set. It must match RR_PUSH_ADMIN_SECRET in backend\.env
  echo Example:  set RR_PUSH_ADMIN_KEY=your-long-random-secret
  exit /b 1
)
if not defined RR_API_BASE set "RR_API_BASE=https://rootrecord-primary.rootrecord.workers.dev/api"

python "%~dp0broadcast_push.py" %*
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
  echo.
  echo Failed with exit code %EC%.
  pause
)
exit /b %EC%
