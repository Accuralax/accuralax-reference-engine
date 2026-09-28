from pathlib import Path
from typing import Any

import yaml


class MasterEntityRegistry:
    """Shared entity vocabulary and relationship registry."""

    def __init__(self, config_path: str | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        self.config_path = Path(config_path or root / "config" / "master_entities.yaml")
        with self.config_path.open("r", encoding="utf-8") as handle:
            self.schema: dict[str, Any] = yaml.safe_load(handle) or {}
        self.entities = self.schema.get("entities", {})
        self.identity = self.schema.get("identity", {})

    def get(self, entity_type: str) -> dict[str, Any] | None:
        return self.entities.get(entity_type)

    def list_entities(self) -> list[str]:
        return sorted(self.entities)

    def validate(self, entity_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        definition = self.get(entity_type)
        if definition is None:
            return {"valid": False, "errors": ["unknown_entity_type"]}
        key = definition["key"]
        errors: list[str] = []
        if self.identity.get("every_entity_requires_stable_key", True) and not payload.get(key):
            errors.append(f"missing:{key}")
        if self.identity.get("timestamps_required", True) and not payload.get("created_at"):
            errors.append("missing:created_at")
        return {"valid": not errors, "errors": errors, "entity_type": entity_type}

    def relationship(self, source: str, target: str) -> bool:
        definition = self.get(source)
        return bool(definition and target in definition.get("links", []))

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "entity_count": len(self.entities),
                "provenance_required": self.identity.get("provenance_required_for_knowledge", True),
                "credentials_must_never_be_entity_data": True}
