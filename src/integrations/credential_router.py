from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .credentials import CredentialProvider
from .adapters.base import AdapterResult, BusinessSystemAdapter


@dataclass(frozen=True)
class AdapterContext:
    system: str
    credential_available: bool


class CredentialAwareRouter:
    """Dispatches only through adapter boundaries; credentials never become payload/context."""

    def __init__(self, credential_provider: CredentialProvider, adapters: dict[str, BusinessSystemAdapter]) -> None:
        self.credentials = credential_provider
        self.adapters = adapters

    def context_for_adapter(self, system: str) -> AdapterContext:
        return AdapterContext(system, self.credentials.has_credential(system))

    def execute(self, system: str, action: str, payload: dict[str, Any] | None = None) -> AdapterResult:
        adapter = self.adapters.get(system)
        if not adapter:
            return AdapterResult(False, system, action, error="adapter_not_configured")
        # A real adapter may obtain the secret here, inside its own implementation.
        # The router deliberately passes no credential into agent-visible payloads.
        return adapter.execute(action, payload or {})
