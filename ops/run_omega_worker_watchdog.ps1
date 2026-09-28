$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$store=Join-Path (Get-Location) 'data\omega-credentials.dpapi'
if(-not (Test-Path $store)){Write-Output 'OMEGA_WORKER_START=BLOCKED_CREDENTIAL_STORE_MISSING'; exit 3}
$lines=Get-Content $store
$url=($lines | Where-Object {$_ -like 'URL=*'} | Select-Object -First 1).Substring(4)
$enc=($lines | Where-Object {$_ -like 'KEY=*'} | Select-Object -First 1).Substring(4)
if([string]::IsNullOrWhiteSpace($url) -or [string]::IsNullOrWhiteSpace($enc)){Write-Output 'OMEGA_WORKER_START=BLOCKED_CREDENTIAL_STORE_INVALID'; exit 3}
$secure=$enc | ConvertTo-SecureString
$bstr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try{$key=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr); $env:SUPABASE_URL=$url; $env:SUPABASE_SERVICE_ROLE_KEY=$key; & (Join-Path (Get-Location) '.venv\Scripts\python.exe') (Join-Path (Get-Location) 'ops\omega_worker_watchdog.py'); exit $LASTEXITCODE}
finally{if($bstr -ne [IntPtr]::Zero){[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)}; Remove-Item Env:SUPABASE_SERVICE_ROLE_KEY -ErrorAction SilentlyContinue; Remove-Item Env:SUPABASE_URL -ErrorAction SilentlyContinue}
