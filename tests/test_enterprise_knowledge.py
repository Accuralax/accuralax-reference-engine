from src.core.enterprise_knowledge import EnterpriseKnowledge


def test_knowledge_health():
    k = EnterpriseKnowledge()
    assert k.health()["status"] == "ok"
    assert k.health()["credentials_indexed"] is False


def test_source_verification_and_rag_retrieval():
    k = EnterpriseKnowledge()
    source = k.register_source("Official Policy", "policy", "authoritative", "Internal Governance")
    blocked = k.validate_source(source["source_id"])
    valid = k.validate_source(source["source_id"], verified=True)
    item = k.ingest("CyberFusion security policy and governance controls",
                    source["source_id"], "Security Policy")
    results = k.retrieve("security policy", minimum_trust="authoritative")
    assert blocked["allowed"] is False
    assert valid["status"] == "active"
    assert item["content_hash"]
    assert results[0]["knowledge_id"] == item["knowledge_id"]
    assert results[0]["trust"] == "authoritative"


def test_stale_and_dispute_governance():
    k = EnterpriseKnowledge()
    source = k.register_source("Research", "research", "high")
    k.validate_source(source["source_id"])
    item = k.ingest("Research finding", source["source_id"], "Research")
    stale = k.mark_stale(item["knowledge_id"])
    blocked = k.resolve_dispute(item["knowledge_id"])
    resolved = k.resolve_dispute(item["knowledge_id"], approved=True, human_reviewed=True)
    assert stale["status"] == "stale"
    assert blocked["allowed"] is False
    assert resolved["status"] == "validated"


def test_sensitive_collection():
    k = EnterpriseKnowledge()
    collection = k.create_collection("Executive Confidential", sensitive=True)
    assert collection["sensitive"] is True
