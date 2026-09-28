from pathlib import Path
from typing import Any
import hashlib
import yaml


class DataIntelligence:
    def __init__(self, config_path: str | None = None) -> None:
        root = Path(__file__).resolve().parents[1]
        path = Path(config_path or root / "config" / "data_intelligence.yaml")
        with path.open("r", encoding="utf-8") as handle:
            self.config = yaml.safe_load(handle) or {}
        self.datasets: dict[str, dict[str, Any]] = {}
        self.metrics: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _ratio(passed: int, total: int) -> float:
        return 1.0 if total == 0 else round(passed / total, 4)

    def validate_quality(self, dataset_id: str, *, total: int, valid: int,
                         completeness: float = 1.0) -> dict[str, Any]:
        accuracy = self._ratio(valid, total)
        score = round(min(accuracy, completeness), 4)
        thresholds = self.config["data_quality"]["thresholds"]
        status = "pass" if score >= thresholds["pass"] else "warning" if score >= thresholds["warning"] else "fail"
        result = {"dataset_id": dataset_id, "quality_score": score,
                  "accuracy": accuracy, "completeness": completeness,
                  "status": status, "review_required": status == "fail",
                  "credentials_exposed": False}
        self.datasets[dataset_id] = result
        return result

    def register_metric(self, metric_id: str, definition: str, source: str,
                        owner: str, calculation_version: str) -> dict[str, Any]:
        if not all((definition, source, owner, calculation_version)):
            raise ValueError("metric definition, source, owner and version are required")
        metric = {"metric_id": metric_id, "definition": definition, "source": source,
                  "owner": owner, "calculation_version": calculation_version,
                  "credentials_exposed": False}
        self.metrics[metric_id] = metric
        return metric

    def detect_anomaly(self, values: list[float], threshold: float = 2.0) -> dict[str, Any]:
        if len(values) < 3:
            return {"anomaly": False, "reason": "insufficient_history"}
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5
        latest = values[-1]
        z = 0.0 if std == 0 else abs(latest - mean) / std
        return {"anomaly": z >= threshold, "z_score": round(z, 4),
                "latest": latest, "confidence": round(min(z / threshold, 1.0), 4)}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "dataset_count": len(self.datasets),
                "metric_count": len(self.metrics), "lineage_required": True}
