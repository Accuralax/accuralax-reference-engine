from __future__ import annotations

from typing import Any
import re


class EvidenceVerifier:
    """Evidence assessment layer. Retrieval is not treated as verification."""

    def verify(self, query: str, evidence: list[dict[str, Any]], memories: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        memories = memories or []
        usable = [e for e in evidence if e.get("source") and e.get("content_hash")]
        conflicts = [e for e in usable if e.get("state") == "disputed"]
        candidates = []
        for e in usable:
            support = self._support(query, e.get("content", ""))
            score = round(0.65 * e.get("score", 0) + 0.20 * e.get("trust_score", e.get("source_authority", 0)) + 0.15 * support, 6)
            candidates.append({
                "source": e["source"],
                "knowledge_id": e.get("knowledge_id"),
                "content_hash": e["content_hash"],
                "trust": e.get("trust"),
                "source_type": e.get("source_type"),
                "score": score,
                "support": round(support, 6),
                "freshness": e.get("freshness"),
                "provenance": e.get("metadata", {}).get("provenance", e.get("source")),
                "citation": {"source": e["source"], "knowledge_id": e.get("knowledge_id"), "content_hash": e["content_hash"]},
            })
        candidates.sort(key=lambda x: x["score"], reverse=True)
        if conflicts:
            status = "conflicting"
        elif not candidates:
            status = "insufficient_evidence"
        elif candidates[0]["score"] >= 0.70 and len(candidates) >= 1:
            status = "supported"
        else:
            status = "unverified"
        return {
            "verification_status": status,
            "requires_verification": status in ("unverified", "conflicting", "insufficient_evidence"),
            "evidence_count": len(candidates),
            "memory_evidence_count": len(memories),
            "conflicts": conflicts,
            "citation_candidates": candidates[:5],
        }

    @staticmethod
    def _support(query: str, content: str) -> float:
        q = set(re.findall(r"[a-z0-9_]{2,}", query.lower()))
        c = set(re.findall(r"[a-z0-9_]{2,}", content.lower()))
        return len(q & c) / max(len(q), 1)
