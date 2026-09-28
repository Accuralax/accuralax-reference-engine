# APEX Parallel Mode

APEX execution no longer depends on a single serial verification bottleneck.

## Track A — Development
Continue implementation, production hardening, adapters, recovery, reconciliation,
observability, agent governance and autonomous runtime work.

## Track B — Verification
Use isolated pytest temporary roots. Preserve historical evidence. Run changed-code,
affected-subsystem, integration and full-regression layers independently.

## Track C — Production Readiness
Prepare manifests, contracts, local database validation and mock adapter validation.
Real credentials remain external gates and are never fabricated.

## Track D — Unattended Runtime
Preserve existing workers. Verify ownership before restart. Keep watchdog scripts
fail-closed. Windows scheduled-task registration remains an administrator action.

## Track E — Release Evidence
Every layer produces machine-readable evidence under data/apex_parallel/.
Historical 636-test evidence is retained until a fresh valid regression replaces it.

## Gate semantics
PASS means the checked layer actually passed. BLOCKED means an external prerequisite
is missing. FAIL means an executable verification failed. UNKNOWN means evidence is
insufficient. Production go-live remains fail-closed.

## Standard order
Layer 1 -> Layer 2 -> Layer 3 -> Layer 4 -> Layer 5 -> Layer 6.

Layers 1-3 can continue while Layer 4 is being repaired. Layers 5-6 remain gated by
their actual prerequisites.
