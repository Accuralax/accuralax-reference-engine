from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class CredentialState(str, Enum):
    AVAILABLE="available"
    MISSING="missing"
    INVALID="invalid"
    EXPIRED="expired"
    BLOCKED="blocked"

@dataclass(frozen=True)
class CredentialStatus:
    system: str
    state: CredentialState
    detail: str = ""
    live: bool = False

class CredentialStateMatrix:
    def __init__(self, provider):
        self.provider=provider
    def check(self, system: str) -> CredentialStatus:
        try:
            available=self.provider.has_credential(system)
        except Exception as exc:
            return CredentialStatus(system,CredentialState.BLOCKED,str(exc))
        if not available:
            return CredentialStatus(system,CredentialState.MISSING,"credential_not_configured")
        return CredentialStatus(system,CredentialState.AVAILABLE,"credential_present")
    def all(self, systems=("hubspot","make")):
        return {s:self.check(s) for s in systems}
