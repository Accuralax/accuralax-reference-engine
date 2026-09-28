from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from .evidence_verifier import EvidenceVerifier


class DocumentEvidenceIntelligence:
    """Tenant-scoped document lifecycle and evidence intelligence foundation."""

    def __init__(self, db_path: str | None = None, verifier: EvidenceVerifier | None = None):
        self.db_path = db_path or os.path.join("data", "document_evidence.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self.verifier = verifier or EvidenceVerifier()
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS documents(
                document_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                title TEXT NOT NULL, document_type TEXT NOT NULL, status TEXT NOT NULL,
                current_version INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                UNIQUE(tenant_id,workspace_id,document_id))""")
            c.execute("""CREATE TABLE IF NOT EXISTS versions(
                document_id TEXT NOT NULL, version INTEGER NOT NULL, content TEXT NOT NULL,
                content_hash TEXT NOT NULL, metadata_json TEXT NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY(document_id,version))""")
            c.execute("""CREATE TABLE IF NOT EXISTS evidence(
                evidence_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                document_id TEXT NOT NULL, source TEXT NOT NULL, content_hash TEXT NOT NULL,
                state TEXT NOT NULL, verified INTEGER NOT NULL, metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL)""")

    def _db(self):
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _scope(tenant_id: str, workspace_id: str) -> tuple[str, str]:
        if not tenant_id or not workspace_id:
            raise ValueError("tenant_id_and_workspace_id_required")
        return str(tenant_id), str(workspace_id)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def register_document(self, tenant_id: str, workspace_id: str, title: str,
                           document_type: str, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        tenant_id, workspace_id = self._scope(tenant_id, workspace_id)
        if not title.strip() or not document_type.strip() or not content.strip():
            return {"allowed": False, "reason": "document_fields_required"}
        document_id = f"DOC-{uuid.uuid4().hex[:12].upper()}"
        now = self._now()
        digest = self._hash(content)
        with self._db() as c:
            c.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?)",
                      (document_id, tenant_id, workspace_id, title, document_type, "active", 1, now, now))
            c.execute("INSERT INTO versions VALUES(?,?,?,?,?,?)",
                      (document_id, 1, content, digest, json.dumps(metadata or {}), now))
        return {"document_id": document_id, "version": 1, "content_hash": digest, "status": "active"}

    def add_version(self, tenant_id: str, workspace_id: str, document_id: str,
                    content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        tenant_id, workspace_id = self._scope(tenant_id, workspace_id)
        if not content.strip():
            return {"allowed": False, "reason": "content_required"}
        with self._db() as c:
            row = c.execute("SELECT current_version FROM documents WHERE document_id=? AND tenant_id=? AND workspace_id=?",
                            (document_id, tenant_id, workspace_id)).fetchone()
            if not row:
                return {"allowed": False, "reason": "document_not_found"}
            version = int(row[0]) + 1
            now = self._now()
            digest = self._hash(content)
            c.execute("INSERT INTO versions VALUES(?,?,?,?,?,?)",
                      (document_id, version, content, digest, json.dumps(metadata or {}), now))
            c.execute("UPDATE documents SET current_version=?,updated_at=? WHERE document_id=? AND tenant_id=? AND workspace_id=?",
                      (version, now, document_id, tenant_id, workspace_id))
        return {"document_id": document_id, "version": version, "content_hash": digest}

    def link_evidence(self, tenant_id: str, workspace_id: str, document_id: str,
                      source: str, content_hash: str, verified: bool = False,
                      state: str = "unverified", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        tenant_id, workspace_id = self._scope(tenant_id, workspace_id)
        with self._db() as c:
            exists = c.execute("SELECT 1 FROM documents WHERE document_id=? AND tenant_id=? AND workspace_id=?",
                               (document_id, tenant_id, workspace_id)).fetchone()
            if not exists:
                return {"allowed": False, "reason": "document_not_found"}
            evidence_id = f"EVD-{uuid.uuid4().hex[:12].upper()}"
            c.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (evidence_id, tenant_id, workspace_id, document_id, source, content_hash,
                       state, int(bool(verified)), json.dumps(metadata or {}), self._now()))
        return {"evidence_id": evidence_id, "document_id": document_id, "verified": bool(verified), "state": state}

    def verify(self, tenant_id: str, workspace_id: str, query: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        tenant_id, workspace_id = self._scope(tenant_id, workspace_id)
        scoped = [e for e in evidence if e.get("tenant_id", tenant_id) == tenant_id and e.get("workspace_id", workspace_id) == workspace_id]
        result = self.verifier.verify(query, scoped)
        result["tenant_id"] = tenant_id
        result["workspace_id"] = workspace_id
        return result

    def get_document(self, tenant_id: str, workspace_id: str, document_id: str) -> dict[str, Any]:
        tenant_id, workspace_id = self._scope(tenant_id, workspace_id)
        with self._db() as c:
            doc = c.execute("SELECT document_id,title,document_type,status,current_version,created_at,updated_at FROM documents WHERE document_id=? AND tenant_id=? AND workspace_id=?",
                            (document_id, tenant_id, workspace_id)).fetchone()
            if not doc:
                return {"allowed": False, "reason": "document_not_found"}
            versions = c.execute("SELECT version,content_hash,metadata_json,created_at FROM versions WHERE document_id=? ORDER BY version",
                                 (document_id,)).fetchall()
            evidence = c.execute("SELECT evidence_id,source,state,verified,content_hash,created_at FROM evidence WHERE document_id=? AND tenant_id=? AND workspace_id=?",
                                 (document_id, tenant_id, workspace_id)).fetchall()
        return {"document": dict(zip(("document_id","title","document_type","status","current_version","created_at","updated_at"), doc)),
                "versions": [dict(zip(("version","content_hash","metadata","created_at"), (v[0],v[1],json.loads(v[2]),v[3]))) for v in versions],
                "evidence": [dict(zip(("evidence_id","source","state","verified","content_hash","created_at"), e)) for e in evidence]}

    def health(self) -> dict[str, Any]:
        with self._db() as c:
            documents = c.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            versions = c.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
            evidence = c.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        return {"status": "ok", "documents": documents, "versions": versions, "evidence": evidence,
                "tenant_scoped": True, "verification": True, "content_hashing": "sha256"}
