from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from .capability import CAPABILITIES
from .credentials import CredentialProvider

@dataclass(frozen=True)
class ProviderHealth:
    system:str
    configured:bool
    adapter_present:bool
    capabilities:tuple[str,...]
    probe_status:str
    detail:str|None=None
    @property
    def credential_state(self): return "available" if self.configured else "missing"
    @property
    def contract_ok(self): return self.adapter_present and bool(self.capabilities)
    def public(self): return {"system":self.system,"configured":self.configured,"adapter_present":self.adapter_present,"capabilities":list(self.capabilities),"probe_status":self.probe_status,"detail":self.detail}

class ProviderHealthProbe:
    def __init__(self, credentials=None):
        self.credentials = credentials or CredentialProvider()
    def probe(self, system, adapter=None, capabilities=()):
        configured = self.credentials.has_credential(system)
        caps = tuple(capabilities)
        return ProviderHealth(system, configured, bool(adapter), caps, "ready" if configured else "credential_missing")

class ProviderHealthRegistry:
    def __init__(self,credentials=None,adapters=None):
        self.credentials=credentials or CredentialProvider(); self.adapters=adapters or {}
    def inspect(self,system,*,probe:Callable[[],Any]|None=None,live=False):
        caps=tuple(sorted(k for k,b in CAPABILITIES.items() if b.system==system)); configured=self.credentials.has_credential(system); present=system in self.adapters
        if not present: status="adapter_missing"
        elif live and probe is not None:
            try: status="healthy" if probe() is not False else "unhealthy"
            except Exception as exc: return ProviderHealth(system,configured,present,caps,"unhealthy",type(exc).__name__)
        else: status="ready" if configured else "credential_missing"
        return ProviderHealth(system,configured,present,caps,status)
    def inspect_all(self,*,live=False):
        systems=sorted(set(self.adapters)|{b.system for b in CAPABILITIES.values()})
        return [self.inspect(s,live=live).public() for s in systems]
