from src.core.agent_registry import AgentRegistry
from src.core.model_gateway import ModelGateway


def test_agent_lifecycle_and_resolution(tmp_path):
    r = AgentRegistry(str(tmp_path / "registry.sqlite3"))
    a = r.register_agent("t1", "w1", "compliance_agent", "Compliance Agent", status="draft",
                         capabilities=["compliance.assess"], allowed_skills=["risk_assessment"],
                         allowed_tools=["compliance_report"])
    assert a["status"] == "draft"
    assert r.resolve("t1", "w1", "compliance_agent")["allowed"] is False
    assert r.set_status("t1", "w1", "compliance_agent", "active")["status"] == "active"
    assert r.resolve("t1", "w1", "compliance_agent", required_skill="risk_assessment")["allowed"] is True
    assert r.resolve("t1", "w1", "compliance_agent", required_skill="unknown")["reason"] == "skill_not_granted"


def test_skill_registry_and_health(tmp_path):
    r = AgentRegistry(str(tmp_path / "registry.sqlite3"))
    s = r.register_skill("t1", "w1", "risk_assessment", "Risk Assessment", dependencies=["knowledge_lookup"], permissions=["compliance.read"])
    assert s["skill_id"] == "risk_assessment"
    assert r.list_skills("t1", "w1")[0]["name"] == "Risk Assessment"
    h = r.health()
    assert h["durable"] and h["tenant_scoped"] and h["agents"] == 0 and h["skills"] == 1


def test_tenant_workspace_isolation(tmp_path):
    r = AgentRegistry(str(tmp_path / "registry.sqlite3"))
    r.register_agent("t1", "w1", "agent", "Tenant One", status="active")
    r.register_agent("t2", "w1", "agent", "Tenant Two", status="active")
    assert r.get_agent("t1", "w1", "agent")["name"] == "Tenant One"
    assert r.get_agent("t2", "w1", "agent")["name"] == "Tenant Two"
    assert r.get_agent("t1", "w2", "agent") is None


def test_default_registry_bootstraps_static_catalog():
    r = AgentRegistry()
    assert r.health()["agents"] >= 1
    assert r.health()["skills"] >= 1
    assert r.get_agent("default", "default", "supervisor")["status"] == "active"


def test_agent_model_resolution_is_governed(tmp_path):
    registry = AgentRegistry(str(tmp_path / "registry.sqlite3"))
    gateway = ModelGateway(str(tmp_path / "models.sqlite3"))
    gateway.register_policy("t", "w", "gen", "generation", allowed_models=["claude"], max_input_tokens=10)
    registry.register_agent("t", "w", "a", "A", status="active",
                            model_policy={"policy_id": "gen", "provider": "anthropic"})
    assert registry.resolve_model("t", "w", "a", gateway, input_tokens=5)["allowed"] is True
    assert registry.resolve_model("t", "w", "a", gateway, input_tokens=11)["reason"] == "input_budget_exceeded"


def test_invalid_status_blocked(tmp_path):
    r = AgentRegistry(str(tmp_path / "registry.sqlite3"))
    assert r.register_agent("t", "w", "a", "A", status="live")["reason"] == "invalid_status"
    assert r.register_skill("t", "w", "s", "S", status="live")["reason"] == "invalid_status"

def test_skill_marketplace_lifecycle(tmp_path):
    r=AgentRegistry(str(tmp_path/'registry.sqlite3'))
    s=r.register_skill('t','w','quality_skill','Quality Skill',version='1.0.0',status='draft')
    assert s['version']=='1.0.0'
    assert r.publish_skill('t','w','quality_skill','1.0.0')['reason']=='evaluation_and_approval_required'
    p=r.publish_skill('t','w','quality_skill','1.0.0',evaluation_id='EVAL-1',approved_by='admin')
    assert p['allowed']
    d=r.deploy_skill('t','w','quality_skill','1.0.0')
    assert d['allowed']
    assert r.retire_skill('t','w','quality_skill','1.0.0')['retired']==1
    assert r.deploy_skill('t','w','missing','1.0.0')['reason']=='skill_not_published'
