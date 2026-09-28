import unittest

from src.core.security_rag import SecurityKnowledgeRAG


class SecurityRAGTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rag = SecurityKnowledgeRAG()

    def test_identity_retrieval(self) -> None:
        hits = self.rag.search("least privilege identity access")
        self.assertTrue(hits)
        self.assertEqual(hits[0].domain, "identity")

    def test_domain_filter(self) -> None:
        hits = self.rag.search("configuration detection", domain="web")
        self.assertTrue(hits)
        self.assertTrue(all(hit.domain == "web" for hit in hits))

    def test_unknown_query_returns_no_guess(self) -> None:
        hits = self.rag.search("quantum pineapple telemetry")
        self.assertEqual(hits, [])

    def test_provenance_is_present(self) -> None:
        hits = self.rag.search("data classification audit")
        provenance = self.rag.provenance(hits)
        self.assertTrue(provenance)
        self.assertIn("document_id", provenance[0])
        self.assertIn("source_type", provenance[0])


if __name__ == "__main__":
    unittest.main()
