from src.core.runtime_control_plane import RuntimeControlPlane


def test_control_plane_readiness_requires_health_and_release():
    plane = RuntimeControlPlane()
    plane.register_check("runtime", lambda: {"status": "ok"})
    result = plane.readiness()
    assert result["status"] == "ready"
    assert result["release"]["release_allowed"] is True


def test_control_plane_release_blocks_failed_gate():
    plane = RuntimeControlPlane()
    plane.register_check("runtime", lambda: {"status": "failed"})
    result = plane.release()
    assert result["status"] == "blocked"
    assert result["release_allowed"] is False
