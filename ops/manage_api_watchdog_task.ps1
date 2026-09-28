param([switch]$Install,[switch]$Remove,[switch]$Verify)
$ErrorActionPreference='Stop'
$Root=Split-Path -Parent $PSScriptRoot
$TaskName='CyberFusion AI API Watchdog'
$Launcher=Join-Path $Root 'ops\run_api_watchdog.ps1'
$Action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -ExecutionPolicy Bypass -File "'+$Launcher+'"')
$Trigger=New-ScheduledTaskTrigger -AtLogOn
$Settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero)
if($Install){
  try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description 'Keeps the local CyberFusion unified API healthy through the project watchdog.' -Force | Out-Null
    Write-Output 'TASK_INSTALL=OK'
  } catch {
    Write-Output 'TASK_INSTALL=FAILED'
    Write-Output ('TASK_INSTALL_REASON='+$_.Exception.Message)
    exit 1
  }
}
if($Remove){
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Output 'TASK_REMOVE=OK'
}
if($Verify -or (-not $Install -and -not $Remove)){
  $t=Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
  if($null -eq $t){Write-Output 'TASK_STATUS=NOT_REGISTERED'} else {Write-Output ('TASK_STATUS='+$t.State); Get-ScheduledTaskInfo -TaskName $TaskName | Select-Object LastRunTime,LastTaskResult,NextRunTime | Format-List}
}
