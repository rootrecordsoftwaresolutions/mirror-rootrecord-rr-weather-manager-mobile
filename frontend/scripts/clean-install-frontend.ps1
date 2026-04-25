# From Weather Manager Mobile: powershell -NoProfile -File frontend\scripts\clean-install-frontend.ps1
# Cleans hoisted workspace + this package, then reinstalls from the Mobile App Development workspace root (pnpm).
# Optional: -PurgeLockfile  also deletes pnpm-lock.yaml at the workspace root (slower next install; only if lock is corrupted)
param([switch]$PurgeLockfile)
$ErrorActionPreference = "Stop"
$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
Set-Location $workspaceRoot
Write-Host "Workspace root: $((Get-Location).Path)"

$frontendNm = Join-Path $workspaceRoot "rr-weather-manager-mobile\frontend\node_modules"
$rootNm = Join-Path $workspaceRoot "node_modules"
foreach ($dir in @($frontendNm, $rootNm)) {
  if (Test-Path $dir) {
    Write-Host "Removing node_modules (rimraf): $dir"
    npx --yes rimraf@6 $dir
  }
}

if ($PurgeLockfile -and (Test-Path "pnpm-lock.yaml")) {
  Write-Host "Removing pnpm-lock.yaml (-PurgeLockfile)…"
  Remove-Item "pnpm-lock.yaml" -Force
}

try {
  if ((Test-Path "pnpm-lock.yaml") -and -not $PurgeLockfile) {
    Write-Host "pnpm install --frozen-lockfile…"
    pnpm install --frozen-lockfile
  } else {
    Write-Host "pnpm install (no lockfile or -PurgeLockfile)…"
    pnpm install
  }
} finally { }
