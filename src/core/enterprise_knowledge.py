from __future__ import annotations

import hashlib
import uuid
from typing import Any

from .event_lineage import EventLineage
from .governance_engine import GovernanceEngine


class EnterpriseKnowledge:
    """Governed enterprise knowledge, provenance and retrieval layer."""

    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}
        self.sources: dict[str, dict[str, Any]] = {}
        self.collections: dict[str, dict[str, Any]] = {}
        self.policy = GovernanceEngine()
        self.lineage = EventLineage()

    @staticmethod
    def content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def register_source(self, name: str, source_type: str, trust: str,
                        authority: str = "") -> dict[str, Any]:
        if not name.strip() or not source_type.strip():
            return {"allowed": False, "reason": "source_identity_required"}
        source_id = f"SRC-{uuid.uuid4().hex[:10].upper()}"
        item = {"source_id": source_id, "name": name, "source_type": source_type,
                "trust": trust, "authority": authority, "status": "discovered"}
        self.sources[source_id] = item
        return self._safe(item)

    def validate_source(self, source_id: str, verified: bool = False) -> dict[str, Any]:
        source = self.sources.get(source_id)
        if not source:
            return {"allowed": False, "reason": "source_not_found"}
        if source["trust"] == "authoritative" and not verified:
            return {"allowed": False, "reason": "authority_verification_required"}
        source["status"] = "active"
        return {"allowed": True, "source_id": source_id, "status": "active"}

    def ingest(self, content: str, source_id: str, title: str) -> dict[str, Any]:
        if not content.strip():
            return {"allowed": False, "reason": "content_required"}
        if source_id not in self.sources:
            return {"allowed": False, "reason": "source_not_found"}
        item_id = f"KNO-{uuid.uuid4().hex[:10].upper()}"
        item = {
            "knowledge_id": item_id, "title": title, "source_id": source_id,
            "content_hash": self.content_hash(content), "content": content,
            "status": "validated", "provenance": {"source_id": source_id},
        }
        self.items[item_id] = item
        self.lineage.record("knowledge.ingested", "system", "knowledge_item",
                            item_id, "knowledge", content_hash=item["content_hash"])
        return self._safe(item)

    def create_collection(self, name: str, sensitive: bool = False) -> dict[str, Any]:
        item = {"collection_id": f"COL-{uuid.uuid4().hex[:10].upper()}",
                "name": name, "sensitive": sensitive, "status": "active"}
        self.collections[item["collection_id"]] = item
        return self._safe(item)

    def retrieve(self, query: str, minimum_trust: str = "low") -> list[dict[str, Any]]:
        trust_order = {"unverified": 0, "low": 1, "medium": 2, "high": 3, "authoritative": 4}
        threshold = trust_order.get(minimum_trust, 1)
        terms = [x.lower() for x in query.split() if x.strip()]
        results = []
        for item in self.items.values():
            source = self.sources[item["source_id"]]
            if trust_order.get(source["trust"], 0) < threshold:
                continue
            haystack = f'{item["title"]} {item["content"]}'.lower()
            score = sum(term in haystack for term in terms)
            if score:
                results.append({"knowledge_id": item["knowledge_id"], "title": item["title"],
                                "score": score, "source_id": item["source_id"],
                                "trust": source["trust"], "content_hash": item["content_hash"]})
        return sorted(results, key=lambda x: x["score"], reverse=True)

    def mark_stale(self, knowledge_id: str) -> dict[str, Any]:
        item = self.items.get(knowledge_id)
        if not item:
            return {"allowed": False, "reason": "knowledge_not_found"}
        item["status"] = "stale"
        return {"allowed": True, "knowledge_id": knowledge_id, "status": "stale"}

    def resolve_dispute(self, knowledge_id: str, approved: bool = False, human_reviewed: bool = False) -> dict[str, Any]:
        item = self.items.get(knowledge_id)
        if not item:
            return {"allowed": False, "reason": "knowledge_not_found"}
        decision = self.policy.evaluate("disputed_source_resolution", approved=approved, human_reviewed=human_reviewed)
        if decision["outcome"] != "allowed":
            return {"allowed": False, "stage": "policy", "policy": decision}
        item["status"] = "validated"
        return {"allowed": True, "knowledge_id": knowledge_id, "status": "validated"}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "items": len(self.items), "sources": len(self.sources),
                "collections": len(self.collections), "credentials_indexed": False,
                "provenance_required": True, "lineage": self.lineage.health()}

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): EnterpriseKnowledge._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [EnterpriseKnowledge._safe(v) for v in value]
        return value
