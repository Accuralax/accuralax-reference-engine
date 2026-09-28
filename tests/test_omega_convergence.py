from src.core.omega_runtime_adapter import OmegaRuntimeAdapter
from src.core.canonical_worker import CanonicalOmegaWorker
from src.core.omega_governance_adapter import OmegaGovernanceAdapter
from src.core.agent_scheduler import AgentScheduler


def test_omega_adapters_fail_closed_without_credentials():
    runtime = OmegaRuntimeAdapter(url="", service_key="")
    governance = OmegaGovernanceAdapter(url="", service_key="")
    assert runtime.enabled is False
    assert governance.enabled is False
    try:
        runtime.health()
        assert False
    except RuntimeError as exc:
        assert str(exc) == "omega_runtime_not_configured"
    try:
        governance.request_approval("job")
        assert False
    except RuntimeError as exc:
        assert str(exc) == "omega_governance_not_configured"


def test_canonical_worker_degrades_safely_when_unconfigured():
    worker = CanonicalOmegaWorker(OmegaRuntimeAdapter(url="", service_key=""))
    assert worker.run_once()["status"] == "degraded"
    assert worker.health()["status"] == "degraded"
    assert worker.reconcile()["status"] == "degraded"


def test_canonical_worker_executes_lease_then_apex_with_mocked_adapter():
    class Fake:
        enabled = True
        def worker_tick(self, worker_code, limit): return {"status": "RUNNING", "worker_code": worker_code}
        def apex_tick(self): return {"status": "HEALTHY"}
        def health(self): return {"status": "HEALTHY"}
        def invariant_check(self): return {"status": "PASSED"}
    worker = CanonicalOmegaWorker(Fake())
    result = worker.run_once()
    assert result["status"] == "completed"
    assert result["lease"]["status"] == "RUNNING"
    assert result["result"]["status"] == "HEALTHY"
    assert worker.health()["omega"]["status"] == "HEALTHY"
    assert worker.reconcile()["status"] == "PASSED"


def test_scheduler_blocks_when_worker_is_not_ready(tmp_path):
    class NotReadyWorker:
        def health(self):
            return {"status": "degraded", "configured": False}
        def reconcile(self):
            raise AssertionError("reconcile must not run when worker is not ready")
    scheduler = AgentScheduler(NotReadyWorker(), db_path=str(tmp_path / "scheduler.sqlite3"))
    result = scheduler.start()
    assert result["status"] == "blocked"
    assert result["reason"] == "worker_not_ready"
