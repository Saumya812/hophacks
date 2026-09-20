<#
.SYNOPSIS
  Point findmypal.us at your local FindMyPal stack (GoDaddy domain + Cloudflare Tunnel).

.NOTES
  GoDaddy = domain registrar (sponsor track).
  Cloudflare = DNS + tunnel (already in front of findmypal.us).
  This does NOT host on GoDaddy servers — it makes YOUR domain open your laptop app.
#>

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$cf = Join-Path $Root "scripts\tools\cloudflared.exe"
if (-not (Test-Path $cf)) {
  throw "Missing $cf — download cloudflared first."
}

$cfDir = Join-Path $env:USERPROFILE ".cloudflared"
New-Item -ItemType Directory -Force -Path $cfDir | Out-Null

Write-Host "== FindMyPal domain tunnel (findmypal.us) =="
Write-Host "GoDaddy keeps the domain registration. Cloudflare Tunnel serves the app."
Write-Host ""

# 1) Login (opens browser once)
$cert = Join-Path $cfDir "cert.pem"
if (-not (Test-Path $cert)) {
  Write-Host "Opening Cloudflare login in your browser..."
  Write-Host "Pick the account that owns the findmypal.us zone, then return here."
  & $cf tunnel login
  if (-not (Test-Path $cert)) {
    throw "Login did not create cert.pem — try again."
  }
}

# 2) Create tunnel if needed
$tunnelName = "findmypal-demo"
$list = & $cf tunnel list 2>&1 | Out-String
if ($list -notmatch $tunnelName) {
  Write-Host "Creating tunnel $tunnelName ..."
  & $cf tunnel create $tunnelName
}

# Resolve credentials file (UUID.json)
$cred = Get-ChildItem $cfDir -Filter "*.json" |
  Where-Object { $_.Name -ne "cert.pem" -and $_.Name -match '^[0-9a-f-]{36}\.json$' } |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1
if (-not $cred) {
  throw "No tunnel credentials JSON in $cfDir"
}

# 3) Write config
$configPath = Join-Path $cfDir "findmypal-config.yml"
@"
tunnel: $tunnelName
credentials-file: $($cred.FullName)

ingress:
  - hostname: spacetime.findmypal.us
    service: http://127.0.0.1:3000
  - hostname: findmypal.us
    service: http://127.0.0.1:5174
  - hostname: www.findmypal.us
    service: http://127.0.0.1:5174
  - service: http_status:404
"@ | Set-Content $configPath -Encoding UTF8
Write-Host "Wrote $configPath"

# 4) Route DNS (Cloudflare API via cloudflared)
Write-Host "Creating DNS routes (CNAME → tunnel)..."
& $cf tunnel route dns $tunnelName findmypal.us 2>&1 | Write-Host
& $cf tunnel route dns $tunnelName www.findmypal.us 2>&1 | Write-Host
& $cf tunnel route dns $tunnelName spacetime.findmypal.us 2>&1 | Write-Host

# 5) Frontend env for custom domain
$envPath = Join-Path $Root "frontend\.env"
Copy-Item $envPath (Join-Path $Root "frontend\.env.localbackup") -Force -ErrorAction SilentlyContinue
@"
# Domain tunnel mode — https://findmypal.us
VITE_API_BASE_URL=
VITE_SPACETIMEDB_URI=wss://spacetime.findmypal.us
VITE_SPACETIMEDB_DATABASE=findmypal
"@ | Set-Content $envPath -Encoding UTF8
Write-Host "Updated frontend/.env for findmypal.us / spacetime.findmypal.us"
Write-Host ""
Write-Host "NEXT:"
Write-Host "  1. Restart Vite (npm run dev) so env reloads"
Write-Host "  2. Keep API + Spacetime running"
Write-Host "  3. This window will run the tunnel — leave it open"
Write-Host "  4. Open https://findmypal.us"
Write-Host ""

& $cf tunnel --config $configPath run $tunnelName
