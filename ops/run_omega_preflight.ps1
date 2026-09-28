$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
$script = Join-Path (Get-Location) 'ops\omega_credential_preflight.py'
if (-not (Test-Path $python)) { throw 'Python runtime not found' }
& $python $script
exit $LASTEXITCODE
