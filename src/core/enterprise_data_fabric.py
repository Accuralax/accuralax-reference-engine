from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import hashlib
import json
import math
import yaml


@dataclass
class DataRecord:
    record_id: str
    source: str
    entity: str
    payload: dict[str, Any]
    received_at: str
    content_hash: str


class EnterpriseDataFabric:
    """Governed data layer connecting sources, quality, metrics and intelligence."""

    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[1]
        self.config = yaml.safe_load((root / "config" / "enterprise_data_fabric.yaml").read_text(encoding="utf-8")) or {}
        self.records: list[DataRecord] = []
        self.metrics: dict[str, dict[str, Any]] = {}
        self._counter = 0

    @staticmethod
    def _safe(value: Any) -> Any:
        blocked = {"password", "api_key", "apikey", "token", "secret", "cvv", "card_number"}
        if isinstance(value, dict):
            return {str(k): EnterpriseDataFabric._safe(v) for k, v in value.items()
                    if str(k).lower() not in blocked}
        if isinstance(value, list):
            return [EnterpriseDataFabric._safe(v) for v in value]
        return value

    def ingest(self, source: str, entity: str, payload: dict[str, Any]) -> DataRecord:
        self._counter += 1
        safe = self._safe(payload)
        raw = json.dumps(safe, sort_keys=True, default=str)
        record = DataRecord(
            f"DAT-{self._counter:08d}", source, entity, safe,
            datetime.now(timezone.utc).isoformat(),
            hashlib.sha256(raw.encode()).hexdigest(),
        )
        self.records.append(record)
        return record

    def validate_quality(self, values: list[Any]) -> dict[str, Any]:
        if not values:
            return {"status": "fail", "score": 0.0, "dimensions": {}}
        complete = sum(v is not None for v in values) / len(values)
        unique = len({json.dumps(v, sort_keys=True, default=str) for v in values}) / len(values)
        score = round((complete + min(unique, 1.0)) / 2, 4)
        threshold = self.config["quality"]
        status = "pass" if score >= threshold["pass_threshold"] else "warning" if score >= threshold["warning_threshold"] else "fail"
        return {"status": status, "score": score,
                "dimensions": {"completeness": round(complete, 4), "uniqueness": round(min(unique, 1.0), 4)}}

    def define_metric(self, name: str, owner: str, source: str, calculation_version: str) -> dict[str, Any]:
        if not all([name, owner, source, calculation_version]):
            return {"allowed": False, "reason": "metric_definition_incomplete"}
        self.metrics[name] = {"owner": owner, "source": source,
                              "calculation_version": calculation_version, "status": "active"}
        return {"allowed": True, "metric": name, "definition": self.metrics[name]}

    def analyze(self, values: list[float]) -> dict[str, Any]:
        if not values:
            return {"status": "insufficient_data"}
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = math.sqrt(variance)
        anomalies = [x for x in values if std > 0 and abs(x - mean) / std >= 2]
        trend = "flat"
        if len(values) >= 2:
            trend = "up" if values[-1] > values[0] else "down" if values[-1] < values[0] else "flat"
        return {"status": "ok", "count": len(values), "mean": mean, "stddev": std,
                "trend": trend, "anomalies": anomalies,
                "confidence": "medium" if len(values) < 10 else "high"}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "records": len(self.records), "metrics": len(self.metrics),
                "lineage_required": True, "provenance_required": True,
                "credentials_stored": False}
