from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile
import time


@dataclass(frozen=True)
class ApplyResult:
    ok: bool
    applied: bool
    rolled_back: bool
    reason: str


class ControlledRepairApplier:
    """Apply only verified, approved repairs with a restore point and rollback."""

    def __init__(self, project_root: str | Path):
        self.root = Path(project_root).resolve()

    def _target(self, relative: str) -> Path:
        target = (self.root / relative).resolve()
        if self.root not in target.parents:
            raise ValueError("repair target escapes project root")
        return target

    def apply(self, relative: str, replacement: str, *, approved: bool, verified: bool) -> ApplyResult:
        if not approved:
            return ApplyResult(False, False, False, "human approval required")
        if not verified:
            return ApplyResult(False, False, False, "repair must pass sandbox verification")

        target = self._target(relative)
        if not target.exists() or not target.is_file():
            return ApplyResult(False, False, False, "target must be an existing file")

        backup_dir = Path(tempfile.mkdtemp(prefix="cyberfusion-rollback-"))
        backup = backup_dir / target.name
        shutil.copy2(target, backup)
        original = target.read_bytes()
        try:
            target.write_text(replacement, encoding="utf-8")
            if target.read_text(encoding="utf-8") != replacement:
                raise RuntimeError("post-write verification failed")
            return ApplyResult(True, True, False, "repair applied with restore point")
        except Exception as exc:
            shutil.copy2(backup, target)
            restored = target.read_bytes() == original
            return ApplyResult(False, False, restored, f"repair failed and rollback was attempted: {type(exc).__name__}: {exc}")
        finally:
            shutil.rmtree(backup_dir, ignore_errors=True)
