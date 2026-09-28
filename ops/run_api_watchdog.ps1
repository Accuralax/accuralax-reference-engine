# Local API watchdog launcher for Windows Task Scheduler.
$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\mpume\aiagent'
& '.\.venv\Scripts\python.exe' 'ops\api_watchdog.py' '--interval' '15' '--startup-timeout' '30'
exit $LASTEXITCODE
