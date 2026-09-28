from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path

from .conversation import ConversationState


_SECRET_FIELD_WORDS = ("password", "api_key", "apikey", "token", "secret", "card_number", "cvv")


def _safe_collected(values: dict[str, str]) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, value in values.items():
        normalized = key.strip().lower().replace("-", "_")
        if any(word in normalized for word in _SECRET_FIELD_WORDS):
            raise ValueError(f"Refusing to persist sensitive field: {key!r}")
        safe[key] = value
    return safe


class ConversationStore(ABC):
    @abstractmethod
    def save(self, state: ConversationState) -> None:
        raise NotImplementedError

    @abstractmethod
    def load(self, reference_id: str) -> ConversationState | None:
        raise NotImplementedError


class InMemoryConversationStore(ConversationStore):
    def __init__(self) -> None:
        self._items: dict[str, ConversationState] = {}

    def save(self, state: ConversationState) -> None:
        state.collected = _safe_collected(state.collected)
        self._items[state.reference_id] = state

    def load(self, reference_id: str) -> ConversationState | None:
        return self._items.get(reference_id)


class SQLiteConversationStore(ConversationStore):
    """Durable local session store. Secrets are rejected before persistence."""

    def __init__(self, path: Path | str = Path("data") / "sessions.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=15.0)
        conn.execute("PRAGMA busy_timeout=15000")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    reference_id TEXT PRIMARY KEY,
                    request TEXT NOT NULL,
                    service_id TEXT,
                    service_name TEXT,
                    required_fields TEXT NOT NULL,
                    collected TEXT NOT NULL,
                    consent_given INTEGER NOT NULL,
                    owner_assigned INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def save(self, state: ConversationState) -> None:
        collected = _safe_collected(state.collected)
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO conversation_sessions
                (reference_id, request, service_id, service_name, required_fields,
                 collected, consent_given, owner_assigned, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(reference_id) DO UPDATE SET
                    request=excluded.request,
                    service_id=excluded.service_id,
                    service_name=excluded.service_name,
                    required_fields=excluded.required_fields,
                    collected=excluded.collected,
                    consent_given=excluded.consent_given,
                    owner_assigned=excluded.owner_assigned,
                    status=excluded.status,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    state.reference_id,
                    state.request,
                    state.service_id,
                    state.service_name,
                    json.dumps(list(state.required_fields)),
                    json.dumps(collected),
                    int(state.consent_given),
                    int(state.owner_assigned),
                    state.status,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def load(self, reference_id: str) -> ConversationState | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM conversation_sessions WHERE reference_id = ?",
                (reference_id,),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None
        return ConversationState(
            request=row["request"],
            reference_id=row["reference_id"],
            service_id=row["service_id"],
            service_name=row["service_name"],
            required_fields=tuple(json.loads(row["required_fields"])),
            collected=json.loads(row["collected"]),
            consent_given=bool(row["consent_given"]),
            owner_assigned=bool(row["owner_assigned"]),
            status=row["status"],
        )
