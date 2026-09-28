from __future__ import annotations
from dataclasses import asdict
from typing import Any
from .creative_studio import CreativeStudio, CreativeAsset


class CreativeAPI:
    """Transport-neutral API facade for the Creative Studio frontend."""

    def __init__(self) -> None:
        self.studio = CreativeStudio()
        self.assets: dict[str, CreativeAsset] = {}

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        asset = self.studio.create_asset(
            payload["asset_id"], payload.get("asset_type", "document"),
            payload.get("title", "Untitled"), payload.get("content", ""),
            **payload.get("metadata", {}),
        )
        self.assets[asset.asset_id] = asset
        return asdict(asset)

    def edit(self, asset_id: str, operation: str, instruction: str = "") -> dict[str, Any]:
        asset = self.assets[asset_id]
        result = self.studio.edit(asset, operation, instruction)
        if result.changed:
            asset.content = result.content
            asset.version += 1
        return {"asset": asdict(asset), "operation": result.operation,
                "changed": result.changed, "safe": result.safe}

    def render(self, asset_id: str, theme: dict[str, Any] | None = None) -> str:
        return self.studio.render_web(self.assets[asset_id], theme)

    def manifest(self, asset_id: str, formats: list[str]) -> dict[str, Any]:
        return self.studio.export_manifest(self.assets[asset_id], formats)

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "service": "creative-studio", "assets": len(self.assets),
                "credentials_exposed": False}
