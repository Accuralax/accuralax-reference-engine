$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\mpume\aiagent'
$store=Join-Path (Get-Location) 'data\omega-credentials.dpapi'
if(-not (Test-Path $store)){Write-Output 'APEX_SUPERVISOR=DEGRADED_OMEGA_CREDENTIAL_STORE_MISSING'}
& '.\.venv\Scripts\python.exe' 'ops\apex_supervisor.py'
exit $LASTEXITCODE
