from src.core.agent_brain import AgentBrain


def test_agent_profile_has_scoped_skills_and_memory_types():
    brain = AgentBrain(db_path="data/test_agent_memory.sqlite3")
    profile = brain.profile("cybersecurity_triage_agent")
    assert "cybersecurity" in profile["domains"]
    assert "cybersecurity_triage" in profile["skills"]
    assert set(profile["memory_types"]) == {"working", "episodic", "semantic", "procedural"}


def test_memory_is_scoped_and_secret_safe():
    brain = AgentBrain(db_path="data/test_agent_memory_safe.sqlite3")
    saved = brain.remember("cybersecurity_triage_agent", "episodic",
                           "Reviewed security incident triage workflow",
                           domains=["cybersecurity"], provenance="test")
    assert saved["allowed"] is True
    found = brain.recall("cybersecurity_triage_agent", "security incident")
    assert found and found[0]["memory_id"] == saved["memory_id"]
    rejected = brain.remember("cybersecurity_triage_agent", "semantic",
                              "api_key=SHOULD_NOT_BE_STORED", provenance="test")
    assert rejected["allowed"] is False


def test_workspace_exposes_brain_and_skills():
    from src.core.agentic_workspace import AgenticWorkspace
    result = AgenticWorkspace().run("I need help with cybersecurity")
    assert result["brain"]["credentials_exposed"] is False
    assert "cybersecurity_triage" in result["brain"]["skills"]
    assert result["active_agent"] == "cybersecurity_triage_agent"
