# SpacetimeDB helpers for Windows (mirrors scripts/spacetime.sh)
param(
  [Parameter(Position = 0)]
  [ValidateSet('start', 'publish', 'generate')]
  [string]$Command = 'start',
  [Parameter(Position = 1)]
  [string]$Database = 'findmypal'
)

$Root = Split-Path -Parent $PSScriptRoot
$Cli = Join-Path $Root '.spacetime\bin\current\spacetimedb-cli.exe'
if (-not (Test-Path $Cli)) {
  Write-Error 'CLI missing. Place spacetimedb-cli.exe in .spacetime/bin/current/'
  exit 1
}

switch ($Command) {
  'start' {
    & $Cli --root-dir (Join-Path $Root '.spacetime') start --listen-addr 127.0.0.1:3000 --data-dir (Join-Path $Root '.spacetime\server') --non-interactive
  }
  'publish' {
    & $Cli --root-dir (Join-Path $Root '.spacetime') publish $Database -p (Join-Path $Root 'spacetimedb\spacetimedb') -s http://127.0.0.1:3000 --yes=skip-login --delete-data=never
  }
  'generate' {
    & $Cli --root-dir (Join-Path $Root '.spacetime') generate --lang typescript --module-path (Join-Path $Root 'spacetimedb\spacetimedb') --out-dir (Join-Path $Root 'frontend\src\spacetime') --yes
  }
}
