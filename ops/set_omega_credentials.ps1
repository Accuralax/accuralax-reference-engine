$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $PSScriptRoot
$Store=Join-Path $Root 'data\omega-credentials.dpapi'
New-Item -ItemType Directory -Force -Path (Split-Path $Store) | Out-Null
$url=Read-Host 'Supabase URL'
$key=Read-Host 'Supabase service-role key' -AsSecureString
if([string]::IsNullOrWhiteSpace($url)){throw 'Supabase URL is required'}
if($url -notmatch '^https://[^/]+$'){throw 'Supabase URL must be a single HTTPS origin'}
$enc=$key | ConvertFrom-SecureString
@("URL=$url","KEY=$enc") | Set-Content -Path $Store -Encoding UTF8
icacls.exe $Store /inheritance:r /grant:r "$env:USERNAME:F" | Out-Null
Write-Output 'OMEGA_CREDENTIAL_STORE=CREATED'
Write-Output 'OMEGA_CREDENTIALS=ENCRYPTED_DPAPI_USER_SCOPE'
