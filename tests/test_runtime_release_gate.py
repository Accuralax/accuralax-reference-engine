from src.core.runtime_release_gate import RuntimeReleaseGate


def test_release_gate_passes_all_green_checks():
    gate = RuntimeReleaseGate()
    gate.register("unit", lambda: True)
    gate.register("health", lambda: {"status": "ok"})
    result = gate.evaluate()
    assert result["release_allowed"] is True
    assert result["failed"] == 0


def test_release_gate_blocks_failed_checks():
    gate = RuntimeReleaseGate()
    gate.register("unit", lambda: True)
    gate.register("regression", lambda: {"status": "failed"})
    result = gate.evaluate()
    assert result["status"] == "blocked"
    assert result["release_allowed"] is False
    assert result["failed"] == 1
