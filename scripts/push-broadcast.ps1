<#
.SYNOPSIS
  POST /api/internal/push-broadcast (all registered FCM tokens).

.EXAMPLE
  $env:RR_PUSH_ADMIN_KEY = 'your-secret'
  $env:REACT_APP_BACKEND_URL = 'https://rootrecord-primary.rootrecord.workers.dev'
  .\scripts\push-broadcast.ps1 -Title "Test" -Body "Hello"
#>
param(
  [Parameter(Mandatory = $true)][string]$Title,
  [Parameter(Mandatory = $true)][string]$Body,
  [string]$BaseUrl = $env:REACT_APP_BACKEND_URL
)

$ErrorActionPreference = 'Stop'
$key = $env:RR_PUSH_ADMIN_KEY
if (-not $key) { throw 'Set env RR_PUSH_ADMIN_KEY to the plaintext admin secret.' }
if (-not $BaseUrl) { throw 'Set env REACT_APP_BACKEND_URL or pass -BaseUrl (origin without /api).' }

$base = $BaseUrl.TrimEnd('/')
$uri = "$base/api/internal/push-broadcast"
$payload = @{ title = $Title; body = $Body } | ConvertTo-Json -Compress

$headers = @{
  'Content-Type'  = 'application/json'
  'X-RR-Push-Admin-Key' = $key
}

Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -Body $payload
