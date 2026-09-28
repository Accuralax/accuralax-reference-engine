# Operational runbook for the local-first API watchdog.

## Manual start
powershell.exe -ExecutionPolicy Bypass -File .\ops\run_api_watchdog.ps1

## Task Scheduler
Create a per-user task named `CyberFusion AI API Watchdog` that runs `ops\run_api_watchdog.ps1` at logon. Use the user's normal Windows account; do not store credentials in this repository. Configure restart-on-failure in Task Scheduler.

## Safety
- The watchdog only starts the API when the health endpoint is unreachable.
- It does not terminate unrelated Python processes.
- Keep the API bound to 127.0.0.1 for local operation.
- For internet-facing deployment, use authenticated mode and an HTTPS reverse proxy.

## Verification
`python .\ops\api_watchdog.py --once` should return 0 while the API is healthy.
