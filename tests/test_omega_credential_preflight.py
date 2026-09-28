from src.core import omega_runtime_adapter


# Load the standalone preflight without changing process credentials.
def test_preflight_blocks_missing_credentials(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    import importlib.util
    spec = importlib.util.spec_from_file_location("omega_preflight", "ops/omega_credential_preflight.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.check()
    assert result["status"] == "BLOCKED"
    assert "SUPABASE_URL_MISSING" in result["issues"]
    assert "SUPABASE_SERVICE_ROLE_KEY_MISSING" in result["issues"]


def test_preflight_accepts_https_and_nonempty_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "x" * 40)
    import importlib.util
    spec = importlib.util.spec_from_file_location("omega_preflight", "ops/omega_credential_preflight.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.check()["status"] == "READY"
