from datetime import datetime, timezone, timedelta

from src.core.worker_lease import WorkerLease


def test_worker_lease_is_single_owner(tmp_path):
    lease = WorkerLease(str(tmp_path / "leases.sqlite3"), lease_seconds=30)
    first = lease.acquire("OMEGA_CORE_WORKER", "owner-a")
    second = lease.acquire("OMEGA_CORE_WORKER", "owner-b")
    assert first["status"] == "acquired"
    assert second["status"] == "blocked"
    assert second["reason"] == "lease_held"


def test_worker_lease_heartbeat_and_reconcile(tmp_path):
    lease = WorkerLease(str(tmp_path / "leases.sqlite3"), lease_seconds=30)
    acquired = lease.acquire("OMEGA_CORE_WORKER", "owner-a")
    renewed = lease.heartbeat(acquired["lease_id"], "owner-a")
    assert renewed["status"] == "renewed"

    with lease._db() as conn:
        stale = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        conn.execute("UPDATE worker_leases SET expires_at=? WHERE lease_id=?", (stale, acquired["lease_id"]))
        conn.commit()

    result = lease.reconcile()
    assert result["expired"] == 1
    assert result["active"] == 0
