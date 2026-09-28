# APEX-J → APEX-T Production Certification

Date: 2026-09-28
Repository: Accuralax/accuralax-reference-engine

## Purpose

This is the canonical release-gate record for the final productionization track.

The platform is not considered production-ready merely because the regression suite passes. Each phase requires evidence, and the final gate fails closed when a mandatory external dependency or production control has not been verified.

## Phase gates

| Phase | Gate | Required evidence |
|---|---|---|
| APEX-J | Unattended runtime | Supervisor/watchdog, restart and recovery evidence |
| APEX-K | Environment convergence | Versioned configuration, deployment artifact, environment parity |
| APEX-L | Live integration | Supabase/API/worker plus HubSpot/Make boundary verification |
| APEX-M | Security | Authentication, authorization, secrets, tenant isolation, security regression |
| APEX-N | Observability | Health, metrics, logs, SLO/SLA, alert routing and dashboards |
| APEX-O | Recovery | Backup, restore, failure injection and recovery verification |
| APEX-P | Multi-tenancy | Tenant/workspace isolation and cross-tenant negative tests |
| APEX-Q | AI certification | Agent registry, evaluation suite, policy checks, regression and human escalation |
| APEX-R | Autonomous operations | Governed self-healing, bounded retries, approvals and audit lineage |
| APEX-S | Enterprise handover | Architecture, deployment, incident, recovery and operator runbooks |
| APEX-T | Go-live | All mandatory gates green and release evidence archived |

## Current verified evidence

- The local repository is on `main`.
- The resumable release runner records 170 test files / 636 tests passed in `data/apex_release_state.json`.
- A local watchdog/supervisor stack exists.
- A Supabase runtime adapter exists and targets the production control-plane schema.
- The Supabase project `AccuraLax Reference Engine` is active and healthy.
- The database contains the reference registry, control-plane, execution, recovery, observability, tenant, audit and AI-evaluation structures.
- RLS is enabled across the exposed public tables.

## Explicit production blockers

The following must not be represented as completed until verified with real production credentials and live traffic:

1. Production API authentication is configured and exercised.
2. Supabase runtime credentials are available to the production worker.
3. HubSpot credentials and boundary tests are active.
4. Make credentials/webhooks and boundary tests are active.
5. Production backup/restore has been executed and timed.
6. Cross-tenant negative tests have been executed against the live deployment.
7. AI production certification has been run against the production model/configuration.
8. Alert delivery has been verified end-to-end.
9. Operator handover has been accepted.

The local `.env.example` contains no secrets. Real secrets must remain outside Git and must never be copied into source, logs, reports or agent context.

## Security interpretation

Supabase reports many `RLS enabled with no policy` informational findings. This is a fail-closed posture for direct `anon`/`authenticated` access because RLS is enabled and no permissive policies exist. It must remain that way unless an explicit application access policy is designed, reviewed and tested. Service-role server operations must stay server-side.

## Go-live rule

`APEX-T = PASS` only when APEX-J through APEX-S have evidence-backed PASS states and all live external integrations, security, recovery, tenant isolation, AI evaluation and operations gates are verified.

If any mandatory gate is unknown, the release remains blocked.

## Operational command

Run the final local evidence collector from the repository root:

` .\\.venv\\Scripts\\python.exe ops\\apex_final_gate.py`

The generated report is written to:

`data/apex_jt_release_report.json`
