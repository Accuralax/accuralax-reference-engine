$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$script = Join-Path $root 'ops\run_omega_worker_watchdog.ps1'
$name = 'AccuraLax Omega Worker'
$action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$script`""
schtasks.exe /Create /TN $name /SC ONLOGON /TR $action /F | Out-Host
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Output "TASK_CREATED=$name"
Write-Output "TASK_ACTION=$script"
