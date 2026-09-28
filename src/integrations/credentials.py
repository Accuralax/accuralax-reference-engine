from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CredentialRef:
    system: str
    env_var: str


class CredentialProvider:
    """Integration-only credential access. Secret values never enter agent state."""

    REFS = {
        "hubspot": CredentialRef("hubspot", "HUBSPOT_ACCESS_TOKEN"),
        "make": CredentialRef("make", "MAKE_API_TOKEN"),
        "whatsapp": CredentialRef("whatsapp", "WHATSAPP_ACCESS_TOKEN"),
        "qx": CredentialRef("qx", "QX_API_TOKEN"),
        "wolas": CredentialRef("wolas", "WOLAS_API_TOKEN"),
    }

    def has_credential(self, system: str) -> bool:
        ref = self.REFS.get(system)
        return bool(ref and os.getenv(ref.env_var))

    def get_for_adapter(self, system: str) -> str:
        ref = self.REFS.get(system)
        if not ref:
            raise KeyError(f"No credential binding for {system!r}")
        value = os.getenv(ref.env_var)
        if not value:
            raise RuntimeError(f"Credential not configured for {system}")
        return value

    def describe(self, system: str) -> dict[str, str | bool]:
        ref = self.REFS.get(system)
        if not ref:
            return {"system": system, "configured": False}
        return {"system": system, "configured": self.has_credential(system), "env_var": ref.env_var}
