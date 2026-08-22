<#
.SYNOPSIS
  Pentest-POMDP lab control for Windows (PowerShell mirror of the Makefile).

.DESCRIPTION
  One-command lifecycle for the docker-compose lab. The Makefile stays canonical for
  Linux/CI/inside the agent; this wrapper gives the same targets on a Windows host that
  has no `make`.

.PARAMETER Command
  up | dev-up | down | build | config | shell-kali | shell-agent | logs | smoke | help

.PARAMETER Backend
  LLM backend / compose profile: local (RTX 5080, no egress) | api (hosted LLM). Default: local.

.EXAMPLE
  ./lab.ps1 up                 # full stack (local profile; pulls ollama on first run)
  ./lab.ps1 dev-up             # fast dev bring-up: kali + target + agent, no ollama
  ./lab.ps1 smoke              # run the agent->kali channel smoke test
  ./lab.ps1 down
  ./lab.ps1 up -Backend api
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('up','dev-up','down','build','config','shell-kali','shell-agent','logs','smoke','help')]
    [string]$Command = 'help',

    [ValidateSet('local','api')]
    [string]$Backend = 'local'
)

$ErrorActionPreference = 'Stop'

function Invoke-Compose {
    param([string[]]$ComposeArgs)   # NB: do not name this $Args (automatic variable)
    & docker compose --profile $Backend @ComposeArgs
    if ($LASTEXITCODE -ne 0) { throw "docker compose exited $LASTEXITCODE" }
}

switch ($Command) {
    'help' {
        Write-Host "Pentest-POMDP lab (Backend=$Backend). Commands:"
        Write-Host "  up           build + start full stack"
        Write-Host "  dev-up       start kali + target + agent only (no ollama)"
        Write-Host "  down         stop and remove the lab (all profiles)"
        Write-Host "  build        build images"
        Write-Host "  config       validate compose for the selected backend"
        Write-Host "  shell-kali   shell into kali-tools"
        Write-Host "  shell-agent  shell into agent"
        Write-Host "  logs         follow logs"
        Write-Host "  smoke        run agent->kali channel smoke test"
    }
    'config'      { Invoke-Compose @('config') }
    'build'       { Invoke-Compose @('build') }
    'up'          { Invoke-Compose @('up','-d','--build') }
    'dev-up'      { Invoke-Compose @('up','-d','--build','--no-deps','kali-tools','target','agent-local') }
    'down'        { & docker compose --profile local --profile api down }
    'logs'        { Invoke-Compose @('logs','-f') }
    'shell-kali'  { & docker exec -it kali-tools bash }
    'shell-agent' { & docker exec -it agent bash }
    'smoke'       { & docker exec agent python /app/docker/agent/smoke_channels.py }
}
