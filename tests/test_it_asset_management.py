import unittest

from src.core.it_asset_management import ITAssetManager


class ITAssetManagementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cmdb = ITAssetManager()

    def test_create_and_list_asset(self):
        asset = self.cmdb.create_asset("laptop", "Finance Laptop", owner="User A", location="Office 1")
        self.assertTrue(asset.asset_id.startswith("AST-"))
        self.assertEqual(len(self.cmdb.list_assets(asset_type="laptop")), 1)

    def test_parent_and_relationship(self):
        server = self.cmdb.create_asset("server", "App Server")
        switch = self.cmdb.create_asset("network_device", "Core Switch")
        self.assertTrue(self.cmdb.link_assets(server.asset_id, switch.asset_id))
        self.assertIn(switch.asset_id, server.related_asset_ids)

    def test_ticket_link(self):
        asset = self.cmdb.create_asset("printer", "Reception Printer")
        self.assertTrue(self.cmdb.link_ticket(asset.asset_id, "IT-123"))
        self.assertIn("IT-123", self.cmdb.ticket_links[asset.asset_id])

    def test_retirement_requires_approval(self):
        asset = self.cmdb.create_asset("laptop", "Old Laptop")
        denied = self.cmdb.update_status(asset.asset_id, "retired")
        self.assertFalse(denied["allowed"])
        self.assertTrue(denied["requires_approval"])
        approved = self.cmdb.update_status(asset.asset_id, "retired", approved=True)
        self.assertTrue(approved["allowed"])

    def test_invalid_asset_is_rejected(self):
        with self.assertRaises(ValueError):
            self.cmdb.create_asset("unknown", "Bad Asset")

    def test_credentials_not_stored(self):
        snapshot = self.cmdb.snapshot()
        self.assertFalse(snapshot["credential_storage"])


if __name__ == "__main__":
    unittest.main()
