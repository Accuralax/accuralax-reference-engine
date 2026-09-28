from src.core.skill_execution import SkillExecutionRuntime, SkillSpec


def test_skill_scope_and_execution():
    rt = SkillExecutionRuntime()
    rt.register(SkillSpec("knowledge_lookup", "Knowledge Lookup", "knowledge",
                          handler=lambda query: {"answer": query}))
    result = rt.execute("knowledge_lookup", agent_id="supervisor",
                         scope="knowledge", args={"query": "pricing"})
    assert result["allowed"]
    assert result["verified"]


def test_skill_not_in_scope_is_blocked():
    rt = SkillExecutionRuntime()
    rt.register(SkillSpec("secret_skill", "Secret", "secret",
                          handler=lambda: {"ok": True}))
    result = rt.execute("secret_skill", agent_id="supervisor", scope="secret")
    assert result["reason"] == "skill_not_in_agent_scope"


def test_risky_skill_requires_approval_and_policy():
    rt = SkillExecutionRuntime()
    rt.register(SkillSpec("publish", "Publish", "publish",
                          handler=lambda: {"published": True}, external_side_effect=True))
    a = rt.execute("publish", agent_id="supervisor", scope="publish")
    assert a["reason"] == "approval_required"
    b = rt.execute("publish", agent_id="supervisor", scope="publish", approved=True)
    assert b["reason"] == "policy_check_required"
    c = rt.execute("publish", agent_id="supervisor", scope="publish",
                   approved=True, policy_checked=True)
    assert c["allowed"]
