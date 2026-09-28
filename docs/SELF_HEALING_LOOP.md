# Controlled Self-Healing Loop

OBSERVE → DETECT → CLASSIFY → DIAGNOSE → PLAN → SANDBOX → TEST → APPROVE/POLICY GATE → APPLY → VERIFY → AUDIT → CONTINUE / ROLLBACK.

## Required controls
- Maximum repair attempts and graph iterations
- Agent/tool timeouts and token/tool budgets
- Circuit breakers
- Duplicate-incident suppression
- Idempotency keys
- Isolated patch/sandbox execution
- Regression-test gate
- Rollback capability
- Human approval for high-impact changes

## Example: RAG quality degradation
Detect a low retrieval/evaluation score → diagnose stale index or bad metadata → create repair plan → reindex in sandbox → run RAG evaluation → activate only if policy allows and quality improves → otherwise rollback → record an audit event.

## Loop detection
Repeated state/tool/action signatures are treated as a cycle. Stop the loop, preserve the trace, attempt only bounded recovery, then escalate if the recovery fails.

## Non-recursive authority
The repair agent cannot modify its own repair authority, safety rules, approval policy, credential store, or audit mechanism. Those changes require human approval.
