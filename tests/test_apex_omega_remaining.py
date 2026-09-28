from src.core.runtime_recovery import RuntimeRecovery
from src.core.runtime_invariants import RuntimeInvariants


def test_failure_injection_recovers_with_reconciliation():
    recovery = RuntimeRecovery(max_attempts=2)
    calls = {"count": 0}

    def operation():
        calls["count"] += 1
        return {"status": "completed"} if calls["count"] == 2 else {"status": "failed"}

    result = recovery.recover("op-1", operation, reconcile=lambda: {"status": "ok"})
    assert result["status"] == "failed"
    assert result["reconciliation"]["status"] == "ok"
    result = recovery.recover("op-1", operation, reconcile=lambda: {"status": "ok"})
    assert result["status"] == "recovered"


def test_recovery_attempts_are_bounded():
    recovery = RuntimeRecovery(max_attempts=1)
    recovery.recover("op-2", lambda: {"status": "failed"})
    result = recovery.recover("op-2", lambda: {"status": "completed"})
    assert result["status"] == "blocked"
    assert result["reason"] == "recovery_attempt_limit"


def test_cross_layer_invariants_gate_release():
    invariants = RuntimeInvariants()
    invariants.register("healthy", lambda: {"status": "ok"})
    invariants.register("traceable", lambda: True)
    result = invariants.evaluate()
    assert result["release_allowed"] is True
    assert result["failed"] == 0


def test_cross_layer_invariant_blocks_release():
    invariants = RuntimeInvariants()
    invariants.register("healthy", lambda: {"status": "ok"})
    invariants.register("broken", lambda: {"status": "failed"})
    result = invariants.evaluate()
    assert result["release_allowed"] is False
    assert result["failed"] == 1
