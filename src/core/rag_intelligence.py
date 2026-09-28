from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import math
import re
import sqlite3
import uuid
import yaml

_SECRET = re.compile(r"(password|api[_-]?key|token|secret|cvv|card[_-]?number)", re.I)


class RAGIntelligenceEngine:
    """Persistent governed hybrid RAG: keyword + semantic proxy + freshness + authority + citations."""

    TRUST = {"unverified": 0.20, "low": 0.40, "medium": 0.60, "high": 0.80, "authoritative": 1.00}

    def __init__(self, db_path: str | Path = Path("data") / "rag_intelligence.sqlite3") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = yaml.safe_load(
            (Path(__file__).resolve().parents[1] / "config" / "enterprise_knowledge.yaml").read_text(encoding="utf-8")
        ) or {}
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY, name TEXT, source_type TEXT, trust TEXT,
                authority_verified INTEGER, created_at TEXT, updated_at TEXT
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY, source_id TEXT, document_id TEXT,
                content TEXT, content_hash TEXT, version INTEGER, created_at TEXT,
                updated_at TEXT, state TEXT, metadata TEXT
            )""")
            db.commit()

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _terms(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9_]{2,}", text.lower()))

    def register_source(self, name: str, source_type: str, trust: str = "medium",
                        authority_verified: bool = False) -> dict[str, Any]:
        if trust not in self.TRUST:
            return {"allowed": False, "reason": "invalid_trust"}
        if trust == "authoritative" and not authority_verified:
            return {"allowed": False, "reason": "authoritative_source_requires_verification"}
        now = datetime.now(timezone.utc).isoformat()
        source_id = f"SRC-{uuid.uuid4().hex[:10].upper()}"
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?)",
                       (source_id, name, source_type, trust, int(authority_verified), now, now))
            db.commit()
        return {"allowed": True, "source_id": source_id, "trust": trust, "authority_verified": authority_verified}

    def ingest(self, source_id: str, content: str, *, document_id: str | None = None,
               version: int = 1, metadata: str = "") -> dict[str, Any]:
        if _SECRET.search(content) or _SECRET.search(metadata):
            return {"allowed": False, "reason": "sensitive_content_rejected"}
        now = datetime.now(timezone.utc).isoformat()
        chunk_id = f"CHK-{uuid.uuid4().hex[:10].upper()}"
        doc_id = document_id or f"DOC-{uuid.uuid4().hex[:10].upper()}"
        with sqlite3.connect(self.db_path) as db:
            if not db.execute("SELECT 1 FROM sources WHERE source_id=?", (source_id,)).fetchone():
                return {"allowed": False, "reason": "source_not_found"}
            db.execute("INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?,?,?)",
                       (chunk_id, source_id, doc_id, content, self._hash(content), version,
                        now, now, "validated", metadata))
            db.commit()
        return {"allowed": True, "chunk_id": chunk_id, "document_id": doc_id,
                "content_hash": self._hash(content), "state": "validated"}

    def _freshness(self, updated_at: str) -> float:
        age_days = max(0.0, (datetime.now(timezone.utc) -
                             datetime.fromisoformat(updated_at)).total_seconds() / 86400)
        stale_after = float(self.config.get("knowledge", {}).get("controls", {}).get("stale_after_days", 90))
        return max(0.0, 1.0 - age_days / max(stale_after, 1.0))

    def retrieve(self, query: str, minimum_trust: str = "medium", limit: int = 10) -> list[dict[str, Any]]:
        threshold = self.TRUST.get(minimum_trust, 0.60)
        qterms = self._terms(query)
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute("""SELECT c.chunk_id,c.document_id,c.content,c.content_hash,c.version,
                                       c.updated_at,c.state,s.source_id,s.name,s.source_type,s.trust,
                                       s.authority_verified
                                FROM chunks c JOIN sources s ON s.source_id=c.source_id
                                WHERE c.state='validated'""").fetchall()
        results = []
        for row in rows:
            trust = self.TRUST[row[10]]
            if trust < threshold:
                continue
            terms = self._terms(row[2])
            keyword = len(qterms & terms) / max(len(qterms), 1)
            # Deterministic semantic proxy: weighted token overlap with character bigrams.
            qgrams = set(query.lower()[i:i+3] for i in range(max(0, len(query)-2)))
            cgrams = set(row[2].lower()[i:i+3] for i in range(max(0, len(row[2])-2)))
            semantic = len(qgrams & cgrams) / max(len(qgrams), 1)
            freshness = self._freshness(row[5])
            authority = trust * (1.0 if row[11] else 0.9)
            relevance = round(0.45 * semantic + 0.25 * keyword + 0.15 * freshness + 0.15 * authority, 6)
            if keyword == 0 and semantic < 0.05:
                continue
            results.append({
                "chunk_id": row[0], "document_id": row[1], "content": row[2],
                "content_hash": row[3], "version": row[4], "source_id": row[7],
                "source": row[8], "source_type": row[9], "trust": row[10],
                "authority_verified": bool(row[11]), "authority_score": round(authority, 4),
                "keyword_score": round(keyword, 4), "semantic_score": round(semantic, 4),
                "freshness_score": round(freshness, 4), "relevance_score": relevance,
                "stale": freshness <= 0.0,
                "citation": f"[{row[8]} | {row[0]} | v{row[4]} | {row[3][:12]}]"
            })
        return sorted(results, key=lambda x: x["relevance_score"], reverse=True)[:limit]

    def detect_contradictions(self, query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        conflicts = []
        for i, left in enumerate(results):
            for right in results[i + 1:]:
                if left["source_id"] == right["source_id"]:
                    continue
                common = self._terms(left["content"]) & self._terms(right["content"]) & self._terms(query)
                if len(common) >= 2 and left["content_hash"] != right["content_hash"]:
                    conflicts.append({"left": left["citation"], "right": right["citation"],
                                       "shared_terms": sorted(common), "requires_review": True})
        return conflicts

    def health(self) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            sources = db.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            chunks = db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        return {"status": "ok", "sources": sources, "chunks": chunks,
                "hybrid_retrieval": True, "reranking": True, "citations": True,
                "contradiction_detection": True, "credentials_indexed": False}
