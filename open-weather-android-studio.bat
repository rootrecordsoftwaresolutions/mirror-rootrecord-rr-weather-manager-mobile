@echo off
setlocal
set "STUDIO=C:\Program Files\Android\Android Studio\bin\studio64.exe"
set "PROJ=%~dp0frontend\android"
if not exist "%STUDIO%" (
  echo Android Studio not found at:
  echo   %STUDIO%
  exit /b 1
)
if not exist "%PROJ%" (
  echo Android project not found at:
  echo   %PROJ%
  exit /b 1
)
start "" "%STUDIO%" "%PROJ%"
endlocal
