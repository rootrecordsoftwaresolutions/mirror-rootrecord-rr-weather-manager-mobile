@echo off
setlocal EnableExtensions
title Root Record Weather Manager — build web + Android

rem Workspace root = parent of this repo (pnpm-workspace.yaml lives there)
pushd "%~dp0..\" || exit /b 1

echo.
echo [1/2] React production build ^(uses frontend\.env.production^)...
call pnpm --filter rrweather-mobile run build
if errorlevel 1 (
  echo BUILD FAILED.
  popd
  pause
  exit /b 1
)

echo.
echo [2/2] Capacitor sync + Android assembleDebug APK...
call pnpm --filter rrweather-mobile run android:assemble
if errorlevel 1 (
  echo ANDROID BUILD FAILED.
  popd
  pause
  exit /b 1
)

echo.
echo Done.
echo Web ^(from workspace root^): rr-weather-manager-mobile\frontend\build\
echo APK ^(from workspace root^): rr-weather-manager-mobile\frontend\android\app\build\outputs\apk\debug\RootRecord-Weather.apk
for %%I in ("%~dp0frontend\android\app\build\outputs\apk\debug\RootRecord-Weather.apk") do echo APK ^(full path^): %%~fI
popd
echo.
pause
exit /b 0
