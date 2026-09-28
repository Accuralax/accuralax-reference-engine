from src.core.agent_knowledge_runtime import AgentKnowledgeRuntime


def test_all_permission_agents_have_brain_profiles():
    runtime = AgentKnowledgeRuntime()
    profiles = [runtime.brain.profile(agent) for agent in runtime.brain.agents]
    assert profiles
    assert all(p["memory_types"] for p in profiles)
    assert all(p["credentials_never_stored"] is True for p in profiles)
    assert all(p["skills"] for p in profiles)


def test_experience_learning_is_persisted():
    runtime = AgentKnowledgeRuntime()
    saved = runtime.learn_experience(
        "cybersecurity_triage_agent",
        "security incident",
        "pass",
        "CFS-TEST-001",
    )
    assert saved["allowed"] is True
    context = runtime.context("cybersecurity_triage_agent", "security incident")
    assert any(m["memory_id"] == saved["memory_id"] for m in context["memory"])
    assert context["credentials_exposed"] is False


def test_workspace_agentic_context():
    from src.core.agentic_workspace import AgenticWorkspace
    result = AgenticWorkspace().run("I need help with cybersecurity")
    assert result["active_agent"] == "cybersecurity_triage_agent"
    assert result["brain"]["skills"]
    assert result["brain"]["credentials_exposed"] is False
