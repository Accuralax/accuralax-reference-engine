from src.core.langgraph_checkpoint import LangGraphCheckpointStore
from src.core.learning_loop import GovernedLearningLoop


def test_checkpoint_persists_and_is_secret_safe(tmp_path):
    store = LangGraphCheckpointStore(tmp_path / "checkpoints.sqlite3")
    cp = store.save("CFS-CP-1", "supervisor", {"status": "ready", "api_key": "hidden"})
    assert cp.state["status"] == "ready"
    assert "api_key" not in cp.state
    fresh = LangGraphCheckpointStore(tmp_path / "checkpoints.sqlite3")
    assert fresh.latest("CFS-CP-1").checkpoint_id == cp.checkpoint_id


def test_learning_loop_is_bounded_and_resumable(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    loop = GovernedLearningLoop(max_iterations=9)
    result = loop.run("CFS-LEARN-1", "cybersecurity_triage_agent",
                      {"status": "verified"}, "pass", verified=True)
    assert result["iterations"] <= 5
    assert result["learning_status"] == "consolidated"
    resumed = loop.resume("CFS-LEARN-1")
    assert resumed["resumable"] is True


def test_unverified_learning_does_not_consolidate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    loop = GovernedLearningLoop(max_iterations=3)
    result = loop.run("CFS-LEARN-2", "cybersecurity_triage_agent",
                      {"status": "pending"}, "needs review", verified=False)
    assert result["learning_status"] == "awaiting_verification"
    assert result["iterations"] == 1
