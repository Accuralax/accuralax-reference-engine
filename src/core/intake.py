from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ClientType(str, Enum):
    INDIVIDUAL = "individual"
    STARTUP = "startup"
    SME = "sme"
    LARGE_BUSINESS = "large_business"
    NPO_NPC = "npo_npc"
    SCHOOL_EDUCATION = "school_education"
    GOVERNMENT = "government"
    CORPORATE = "corporate"
    PROFESSIONAL = "professional"
    COMMUNITY_ORGANISATION = "community_organisation"
    OTHER = "other"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IntakeResult:
    intent: str
    client_type: ClientType
    service_area: str
    missing_information: tuple[str, ...] = ()


def classify_client_type(value: str | None) -> ClientType:
    """Normalize a known client-type value without guessing from sensitive data."""
    if not value:
        return ClientType.UNKNOWN
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "business": ClientType.SME,
        "small_medium_business": ClientType.SME,
        "npo": ClientType.NPO_NPC,
        "npc": ClientType.NPO_NPC,
        "education": ClientType.SCHOOL_EDUCATION,
        "school": ClientType.SCHOOL_EDUCATION,
        "community": ClientType.COMMUNITY_ORGANISATION,
    }
    if normalized in aliases:
        return aliases[normalized]
    try:
        return ClientType(normalized)
    except ValueError:
        return ClientType.OTHER
