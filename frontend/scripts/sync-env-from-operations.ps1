# Copies env files from F:\Root Record Operations into this repo when you place them there.
# Create (for example):
#   F:\Root Record Operations\secrets\rr-weather-manager\frontend.env.production
#   F:\Root Record Operations\secrets\rr-weather-manager\backend.env
# Put the same contents you would use for frontend/.env.production and backend/.env.
$ErrorActionPreference = "Stop"
$base = "F:\Root Record Operations\secrets\rr-weather-manager"
$feSrc = Join-Path $base "frontend.env.production"
$beSrc = Join-Path $base "backend.env"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$feDst = Join-Path $repo "frontend\.env.production"
$beDst = Join-Path $repo "backend\.env"

if (-not (Test-Path $base)) {
  Write-Host "Nothing to do: create folder and files:" -ForegroundColor Yellow
  Write-Host "  $base"
  Write-Host "  $feSrc"
  Write-Host "  $beSrc"
  exit 0
}
$copied = $false
if (Test-Path $feSrc) {
  Copy-Item -LiteralPath $feSrc -Destination $feDst -Force
  Write-Host "Copied -> $feDst" -ForegroundColor Green
  $copied = $true
} else {
  Write-Host "Skip (missing): $feSrc" -ForegroundColor DarkYellow
}
if (Test-Path $beSrc) {
  Copy-Item -LiteralPath $beSrc -Destination $beDst -Force
  Write-Host "Copied -> $beDst" -ForegroundColor Green
  $copied = $true
} else {
  Write-Host "Skip (missing): $beSrc" -ForegroundColor DarkYellow
}
if (-not $copied) {
  Write-Host "No source files found under $base" -ForegroundColor Yellow
  exit 1
}
Write-Host "Done. Rebuild frontend/Android so REACT_APP_BACKEND_URL is embedded." -ForegroundColor Green
