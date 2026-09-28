import tempfile
from datetime import datetime, timezone, timedelta

from src.core.context_graph import TemporalContextGraph

def test_add_current_and_history():
    with tempfile.TemporaryDirectory() as d:
        graph = TemporalContextGraph(f"{d}/graph.sqlite3")
        r = graph.add_fact("t1", "w1", "client:1", "status", "active",
                           source="crm", confidence=0.9, reference_id="REF-1", agent_id="a1")
        assert r["allowed"]
        current = graph.current("t1", "w1", "client:1")
        assert len(current) == 1
        assert current[0].object_id == "active"
        assert current[0].reference_id == "REF-1"
        assert graph.history("t1", "w1", "client:1")[0].fact_id == r["fact_id"]

def test_invalidate_preserves_history_and_point_in_time_query():
    with tempfile.TemporaryDirectory() as d:
        graph = TemporalContextGraph(f"{d}/graph.sqlite3")
        start = "2026-01-01T00:00:00+00:00"
        end = "2026-06-01T00:00:00+00:00"
        r = graph.add_fact("t1", "w1", "client:1", "status", "active",
                           source="crm", valid_from=start)
        graph.invalidate(r["fact_id"], tenant_id="t1", workspace_id="w1", valid_until=end)
        assert graph.current("t1", "w1", "client:1") == []
        assert len(graph.at("t1", "w1", "client:1", "2026-03-01T00:00:00+00:00")) == 1
        assert graph.at("t1", "w1", "client:1", "2026-07-01T00:00:00+00:00") == []
def test_tenant_and_workspace_isolation():
    with tempfile.TemporaryDirectory() as d:
        graph = TemporalContextGraph(f"{d}/graph.sqlite3")
        graph.add_fact("t1", "w1", "client:1", "owner", "alice", source="crm")
        graph.add_fact("t2", "w1", "client:1", "owner", "bob", source="crm")
        graph.add_fact("t1", "w2", "client:1", "owner", "carol", source="crm")
        assert [x.object_id for x in graph.current("t1", "w1", "client:1")] == ["alice"]
        assert [x.object_id for x in graph.current("t2", "w1", "client:1")] == ["bob"]
        assert [x.object_id for x in graph.current("t1", "w2", "client:1")] == ["carol"]

def test_confidence_is_bounded():
    with tempfile.TemporaryDirectory() as d:
        graph = TemporalContextGraph(f"{d}/graph.sqlite3")
        r = graph.add_fact("t", "w", "s", "p", "o", source="test", confidence=4)
        assert graph.current("t", "w", "s")[0].confidence == 1.0
        assert r["allowed"]
if __name__ == "__main__":
    import unittest
    unittest.main()
