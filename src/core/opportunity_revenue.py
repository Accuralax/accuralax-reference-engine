import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from .event_bus import EventBus

DB_PATH = os.getenv("OPPORTUNITY_REVENUE_DB_PATH", os.path.join("data", "opportunity_revenue.sqlite3"))
STATUSES = ("open", "won", "lost", "cancelled")

class OpportunityRevenue:
    """Tenant-scoped opportunity and revenue lifecycle anchored to canonical CRM clients."""

    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        self.events = EventBus(os.path.join(os.path.dirname(db_path) or ".", "event_bus.sqlite3"))
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS opportunities(
                opportunity_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                client_id TEXT NOT NULL, lead_id TEXT, name TEXT NOT NULL, stage TEXT NOT NULL,
                status TEXT NOT NULL, value REAL, currency TEXT, probability REAL,
                expected_close_date TEXT, actual_close_date TEXT, lost_reason TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
            c.execute("""CREATE TABLE IF NOT EXISTS opportunity_history(
                history_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                opportunity_id TEXT NOT NULL, from_stage TEXT, to_stage TEXT,
                from_status TEXT, to_status TEXT, changed_by TEXT NOT NULL,
                changed_at TEXT NOT NULL, reason TEXT NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_opp_scope_status ON opportunities(tenant_id,workspace_id,status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_opp_scope_client ON opportunities(tenant_id,workspace_id,client_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_opp_history ON opportunity_history(tenant_id,workspace_id,opportunity_id,changed_at)")

    @contextmanager
    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    @staticmethod
    def _scope(tenant_id, workspace_id):
        return str(tenant_id), str(workspace_id)

    @staticmethod
    def _client(client_id):
        if not str(client_id).strip():
            raise ValueError("client_id_required")

    @staticmethod
    def _number(value, field):
        if value is None:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(field + "_must_be_number")
        return value

    def create(self, tenant_id, workspace_id, client_id, name, value=None, currency=None,
               probability=0, expected_close_date=None, lead_id=None):
        self._client(client_id)
        if not str(name).strip():
            raise ValueError("name_required")
        value = self._number(value, "value")
        probability = self._number(probability, "probability")
        if probability is not None and not 0 <= probability <= 100:
            raise ValueError("probability_out_of_range")
        now = datetime.now(timezone.utc).isoformat()
        oid = "OPP-" + uuid.uuid4().hex[:16].upper()
        with self._db() as c:
            c.execute("INSERT INTO opportunities VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (oid, *self._scope(tenant_id, workspace_id), str(client_id),
                 str(lead_id) if lead_id else None, str(name), "new", "open", value,
                 str(currency or "").upper(), probability, expected_close_date, None, None, now, now))
            c.execute("INSERT INTO opportunity_history VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                ("OHS-" + uuid.uuid4().hex[:16].upper(), *self._scope(tenant_id, workspace_id),
                 oid, None, "new", None, "open", "system", now, "opportunity_created"))
        result = self.get(tenant_id, workspace_id, oid)
        self.events.publish("sales.opportunity.created", tenant_id, workspace_id, "system", "opportunity", oid, oid, {"client_id": client_id, "lead_id": lead_id, "value": value, "currency": currency})
        return result

    def get(self, tenant_id, workspace_id, opportunity_id):
        with self._db() as c:
            row = c.execute("SELECT * FROM opportunities WHERE tenant_id=? AND workspace_id=? AND opportunity_id=?",
                            (*self._scope(tenant_id, workspace_id), str(opportunity_id))).fetchone()
        return dict(row) if row else None

    def update_stage(self, tenant_id, workspace_id, opportunity_id, stage, changed_by="system", reason=""):
        if not str(stage).strip():
            raise ValueError("stage_required")
        item = self.get(tenant_id, workspace_id, opportunity_id)
        if not item:
            raise ValueError("opportunity_not_found")
        if item["stage"] == str(stage):
            return item
        return self._transition(tenant_id, workspace_id, item, str(stage), item["status"], changed_by, reason)

    def close(self, tenant_id, workspace_id, opportunity_id, status, changed_by="system", reason=""):
        status = str(status)
        if status not in STATUSES:
            raise ValueError("invalid_status")
        item = self.get(tenant_id, workspace_id, opportunity_id)
        if not item:
            raise ValueError("opportunity_not_found")
        if status == "lost" and not str(reason).strip():
            raise ValueError("lost_reason_required")
        if item["status"] == status:
            return item
        stage = "closed_won" if status == "won" else ("closed_lost" if status == "lost" else item["stage"])
        now = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute("""UPDATE opportunities SET stage=?, status=?, actual_close_date=?, lost_reason=?, updated_at=?
                WHERE tenant_id=? AND workspace_id=? AND opportunity_id=?""",
                (stage, status, now if status in ("won","lost","cancelled") else None,
                 str(reason) if status == "lost" else item["lost_reason"], now,
                 *self._scope(tenant_id, workspace_id), str(opportunity_id)))
            c.execute("INSERT INTO opportunity_history VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                ("OHS-" + uuid.uuid4().hex[:16].upper(), *self._scope(tenant_id, workspace_id),
                 str(opportunity_id), item["stage"], stage, item["status"], status,
                 str(changed_by), now, str(reason)))
        result = self.get(tenant_id, workspace_id, opportunity_id)
        self.events.publish("sales.opportunity.closed", tenant_id, workspace_id, str(changed_by), "opportunity", opportunity_id, opportunity_id, {"status": status, "reason": reason})
        return result

    def _transition(self, tenant_id, workspace_id, item, stage, status, changed_by, reason):
        now = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute("UPDATE opportunities SET stage=?, updated_at=? WHERE tenant_id=? AND workspace_id=? AND opportunity_id=?",
                      (stage, now, *self._scope(tenant_id, workspace_id), item["opportunity_id"]))
            c.execute("INSERT INTO opportunity_history VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                      ("OHS-" + uuid.uuid4().hex[:16].upper(), *self._scope(tenant_id, workspace_id),
                       item["opportunity_id"], item["stage"], stage, status, status,
                       str(changed_by), now, str(reason)))
        result = self.get(tenant_id, workspace_id, item["opportunity_id"])
        self.events.publish("sales.opportunity.stage_changed", tenant_id, workspace_id, str(changed_by), "opportunity", item["opportunity_id"], item["opportunity_id"], {"from_stage": item["stage"], "to_stage": stage, "reason": reason})
        return result

    def history(self, tenant_id, workspace_id, opportunity_id):
        with self._db() as c:
            rows = c.execute("SELECT * FROM opportunity_history WHERE tenant_id=? AND workspace_id=? AND opportunity_id=? ORDER BY changed_at",
                             (*self._scope(tenant_id, workspace_id), str(opportunity_id))).fetchall()
        return [dict(r) for r in rows]

    def revenue(self, tenant_id, workspace_id, currency=None):
        args = [*self._scope(tenant_id, workspace_id)]
        query = "SELECT status, COUNT(*) AS count, COALESCE(SUM(value),0) AS value FROM opportunities WHERE tenant_id=? AND workspace_id=?"
        if currency:
            query += " AND currency=?"
            args.append(str(currency).upper())
        query += " GROUP BY status"
        with self._db() as c:
            rows = c.execute(query, args).fetchall()
        result = {status: {"count": 0, "value": 0.0} for status in STATUSES}
        for row in rows:
            result[row["status"]] = {"count": row["count"], "value": float(row["value"] or 0)}
        open_forecast = 0.0
        for row in rows:
            if row["status"] == "open":
                open_forecast = float(row["value"] or 0)
        return {"currency": str(currency).upper() if currency else None, "statuses": result,
                "won_revenue": result["won"]["value"], "open_pipeline": result["open"]["value"],
                "open_forecast_unweighted": open_forecast,
                "total_opportunities": sum(x["count"] for x in result.values())}

    def health(self):
        with self._db() as c:
            count = c.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
            history = c.execute("SELECT COUNT(*) FROM opportunity_history").fetchone()[0]
        return {"status":"ok","engine":"opportunity-revenue","tenant_workspace_scoped":True,
                "canonical_client_anchor":True,"revenue_audit":True,
                "credentials_exposed":False,"opportunities":count,"history":history}
