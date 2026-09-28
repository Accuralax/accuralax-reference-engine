from __future__ import annotations

from pathlib import Path
import subprocess

from src.core.apex_autonomous_development import ApexAutonomousDevelopment


def _runner(command, **kwargs):
    return subprocess.CompletedProcess(command, 0, "1 passed in 0.01s", "")


def test_autonomous_development_healthy_cycle_is_non_destructive(tmp_path):
    root = tmp_path
    (root / "src").mkdir()
    (root / "src" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    dev = ApexAutonomousDevelopment(root, runner=_runner)
    healthy = {"status": "healthy", "score": 100, "checks": []}
    result = dev.cycle(health_report=healthy)
    assert result["status"] == "healthy"
    assert (root / "src" / "sample.py").read_text(encoding="utf-8") == "VALUE = 1\n"


def test_protected_target_is_blocked(tmp_path):
    dev = ApexAutonomousDevelopment(tmp_path, runner=_runner)
    result = dev.propose("src/core/agent_permissions.py", "changed")
    assert result["status"] == "blocked"
    assert result["reason"] == "protected_target"


def test_candidate_requires_approval_after_sandbox_verification(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    dev = ApexAutonomousDevelopment(tmp_path, runner=_runner)
    proposal = dev.propose("src/sample.py", "VALUE = 2\n")
    cid = proposal["candidate"]["candidate_id"]
    verification = dev.sandbox_verify(cid)
    assert verification["verified"] is True
    blocked = dev.promote(cid, approved=False, verified=True)
    assert blocked["status"] == "blocked"
    assert blocked["reason"] == "approval_required"
    assert (tmp_path / "src" / "sample.py").read_text(encoding="utf-8") == "VALUE = 1\n"


def test_approved_verified_candidate_can_promote_with_rollback_capability(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    dev = ApexAutonomousDevelopment(tmp_path, runner=_runner)
    proposal = dev.propose("src/sample.py", "VALUE = 2\n")
    cid = proposal["candidate"]["candidate_id"]
    assert dev.sandbox_verify(cid)["verified"] is True
    approval = dev.approve(cid, "tester", approved=True)
    assert approval["status"] == "approved"
    promoted = dev.promote(cid, approved=True, verified=True)
    assert promoted["status"] == "promoted", promoted
    assert promoted["applied"] is True
    assert (tmp_path / "src" / "sample.py").read_text(encoding="utf-8") == "VALUE = 2\n"
