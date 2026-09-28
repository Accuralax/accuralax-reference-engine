import unittest

from src.core.business_function_rag import BusinessFunctionRAG


class BusinessFunctionRAGTests(unittest.TestCase):
    def setUp(self):
        self.rag = BusinessFunctionRAG()

    def test_strategy_retrieval(self):
        hits = self.rag.search("strategy planning growth", function="strategy")
        self.assertTrue(hits)
        self.assertEqual(hits[0].function, "strategy")

    def test_function_filter(self):
        hits = self.rag.search("budget accounting", function="finance")
        self.assertTrue(all(hit.function == "finance" for hit in hits))

    def test_unknown_query_does_not_guess(self):
        self.assertEqual(self.rag.search("quantum pineapple telemetry"), [])

    def test_provenance(self):
        hits = self.rag.search("procurement suppliers")
        provenance = self.rag.provenance(hits)
        self.assertTrue(provenance)
        self.assertIn("source_type", provenance[0])

    def test_snapshot_is_safe(self):
        self.assertFalse(self.rag.snapshot()["credentials_exposed_to_agents"])


if __name__ == "__main__":
    unittest.main()
