import unittest

from src.core.agentic_trace import AgenticTrace


class AgenticTraceTests(unittest.TestCase):
    def test_records_agentic_chain(self) -> None:
        trace = AgenticTrace("CFS-TEST-001")
        trace.record("global_supervisor", "routed", domain="business")
        trace.record("domain_supervisor", "delegated", specialist="finance_agent")
        trace.record("skill", "planned", skill="financial_analysis")
        summary = trace.summary()
        self.assertEqual(summary["event_count"], 3)
        self.assertEqual(summary["nodes"], ["global_supervisor", "domain_supervisor", "skill"])
        self.assertFalse(summary["credentials_exposed"])

    def test_filters_secrets(self) -> None:
        trace = AgenticTrace("CFS-TEST-002")
        event = trace.record("gateway", "completed", api_key="hidden", result={"token": "hidden", "ok": True})
        self.assertNotIn("api_key", event.details)
        self.assertNotIn("token", event.details["result"])
