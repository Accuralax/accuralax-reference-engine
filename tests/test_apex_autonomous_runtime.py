from __future__ import annotations

import subprocess
from pathlib import Path

from src.core.autonomous_developer import AutonomousDeveloper
from src.core.supabase_runtime_adapter import SupabaseRuntimeAdapter
from src.core.apex_autonomous_runtime import ApexAutonomousRuntime


def test_autonomous_developer_inspects_and_selects_tests(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "tests" / "test_sample.py").write_text("def test_sample(): assert True\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    (tmp_path / "src" / "sample.py").write_text("VALUE = 2\n", encoding="utf-8")
    dev = AutonomousDeveloper(tmp_path)
    report = dev.inspect()
    assert "src/sample.py" in report["changed_files"]
    assert dev.select_tests(["src/sample.py"]) == ["tests/test_sample.py"]


def test_autonomous_developer_fails_closed_without_generator(tmp_path):
    dev = AutonomousDeveloper(tmp_path)
    result = dev.generate_patch({"category": "test_regression"}, {"python_files": []})
    assert result["status"] == "blocked"
    assert result["reason"] == "provider_generation_adapter_not_configured"


def test_supabase_adapter_is_fail_closed_without_credentials():
    adapter = SupabaseRuntimeAdapter(url="", service_key="")
    assert adapter.enabled is False
    assert adapter.health()["status"] == "degraded"


def test_apex_runtime_is_bounded_and_healthful(tmp_path):
    runtime = ApexAutonomousRuntime(tmp_path)
    health = runtime.health()
    assert health["execution_authority"] == "omega9"
    assert health["bounded"] is True
    assert health["fail_closed"] is True
