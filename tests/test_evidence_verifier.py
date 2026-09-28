from src.core.evidence_verifier import EvidenceVerifier

def test_no_evidence_requires_verification():
    result = EvidenceVerifier().verify("tax compliance", [])
    assert result["verification_status"] == "insufficient_evidence"
    assert result["requires_verification"] is True

def test_strong_evidence_is_supported():
    result = EvidenceVerifier().verify("tax compliance", [{
        "source": "official-regulation",
        "knowledge_id": "KNO-1",
        "content_hash": "abc",
        "trust": "authoritative",
        "source_type": "regulation",
        "score": 0.95,
        "source_authority": 1.0,
        "freshness": 1.0,
        "content": "Tax compliance requirements apply to registered businesses."
    }])
    assert result["verification_status"] == "supported"
    assert result["citation_candidates"][0]["content_hash"] == "abc"
