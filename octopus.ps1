# octopus — one-command launcher (Windows). Ensures deps, then starts the Ink CLI.
$ErrorActionPreference = 'Stop'
$cli = Join-Path $PSScriptRoot 'cli'
if (-not (Test-Path (Join-Path $cli 'node_modules'))) {
    Write-Host 'installing octopus deps (first run)...' -ForegroundColor Yellow
    npm --prefix $cli install
}
npm --prefix $cli start
