import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import tempfile
import unittest
from src.core.repair_executor import RepairExecutor


class RepairExecutorTests(unittest.TestCase):
    def test_requires_approval(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sample.txt"; p.write_text("old")
            e=RepairExecutor(d); c=e.candidate("r1", "sample.txt", "new")
            r=e.execute(c, approved=False, verified=True)
            self.assertEqual(r.status,"awaiting_approval"); self.assertEqual(p.read_text(),"old")

    def test_requires_verification(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sample.txt"; p.write_text("old")
            e=RepairExecutor(d); c=e.candidate("r2", "sample.txt", "new")
            r=e.execute(c, approved=True, verified=False)
            self.assertEqual(r.status,"verification_required"); self.assertEqual(p.read_text(),"old")

    def test_approved_verified_candidate_applies(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"sample.txt"; p.write_text("old")
            e=RepairExecutor(d); c=e.candidate("r3", "sample.txt", "new")
            r=e.execute(c, approved=True, verified=True)
            self.assertEqual(r.status,"applied"); self.assertEqual(p.read_text(),"new")

    def test_protected_target_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            e=RepairExecutor(d)
            with self.assertRaises(PermissionError): e.candidate("r4", "src/core/agent_permissions.py", "bad")

if __name__ == "__main__": unittest.main()
