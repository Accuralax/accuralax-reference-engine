from __future__ import annotations
from dataclasses import dataclass
from .capability import CAPABILITIES

@dataclass(frozen=True)
class ContractCase:
    name: str
    expected: str

CASES = (
    ContractCase("allowed_read","completed"),
    ContractCase("denied_unknown","denied"),
    ContractCase("credential_missing","failed"),
    ContractCase("retry_then_success","completed"),
)

def matrix() -> list[dict]:
    return [{"capability": key, "system": value.system, "action": value.action,
             "side_effect": value.side_effect,
             "cases":[c.__dict__.copy() for c in CASES]}
            for key, value in CAPABILITIES.items()]
