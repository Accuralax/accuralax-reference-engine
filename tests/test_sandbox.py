import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import unittest
from src.core.sandbox import SandboxVerifier


class SandboxVerifierTests(unittest.TestCase):
    def test_forbidden_security_targets_are_blocked(self):
        verifier = SandboxVerifier()
        self.assertFalse(verifier.validate_target("src/config/agent_permissions.yaml"))
        self.assertFalse(verifier.validate_target("src/integrations/credentials.py"))
        self.assertTrue(verifier.validate_target("src/core/repair.py"))

    def test_snapshot_is_read_only(self):
        verifier = SandboxVerifier()
        root = Path(__file__).resolve().parent.parent
        before = verifier.snapshot(root)
        after = verifier.snapshot(root)
        self.assertEqual(before, after)
        self.assertTrue(before)

    def test_verification_requires_all_gates(self):
        verifier = SandboxVerifier()
        self.assertTrue(verifier.verify(True, True, True).ok)
        self.assertFalse(verifier.verify(True, False, True).ok)
        self.assertFalse(verifier.verify(True, True, False).ok)

    def test_sandbox_excludes_runtime_and_git_data(self):
        verifier = SandboxVerifier()
        root = Path(__file__).resolve().parent.parent
        sandbox = verifier.create_sandbox(root)
        try:
            self.assertFalse((sandbox / ".git").exists())
            self.assertFalse((sandbox / ".venv").exists())
            self.assertFalse((sandbox / "data" / "executions.sqlite3").exists())
            self.assertTrue((sandbox / "src").exists())
        finally:
            import shutil
            shutil.rmtree(sandbox, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
