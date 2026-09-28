from __future__ import annotations
import os
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ops" / "omega_live_validation.py"


def test_live_validation_fails_closed_without_credentials(monkeypatch, capsys):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 3
    out = capsys.readouterr().out
    assert "OMEGA_LIVE_VALIDATION=BLOCKED" in out
    assert "CREDENTIALS_NOT_CONFIGURED" in out
    assert "SUPABASE_SERVICE_ROLE_KEY" not in out
