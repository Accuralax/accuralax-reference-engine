from src.core.rag_intelligence import RAGIntelligenceEngine


def test_persistent_hybrid_rag_and_citations(tmp_path):
    engine = RAGIntelligenceEngine(tmp_path / "rag.sqlite3")
    source = engine.register_source("CyberFusion Policy", "policy", "authoritative", True)
    assert source["allowed"]
    saved = engine.ingest(source["source_id"], "CyberFusion security policy requires human approval for destructive actions.", document_id="DOC-1")
    assert saved["allowed"]
    fresh = engine.retrieve("human approval destructive actions")
    assert fresh
    item = fresh[0]
    assert item["keyword_score"] > 0
    assert item["semantic_score"] > 0
    assert item["authority_score"] == 1.0
    assert item["citation"].startswith("[CyberFusion Policy")
    assert "content_hash" in item


def test_authority_and_secret_controls(tmp_path):
    engine = RAGIntelligenceEngine(tmp_path / "rag.sqlite3")
    blocked = engine.register_source("Unverified Authority", "policy", "authoritative", False)
    assert blocked["allowed"] is False
    source = engine.register_source("Research", "research", "high", True)
    rejected = engine.ingest(source["source_id"], "password=DO_NOT_STORE")
    assert rejected["allowed"] is False


def test_contradiction_detection(tmp_path):
    engine = RAGIntelligenceEngine(tmp_path / "rag.sqlite3")
    a = engine.register_source("Policy A", "policy", "high", True)
    b = engine.register_source("Policy B", "policy", "high", True)
    engine.ingest(a["source_id"], "Refund approval requires manager review.", document_id="A")
    engine.ingest(b["source_id"], "Refund approval requires director review.", document_id="B")
    results = engine.retrieve("refund approval review", minimum_trust="high")
    conflicts = engine.detect_contradictions("refund approval review", results)
    assert conflicts
    assert conflicts[0]["requires_review"] is True
