import unittest

from src.core.it_support_rag import ITSupportRAG


class ITSupportRAGTests(unittest.TestCase):
    def setUp(self):
        self.rag = ITSupportRAG()

    def test_helpdesk_retrieval(self):
        hits = self.rag.search("helpdesk ticket troubleshooting")
        self.assertTrue(hits)
        self.assertEqual(hits[0].document.domain, "support")

    def test_domain_filter(self):
        hits = self.rag.search("wifi connectivity network", domain="ict")
        self.assertTrue(hits)
        self.assertTrue(all(hit.document.domain == "ict" for hit in hits))

    def test_unknown_query_does_not_guess(self):
        self.assertEqual(self.rag.search("quantum pineapple telemetry"), [])

    def test_provenance_is_present(self):
        hits = self.rag.search("management dashboard report")
        provenance = self.rag.provenance(hits)
        self.assertTrue(provenance)
        self.assertIn("document_id", provenance[0])
        self.assertIn("source_type", provenance[0])


if __name__ == "__main__":
    unittest.main()
