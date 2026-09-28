import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import tempfile
import unittest
from src.core.controlled_repair import ControlledRepairApplier


class ControlledRepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "sample.txt").write_text("before", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_requires_approval(self):
        result = ControlledRepairApplier(self.root).apply("sample.txt", "after", approved=False, verified=True)
        self.assertFalse(result.ok)
        self.assertEqual((self.root / "sample.txt").read_text(), "before")

    def test_requires_sandbox_verification(self):
        result = ControlledRepairApplier(self.root).apply("sample.txt", "after", approved=True, verified=False)
        self.assertFalse(result.ok)
        self.assertEqual((self.root / "sample.txt").read_text(), "before")

    def test_verified_approved_repair_applies(self):
        result = ControlledRepairApplier(self.root).apply("sample.txt", "after", approved=True, verified=True)
        self.assertTrue(result.ok)
        self.assertTrue(result.applied)
        self.assertFalse(result.rolled_back)
        self.assertEqual((self.root / "sample.txt").read_text(), "after")

    def test_path_escape_is_rejected(self):
        with self.assertRaises(ValueError):
            ControlledRepairApplier(self.root).apply("..\\outside.txt", "bad", approved=True, verified=True)


if __name__ == "__main__":
    unittest.main()
