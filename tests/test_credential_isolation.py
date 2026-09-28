import os
import unittest

from integrations.credentials import CredentialProvider
from integrations.credential_router import CredentialAwareRouter
from integrations.adapters.mock import build_mock_adapters


class CredentialIsolationTests(unittest.TestCase):
    def setUp(self):
        self.provider = CredentialProvider()
        self.adapters = build_mock_adapters()
        self.router = CredentialAwareRouter(self.provider, self.adapters)

    def test_agent_facing_description_never_contains_secret(self):
        os.environ["HUBSPOT_ACCESS_TOKEN"] = "super-secret-test-value"
        description = self.provider.describe("hubspot")
        self.assertNotIn("super-secret-test-value", str(description))
        self.assertEqual(description["env_var"], "HUBSPOT_ACCESS_TOKEN")

    def test_secret_is_available_only_inside_provider_boundary(self):
        os.environ["HUBSPOT_ACCESS_TOKEN"] = "super-secret-test-value"
        self.assertTrue(self.provider.has_credential("hubspot"))
        self.assertEqual(self.provider.get_for_adapter("hubspot"), "super-secret-test-value")

    def test_router_does_not_put_secret_in_adapter_payload(self):
        os.environ["HUBSPOT_ACCESS_TOKEN"] = "super-secret-test-value"
        result = self.router.execute("hubspot", "search_contact", {"email": "test@example.com"})
        self.assertTrue(result.ok)
        call_payload = self.adapters["hubspot"].calls[-1][1]
        self.assertNotIn("super-secret-test-value", str(call_payload))
        self.assertNotIn("access_token", call_payload)

    def tearDown(self):
        os.environ.pop("HUBSPOT_ACCESS_TOKEN", None)


if __name__ == "__main__":
    unittest.main()
