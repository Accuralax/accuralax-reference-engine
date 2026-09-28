from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


ASSET_TYPES = {"computer", "laptop", "printer", "server", "network_device", "mobile", "iot", "software", "other"}
ASSET_STATUSES = {"planned", "active", "maintenance", "retired", "disposed"}


@dataclass
class ITAsset:
    asset_id: str
    asset_type: str
    name: str
    owner: str | None = None
    location: str | None = None
    status: str = "active"
    serial_number: str | None = None
    warranty_until: str | None = None
    parent_asset_id: str | None = None
    related_asset_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ITAssetManager:
    """Local CMDB-style asset registry. Credentials and secrets are never stored."""

    def __init__(self) -> None:
        self.assets: dict[str, ITAsset] = {}
        self.ticket_links: dict[str, set[str]] = {}

    def create_asset(
        self,
        asset_type: str,
        name: str,
        *,
        owner: str | None = None,
        location: str | None = None,
        status: str = "active",
        serial_number: str | None = None,
        warranty_until: str | None = None,
        parent_asset_id: str | None = None,
    ) -> ITAsset:
        if asset_type not in ASSET_TYPES:
            raise ValueError("invalid_asset_type")
        if status not in ASSET_STATUSES:
            raise ValueError("invalid_asset_status")
        if not name.strip():
            raise ValueError("asset_name_required")
        if parent_asset_id and parent_asset_id not in self.assets:
            raise ValueError("parent_asset_not_found")
        asset = ITAsset(
            asset_id=f"AST-{uuid.uuid4().hex[:10].upper()}",
            asset_type=asset_type,
            name=name.strip(),
            owner=owner,
            location=location,
            status=status,
            serial_number=serial_number,
            warranty_until=warranty_until,
            parent_asset_id=parent_asset_id,
        )
        self.assets[asset.asset_id] = asset
        return asset

    def link_assets(self, asset_id: str, related_asset_id: str) -> bool:
        if asset_id not in self.assets or related_asset_id not in self.assets or asset_id == related_asset_id:
            return False
        if related_asset_id not in self.assets[asset_id].related_asset_ids:
            self.assets[asset_id].related_asset_ids.append(related_asset_id)
        if asset_id not in self.assets[related_asset_id].related_asset_ids:
            self.assets[related_asset_id].related_asset_ids.append(asset_id)
        return True

    def link_ticket(self, asset_id: str, ticket_id: str) -> bool:
        if asset_id not in self.assets or not ticket_id.strip():
            return False
        self.ticket_links.setdefault(asset_id, set()).add(ticket_id.strip())
        return True

    def get_asset(self, asset_id: str) -> ITAsset | None:
        return self.assets.get(asset_id)

    def list_assets(self, *, asset_type: str | None = None, status: str | None = None) -> list[ITAsset]:
        values = list(self.assets.values())
        if asset_type:
            values = [a for a in values if a.asset_type == asset_type]
        if status:
            values = [a for a in values if a.status == status]
        return values

    def update_status(self, asset_id: str, status: str, *, approved: bool = False) -> dict[str, Any]:
        if asset_id not in self.assets:
            return {"allowed": False, "reason": "asset_not_found"}
        if status not in ASSET_STATUSES:
            return {"allowed": False, "reason": "invalid_asset_status"}
        if status in {"retired", "disposed"} and not approved:
            return {"allowed": False, "reason": "human_approval_required", "requires_approval": True}
        self.assets[asset_id].status = status
        return {"allowed": True, "reason": "updated", "requires_approval": False}

    def snapshot(self) -> dict[str, Any]:
        return {
            "asset_types": sorted(ASSET_TYPES),
            "statuses": sorted(ASSET_STATUSES),
            "credential_storage": False,
            "ticket_linking": True,
            "retirement_and_disposal": "human_approval",
        }
