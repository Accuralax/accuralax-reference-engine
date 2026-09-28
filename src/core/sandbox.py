from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import shutil
import tempfile

@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    tests_passed: bool
    health_passed: bool
    rollback_ready: bool
    reason: str

class SandboxVerifier:
    """Prepare and verify bounded repair candidates without touching production files."""

    FORBIDDEN_TARGETS = {
        "src/config/agent_permissions.yaml",
        "src/config/business_rules.yaml",
        "src/config/business_systems.yaml",
        "src/core/agent_permissions.py",
        "src/core/audit.py",
        "src/integrations/credentials.py",
        "src/integrations/credential_router.py",
    }

    def snapshot(self, source: str | Path) -> dict[str, str]:
        """Fingerprint production Python source, excluding tests/runtime artifacts."""
        root = Path(source).resolve()
        source_root = root / "src" if (root / "src").is_dir() else root
        files: dict[str, str] = {}
        for path in source_root.rglob("*.py"):
            if ".venv" in path.parts or "__pycache__" in path.parts:
                continue
            files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return files

    def validate_target(self, target: str) -> bool:
        normalized = target.replace("\\", "/").lstrip("./")
        return normalized not in self.FORBIDDEN_TARGETS

    def create_sandbox(self, source: str | Path) -> Path:
        source_path = Path(source).resolve()
        sandbox = Path(tempfile.mkdtemp(prefix="cyberfusion-repair-"))
        # Repair verification only needs production source/config. Copying the
        # entire workspace can traverse node_modules and other large artifacts,
        # causing bounded verification to become effectively unbounded.
        src_root = source_path / "src" if (source_path / "src").is_dir() else source_path
        target = sandbox / "src"
        shutil.copytree(
            src_root,
            target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.sqlite3"),
        )
        return sandbox

    def verify(self, tests_passed: bool, health_passed: bool, rollback_ready: bool) -> VerificationResult:
        ok = tests_passed and health_passed and rollback_ready
        return VerificationResult(ok, tests_passed, health_passed, rollback_ready,
                                  "candidate verified" if ok else "candidate rejected")
