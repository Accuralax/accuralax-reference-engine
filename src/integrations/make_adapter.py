from __future__ import annotations
import os
from typing import Callable

class MakeAdapter:
    """Fail-closed Make.com boundary; transport is injectable for contract tests."""
    name = "make"

    def __init__(self, transport: Callable | None = None,
                 token: str | None = None, webhook: str | None = None):
        self._transport = transport
        self._token = token or os.getenv("MAKE_API_TOKEN")
        self._webhook = webhook or os.getenv("MAKE_WEBHOOK_URL")

    def health(self) -> dict:
        return {"connector": self.name,
                "configured": bool(self._token or self._webhook),
                "transport_injected": self._transport is not None}

    def execute(self, action: str, payload: dict) -> dict:
        if not (self._token or self._webhook) and self._transport is None:
            raise RuntimeError("make_credentials_not_configured")
        if self._transport is None:
            raise RuntimeError("make_transport_not_configured")
        result = self._transport(action, payload, self._token, self._webhook)
        return {"connector": self.name, "action": action, "result": result}
