from pathlib import Path
import json
import os
import tempfile
from unittest.mock import patch

from ops.api_watchdog import acquire_lock, release_lock, healthy, status_snapshot, supervise


def test_health_success():
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
    with patch("urllib.request.urlopen", return_value=Response()):
        assert healthy("http://127.0.0.1:8788/health") is True


def test_health_failure():
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        assert healthy("http://127.0.0.1:8788/health") is False


def test_single_instance_lock():
    import ops.api_watchdog as watchdog
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp)
        with patch.object(watchdog, "STATE_DIR", state), patch.object(watchdog, "STATE_FILE", state / "state.json"), patch.object(watchdog, "LOCK_FILE", state / "watchdog.lock"):
            assert acquire_lock() is True
            assert acquire_lock() is False
            release_lock()
            assert acquire_lock() is True
            release_lock()


def test_state_file_round_trip():
    import ops.api_watchdog as watchdog
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp)
        with patch.object(watchdog, "STATE_DIR", state), patch.object(watchdog, "STATE_FILE", state / "state.json"):
            result = watchdog._write_state(status="healthy", restart_count=3)
            assert result["restart_count"] == 3
            assert json.loads((state / "state.json").read_text())["status"] == "healthy"


def test_status_snapshot_tracks_owned_child():
    import ops.api_watchdog as watchdog
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp)
        with patch.object(watchdog, "STATE_DIR", state), patch.object(watchdog, "STATE_FILE", state / "state.json"), patch.object(watchdog, "LOCK_FILE", state / "watchdog.lock"):
            (state / "state.json").write_text(json.dumps({"status": "healthy", "healthy": True, "child_pid": os.getpid(), "restart_count": 2}), encoding="utf-8")
            (state / "watchdog.lock").write_text(str(os.getpid()), encoding="utf-8")
            result = status_snapshot()
            assert result["watchdog_running"] is True
            assert result["child_alive"] is True
            assert result["restart_count"] == 2


def test_controlled_recovery_simulation_records_owned_recovery():
    import ops.api_watchdog as watchdog
    class FakeProcess:
        pid = 424242
        terminated = False
        def poll(self): return None
        def terminate(self): self.terminated = True

    process = FakeProcess()
    health_results = iter([False, True])
    events = []
    with tempfile.TemporaryDirectory() as tmp:
        state = Path(tmp)
        def fake_event(event, **details):
            events.append((event, details))
        with patch.object(watchdog, "STATE_DIR", state), patch.object(watchdog, "STATE_FILE", state / "state.json"), patch.object(watchdog, "LOCK_FILE", state / "watchdog.lock"), patch.object(watchdog, "EVENTS_FILE", state / "events.jsonl"), patch.object(watchdog, "_write_event", side_effect=fake_event):
            result = supervise("http://recovery.test/health", 0, 1, False, health_fn=lambda url: next(health_results), start_fn=lambda: process, sleep_fn=lambda _: None, max_cycles=1)
            saved = json.loads((state / "state.json").read_text(encoding="utf-8"))
            names = [name for name, _ in events]
            assert result == 0
            assert "health_failure" in names
            assert "recovery_started" in names
            assert "health_recovered" in names
            assert saved["child_pid"] == 424242
            assert saved["restart_count"] == 1
            assert saved["consecutive_failures"] == 0
            assert saved["healthy"] is True
            assert saved["status"] == "stopped"
            assert not (state / "watchdog.lock").exists()
            assert process.terminated is False
            assert names.count("health_recovered") == 1
