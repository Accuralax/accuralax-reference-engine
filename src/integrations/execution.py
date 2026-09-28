from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionReceipt:
    execution_id: str
    idempotency_key: str
    system: str
    action: str
    status: str
    created_at: float
    attempt: int
    trace: tuple[str, ...] = ()
    error: str | None = None

    def public(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "idempotency_key": self.idempotency_key,
            "system": self.system,
            "action": self.action,
            "status": self.status,
            "created_at": self.created_at,
            "attempt": self.attempt,
            "trace": list(self.trace),
            "error": self.error,
        }


class ExecutionLedger:
    """Process-local idempotency ledger; designed to be replaceable by durable storage."""

    def __init__(self) -> None:
        self._receipts: dict[str, ExecutionReceipt] = {}

    def get(self, key: str) -> ExecutionReceipt | None:
        return self._receipts.get(key)

    def record(self, receipt: ExecutionReceipt) -> ExecutionReceipt:
        existing = self._receipts.get(receipt.idempotency_key)
        if existing:
            return existing
        self._receipts[receipt.idempotency_key] = receipt
        return receipt

    def fingerprint(self, system: str, action: str, payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(f"{system}|{action}|{canonical}".encode()).hexdigest()


class AuditedExecutor:
    """Exactly-once-at-most-per-idempotency-key execution boundary."""

    def __init__(self, ledger: ExecutionLedger | None = None) -> None:
        self.ledger = ledger or ExecutionLedger()

    def execute(self, system: str, action: str, idempotency_key: str, operation) -> ExecutionReceipt:
        if not idempotency_key:
            raise ValueError("idempotency_key is required")
        existing = self.ledger.get(idempotency_key)
        if existing:
            return existing
        execution_id = f"exec_{uuid.uuid4().hex}"
        trace = (f"execution:{execution_id}", f"system:{system}", f"action:{action}")
        try:
            operation()
            receipt = ExecutionReceipt(execution_id, idempotency_key, system, action, "succeeded", time.time(), 1, trace)
        except Exception as exc:
            receipt = ExecutionReceipt(execution_id, idempotency_key, system, action, "failed", time.time(), 1, trace, type(exc).__name__)
        return self.ledger.record(receipt)
