from pathlib import Path

from src.core.hybrid_context_engine import HybridContextEngine
from src.core.persistent_memory import PersistentMemory
from src.core.knowledge_rag import KnowledgeRAG
from src.core.context_graph import TemporalContextGraph


def test_hybrid_assembles_sources(tmp_path: Path):
    memory = PersistentMemory(tmp_path / "m.sqlite3")
    rag = KnowledgeRAG(db_path=tmp_path / "k.sqlite3")
    graph = TemporalContextGraph(tmp_path / "g.sqlite3")
    memory.write("business_supervisor_agent", "episodic", "customer needs training support",
                 scope=["business"], provenance="test", confidence=.8)
    rag.ingest("Training management system policy", source="policy",
               trust="high", tenant_id="t1", workspace_id="w1")
    graph.add_fact("t1", "w1", "client-1", "enrolled_in", "course-1",
                   source="test", confidence=.9)
    engine = HybridContextEngine(memory=memory, rag=rag, graph=graph)
    result = engine.build("business_supervisor_agent", "training support", tenant_id="t1",
                          workspace_id="w1", entity_id="client-1")
    assert result["allowed"] is True
    assert result["tenant_id"] == "t1"
    assert any(x["source_type"] == "persistent_memory" for x in result["items"])
    assert any(x["source_type"] == "knowledge_rag" for x in result["items"])
    assert any(x["source_type"] == "temporal_graph" for x in result["items"])
def test_hybrid_enforces_tenant_workspace_for_rag_and_graph(tmp_path: Path):
    rag = KnowledgeRAG(db_path=tmp_path / "k.sqlite3")
    graph = TemporalContextGraph(tmp_path / "g.sqlite3")
    rag.ingest("private tenant policy", source="private", trust="high",
               tenant_id="t1", workspace_id="w1")
    graph.add_fact("t1", "w1", "agent-a", "knows", "secret-client",
                   source="test", confidence=.9)
    engine = HybridContextEngine(rag=rag, graph=graph)
    result = engine.build("supervisor", "private policy", tenant_id="t2",
                          workspace_id="w2")
    assert result["allowed"] is True
    assert result["knowledge"] == []
    assert result["graph"] == []
    assert result["governance"]["credentials_exposed"] is False


def test_hybrid_rejects_missing_identity_scope(tmp_path: Path):
    engine = HybridContextEngine(
        memory=PersistentMemory(tmp_path / "m.sqlite3"),
        rag=KnowledgeRAG(db_path=tmp_path / "k.sqlite3"),
        graph=TemporalContextGraph(tmp_path / "g.sqlite3"),
    )
    result = engine.build("", "request", tenant_id="t", workspace_id="w")
    assert result == {"allowed": False, "reason": "identity_scope_request_required"}
