from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re
import sqlite3
import uuid

import yaml

_SECRET = re.compile(r"(password|api[_-]?key|token|secret|cvv|card[_-]?number)", re.I)


class AgentBrain:
    """Scoped working, episodic, semantic and procedural memory for agents."""

    def __init__(self, config_path: str | None = None, db_path: str | Path = Path("data") / "agent_memory.sqlite3") -> None:
        root = Path(__file__).resolve().parents[1]
        path = Path(config_path or root / "config" / "agent_brains.yaml")
        self.config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self.agents = self.config.get("agents", {})
        permissions_path = root / "config" / "agent_permissions.yaml"
        if permissions_path.exists():
            permissions = yaml.safe_load(permissions_path.read_text(encoding="utf-8")) or {}
            for agent_id, profile in permissions.get("agents", {}).items():
                self.agents.setdefault(agent_id, {
                    "domains": [self._domain_from_agent(agent_id)],
                    "skills": profile.get("allowed_skills", []),
                })
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @staticmethod
    def _domain_from_agent(agent_id: str) -> str:
        name = agent_id.replace("_agent", "").replace("_supervisor", "")
        return name.split("_")[0] if name else "general"

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS agent_memory (
                memory_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, memory_type TEXT NOT NULL,
                content TEXT NOT NULL, domains TEXT NOT NULL, provenance TEXT NOT NULL,
                importance REAL NOT NULL DEFAULT 0.5, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            db.commit()

    def profile(self, agent_id: str) -> dict[str, Any]:
        profile = self.agents.get(agent_id, {})
        return {"agent_id": agent_id, "domains": profile.get("domains", []),
                "skills": profile.get("skills", []), "memory_types": self.config.get("memory_types", []),
                "credentials_never_stored": True}

    def remember(self, agent_id: str, memory_type: str, content: str,
                 domains: list[str] | None = None, provenance: str = "runtime",
                 importance: float = 0.5) -> dict[str, Any]:
        if memory_type not in self.config.get("memory_types", []):
            return {"allowed": False, "reason": "invalid_memory_type"}
        if _SECRET.search(content):
            return {"allowed": False, "reason": "sensitive_memory_rejected"}
        if not provenance:
            return {"allowed": False, "reason": "provenance_required"}
        memory_id = f"MEM-{uuid.uuid4().hex[:10].upper()}"
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO agent_memory(memory_id,agent_id,memory_type,content,domains,provenance,importance) VALUES(?,?,?,?,?,?,?)",
                       (memory_id, agent_id, memory_type, content,
                        json.dumps(domains or self.profile(agent_id)["domains"]),
                        provenance, max(0.0, min(1.0, importance))))
            db.commit()
        return {"allowed": True, "memory_id": memory_id, "agent_id": agent_id, "memory_type": memory_type}

    def recall(self, agent_id: str, query: str = "", memory_type: str | None = None,
               limit: int = 5) -> list[dict[str, Any]]:
        profile = self.profile(agent_id)
        domains = set(profile["domains"])
        terms = {x.lower() for x in re.findall(r"[a-z0-9_]+", query.lower())}
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute("SELECT memory_id,memory_type,content,domains,provenance,importance,created_at FROM agent_memory WHERE agent_id=? ORDER BY importance DESC, created_at DESC",
                              (agent_id,)).fetchall()
        results = []
        for row in rows:
            row_domains = set(json.loads(row[3]))
            if domains and row_domains and not (domains & row_domains):
                continue
            if memory_type and row[1] != memory_type:
                continue
            score = sum(term in row[2].lower() for term in terms)
            if query and score == 0:
                continue
            results.append({"memory_id": row[0], "memory_type": row[1], "content": row[2],
                            "domains": list(row_domains), "provenance": row[4],
                            "importance": row[5], "created_at": row[6], "relevance": score})
            if len(results) >= limit:
                break
        return results

    def relevant_context(self, agent_id: str, query: str, limit: int = 5) -> dict[str, Any]:
        profile = self.profile(agent_id)
        memories = self.recall(agent_id, query, limit=limit)
        return {"agent": profile, "memories": memories, "skills": profile["skills"],
                "policy": {"credentials_exposed": False, "policy_overrides_memory": True}}

    def health(self) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            count = db.execute("SELECT COUNT(*) FROM agent_memory").fetchone()[0]
        return {"status": "ok", "agent_profiles": len(self.agents),
                "memory_count": count, "memory_types": self.config.get("memory_types", []),
                "credentials_stored": False}
