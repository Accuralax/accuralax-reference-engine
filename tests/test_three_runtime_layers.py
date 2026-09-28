from src.core.continuous_runtime import ContinuousRuntime
from src.core.integration_control_plane import IntegrationControlPlane
from src.core.apex_regression_gate import ApexRegressionGate


class Worker:
    def __init__(self):
        self.calls = 0

    def run_once(self, tenant_id="", workspace_id=""):
        self.calls += 1
        return {"status": "completed", "call": self.calls}


def test_continuous_runtime_runs_bounded_ticks():
    worker = Worker()
    runtime = ContinuousRuntime(worker, interval_seconds=0)
    result = runtime.run(3)
    assert result["iterations"] == 3
    assert worker.calls == 3
    assert runtime.health()["ticks"] == 3


def test_integration_control_plane_delegates():
    class Integration:
        def health(self): return {"status": "ok"}
        def dispatch(self, *args, **kwargs): return {"status": "completed"}
        def retry(self, *args, **kwargs): return {"status": "completed"}
        def jobs(self, *args, **kwargs): return []

    plane = IntegrationControlPlane(Integration())
    assert plane.health()["status"] == "ok"
    assert plane.dispatch("t", "w", "c", "a")["status"] == "completed"


def test_apex_regression_gate_blocks_failed_check():
    gate = ApexRegressionGate()
    gate.register("convergence", lambda: {"status": "ok"})
    gate.register("regression", lambda: {"status": "failed"})
    result = gate.evaluate()
    assert result["release_allowed"] is False
    assert result["failed"] == 1
