import tempfile
import unittest
from pathlib import Path

from src.core.it_asset_management import ITAssetManager
from src.core.it_operational_store import ITOperationalStore
from src.core.it_service_management import ITServiceManager


class ITOperationalStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ITOperationalStore(Path(self.tmp.name) / "ops.sqlite3")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_asset_survives_new_store_instance(self):
        manager = ITAssetManager()
        asset = manager.create_asset("server", "App Server", owner="Ops")
        self.store.save_asset(asset)
        second = ITOperationalStore(self.store.path)
        saved = second.get_asset(asset.asset_id)
        self.assertEqual(saved["name"], "App Server")
        self.assertEqual(saved["owner"], "Ops")

    def test_ticket_survives_new_store_instance(self):
        ticket = ITServiceManager().create_ticket("CFS-IT-100", "Laptop not working")
        self.store.save_ticket(ticket)
        second = ITOperationalStore(self.store.path)
        saved = second.get_ticket(ticket.ticket_id)
        self.assertEqual(saved["reference_id"], "CFS-IT-100")
        self.assertEqual(saved["status"], "open")

    def test_ticket_asset_relationship_survives(self):
        manager = ITAssetManager()
        asset = manager.create_asset("laptop", "User Laptop")
        ticket = ITServiceManager().create_ticket("CFS-IT-101", "Laptop not working")
        self.store.save_asset(asset)
        self.store.save_ticket(ticket)
        self.store.link_ticket_asset(ticket.ticket_id, asset.asset_id)
        second = ITOperationalStore(self.store.path)
        self.assertEqual(second.ticket_assets(ticket.ticket_id), [asset.asset_id])

    def test_counts(self):
        self.assertEqual(self.store.counts(), {"assets": 0, "tickets": 0, "ticket_asset_links": 0})

    def test_snapshot_is_safe(self):
        snapshot = self.store.snapshot()
        self.assertTrue(snapshot["durable"])
        self.assertFalse(snapshot["credential_storage"])


if __name__ == "__main__":
    unittest.main()
