from __future__ import annotations

from pathlib import Path
from typing import Any
from datetime import datetime, timezone, timedelta
import hashlib
import json
import re
import sqlite3
import uuid
import yaml

_SECRET = re.compile(r"(password|api[_-]?key|token|secret|cvv|card[_-]?number)", re.I)


class PersistentMemory:
    """Governed persistent memory with provenance, confidence, scope and lifecycle."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        root = Path(__file__).resolve().parents[2]
        config = root / "src" / "config" / "memory_governance.yaml"
        self.config = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
        self.db_path = Path(db_path) if db_path else root / "data" / "persistent_memory.sqlite3"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, memory_type TEXT NOT NULL,
                content TEXT NOT NULL, scope TEXT NOT NULL, provenance TEXT NOT NULL,
                source_hash TEXT NOT NULL, confidence REAL NOT NULL, importance REAL NOT NULL,
                state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")
            db.commit()

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def write(self, agent_id: str, memory_type: str, content: str, *,
              scope: list[str], provenance: str, confidence: float = 0.5,
              importance: float = 0.5, validated: bool = False) -> dict[str, Any]:
        if memory_type not in self.config.get("memory", {}).get("types", []):
            return {"allowed": False, "reason": "invalid_memory_type"}
        if not scope or not provenance or not content.strip():
            return {"allowed": False, "reason": "scope_provenance_content_required"}
        if _SECRET.search(content):
            return {"allowed": False, "reason": "sensitive_memory_rejected"}
        now = datetime.now(timezone.utc).isoformat()
        memory_id = f"MEM-{uuid.uuid4().hex[:12].upper()}"
        state = "validated" if validated else "candidate"
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                       (memory_id, agent_id, memory_type, content, json.dumps(scope),
                        provenance, self._hash(content), max(0, min(1, confidence)),
                        max(0, min(1, importance)), state, now, now))
            db.commit()
        return {"allowed": True, "memory_id": memory_id, "state": state,
                "credentials_stored": False}

    def validate(self, memory_id: str, confidence: float = 0.8) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            row = db.execute("SELECT memory_id FROM memories WHERE memory_id=?", (memory_id,)).fetchone()
            if not row:
                return {"allowed": False, "reason": "memory_not_found"}
            db.execute("UPDATE memories SET state='validated', confidence=?, updated_at=? WHERE memory_id=?",
                       (max(0, min(1, confidence)), datetime.now(timezone.utc).isoformat(), memory_id))
            db.commit()
        return {"allowed": True, "memory_id": memory_id, "state": "validated"}

    def recall(self, agent_id: str, query: str, *, scope: list[str],
               limit: int = 10) -> list[dict[str, Any]]:
        if not scope:
            return []
        terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute(
                "SELECT memory_id,memory_type,content,scope,provenance,confidence,importance,state,created_at "
                "FROM memories WHERE agent_id=? AND state IN ('candidate','validated','consolidated') "
                "ORDER BY importance DESC, confidence DESC, created_at DESC", (agent_id,)
            ).fetchall()
        results = []
        for row in rows:
            row_scope = set(json.loads(row[3]))
            if row_scope and not (row_scope & set(scope)):
                continue
            relevance = sum(t in row[2].lower() for t in terms)
            if query and relevance == 0:
                continue
            results.append({"memory_id": row[0], "memory_type": row[1], "content": row[2],
                            "scope": list(row_scope), "provenance": row[4],
                            "confidence": row[5], "importance": row[6],
                            "state": row[7], "created_at": row[8], "relevance": relevance})
        results.sort(key=lambda x: (x["relevance"], x["importance"], datetime.fromisoformat(x["created_at"]).timestamp() if x["created_at"] else 0, x["confidence"]), reverse=True)
        return results[:limit]

    def consolidate(self, agent_id: str) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            count = db.execute(
                "SELECT COUNT(*) FROM memories WHERE agent_id=? AND state='validated'", (agent_id,)
            ).fetchone()[0]
            db.execute("UPDATE memories SET state='consolidated', updated_at=? WHERE agent_id=? AND state='validated'",
                       (datetime.now(timezone.utc).isoformat(), agent_id))
            db.commit()
        return {"allowed": True, "agent_id": agent_id, "consolidated": count}

    def retrieve_ranked(self, agent_id: str, query: str, *, scope: list[str], limit: int = 10) -> list[dict[str, Any]]:
        items = self.recall(agent_id, query, scope=scope, limit=limit * 3)
        now = datetime.now(timezone.utc)
        for item in items:
            try:
                age_hours = max((now - datetime.fromisoformat(item['created_at'])).total_seconds() / 3600.0, 0.0)
            except Exception:
                age_days = 365
            freshness = 1.0 / (1.0 + age_hours / 6.0)
            item['freshness'] = round(freshness, 4)
            relevance = min(item['relevance'] / max(len(query.split()), 1), 1)
            item['memory_score'] = round(0.40 * relevance + 0.20 * item['confidence'] + 0.15 * item['importance'] + 0.25 * freshness, 6)
        return sorted(items, key=lambda x: x['memory_score'], reverse=True)[:limit]

    def apply_decay(self, agent_id: str | None = None, days: int = 90) -> dict[str, Any]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as db:
            if agent_id:
                cur = db.execute("UPDATE memories SET state='stale', updated_at=? WHERE agent_id=? AND created_at<? AND state IN ('candidate','validated','consolidated')", (now, agent_id, cutoff))
            else:
                cur = db.execute("UPDATE memories SET state='stale', updated_at=? WHERE created_at<? AND state IN ('candidate','validated','consolidated')", (now, cutoff))
            db.commit()
        return {"allowed": True, "staled": cur.rowcount, "threshold_days": days}

    def health(self) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            count = db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        return {"status": "ok", "memory_count": count,
                "memory_types": self.config["memory"]["types"],
                "provenance_required": True, "credentials_stored": False}
