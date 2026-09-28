from pathlib import Path


def test_watchdog_launcher_requires_encrypted_store():
    text = Path('ops/run_omega_worker_watchdog.ps1').read_text(encoding='utf-8-sig')
    assert 'omega-credentials.dpapi' in text
    assert 'ConvertTo-SecureString' in text
    assert 'SUPABASE_SERVICE_ROLE_KEY' in text


def test_provisioner_uses_secure_prompt_and_dpapi():
    text = Path('ops/set_omega_credentials.ps1').read_text(encoding='utf-8-sig')
    assert 'Read-Host' in text and '-AsSecureString' in text
    assert 'ConvertFrom-SecureString' in text
    assert 'icacls.exe' in text
