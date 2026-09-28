from src.core.unified_agent_brain import UnifiedAgentBrain


def test_unified_brain_has_memory_rag_and_skills():
    brain = UnifiedAgentBrain()
    context = brain.context("cybersecurity_triage_agent", "security incident")
    assert context["skills"]
    assert context["working_memory"] is not None
    assert context["persistent_memory"] is not None
    assert context["knowledge"] is not None
    assert context["governance"]["credentials_exposed"] is False


def test_experience_requires_validation_before_consolidation():
    brain = UnifiedAgentBrain()
    saved = brain.capture_experience(
        "cybersecurity_triage_agent", "security incident", "verified", "CFS-TEST-BRAIN"
    )
    assert saved["state"] == "candidate"
    validated = brain.validate_experience(saved["memory_id"])
    assert validated["state"] == "validated"
    consolidated = brain.memory.consolidate("cybersecurity_triage_agent")
    assert consolidated["consolidated"] >= 1


def test_secret_memory_rejected():
    brain = UnifiedAgentBrain()
    result = brain.memory.write(
        "cybersecurity_triage_agent", "semantic", "token=DO_NOT_STORE",
        scope=["cybersecurity"], provenance="test"
    )
    assert result["allowed"] is False
