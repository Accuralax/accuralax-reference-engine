from __future__ import annotations
import os
from typing import Callable

class HubSpotAdapter:
    """Fail-closed HubSpot boundary; transport is injectable for contract tests."""
    name = "hubspot"

    def __init__(self, transport: Callable | None = None, token: str | None = None):
        self._transport = transport
        self._token = token or os.getenv("HUBSPOT_ACCESS_TOKEN")

    def health(self) -> dict:
        return {"connector": self.name, "configured": bool(self._token),
                "transport_injected": self._transport is not None}

    def execute(self, action: str, payload: dict) -> dict:
        if not self._token and self._transport is None:
            raise RuntimeError("hubspot_credentials_not_configured")
        if self._transport is None:
            raise RuntimeError("hubspot_transport_not_configured")
        result = self._transport(action, payload, self._token)
        return {"connector": self.name, "action": action, "result": result}
