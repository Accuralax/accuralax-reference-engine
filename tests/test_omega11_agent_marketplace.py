from src.core.omega11_agent_marketplace import Omega11AgentMarketplace


def make(tmp_path):
    from src.core.agent_registry import AgentRegistry
    return Omega11AgentMarketplace(AgentRegistry(str(tmp_path / "agents.sqlite3")))


def test_registry_discovery_matching_and_routing(tmp_path):
    o=make(tmp_path)
    o.register_agent("t","w","compliance","Compliance",status="active",
                     capabilities=["compliance.assess"],allowed_skills=["risk"],allowed_tools=["report"])
    o.register_capability("t","w","compliance.assess")
    o.trust("t","w","compliance",score=.9)
    found=o.discover("t","w",capability="compliance.assess")
    assert found["count"]==1
    selected=o.select("t","w",{"capability":"compliance.assess"})
    assert selected["status"]=="selected"
    assert o.route("t","w",{"capability":"compliance.assess"})["execution_authority"]=="omega9"


def test_governed_delegation_and_bounds(tmp_path):
    o=make(tmp_path)
    o.register_agent("t","w","lead","Lead",status="active")
    o.register_agent("t","w","worker","Worker",status="active",capabilities=["x"])
    # Static permission registry may not contain this custom agent, so delegation fails closed.
    assert o.delegate("t","w","lead",{"capability":"x"})["status"]=="blocked"
    assert o.delegate("t","w","lead",{"capability":"x"},delegation_count=99)["reason"]=="delegation_limit"


def test_evaluation_publication_certification(tmp_path):
    o=make(tmp_path)
    o.register_agent("t","w","a","Agent",status="active",capabilities=["x"])
    ev=o.evaluate("t","w","a",passed=True,score=.95)
    assert o.publish("t","w","a",evaluation_id=ev["evaluation_id"],approved_by="admin",
                     certification={"certificate_id":"CERT-1"})["state"]=="published"
    assert o.certification("t","w","a")["certified"] is True


def test_tenant_isolation_and_lifecycle(tmp_path):
    o=make(tmp_path)
    o.register_agent("t1","w","a","One",status="active")
    o.register_agent("t2","w","a","Two",status="active")
    assert o.lifecycle("t1","w","a","deprecated")["status"]=="deprecated"
    assert o.registry.get_agent("t2","w","a")["status"]=="active"
    assert o.security_boundary("t1","w","a")["tenant_scoped"] is True


def test_health_readiness_and_lineage(tmp_path):
    o=make(tmp_path)
    o.register_agent("t","w","a","Agent",status="active",capabilities=["x"])
    o.select("t","w",{"capability":"x"})
    h=o.health()
    assert h["bounded"] and h["tenant_isolated"] and h["execution_authority"]=="omega9"
    assert o.lineage("t","w")
    assert o.release_gate()["release_allowed"] is True
