from src.core.apex_runtime_bootstrap import ApexRuntimeBootstrap

def test_bootstrap_composes_real_omega_stages():
    r=ApexRuntimeBootstrap()
    assert set(r.stages)=={f"omega{i}" for i in range(8,16)}
    assert r.omega9 is r.stages["omega9"]
    assert r.health()["execution_authority"]=="omega9"
    assert r.health()["autonomous_development"]["proposal_boundary"] is True

def test_bootstrap_certification_is_runtime_gated():
    r=ApexRuntimeBootstrap()
    result=r.certify()
    assert result["release_allowed"] is True
    assert result["invariants"]["release_allowed"] is True
