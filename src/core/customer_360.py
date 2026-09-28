import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from .event_bus import EventBus

DB_PATH = os.getenv("CRM_360_DB_PATH", os.path.join("data", "crm_360.sqlite3"))

class Customer360:
    """Persistent relationship layer anchored to canonical CRM client IDs."""

    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        self.events = EventBus(os.path.join(os.path.dirname(db_path) or ".", "event_bus.sqlite3"))
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS relationships(
                relationship_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                client_id TEXT NOT NULL, relationship_type TEXT NOT NULL, subject TEXT NOT NULL,
                status TEXT NOT NULL, metadata_json TEXT NOT NULL, created_at TEXT NOT NULL)""")
            c.execute("""CREATE TABLE IF NOT EXISTS relationship_events(
                event_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                client_id TEXT NOT NULL, channel TEXT NOT NULL, event_type TEXT NOT NULL,
                summary TEXT NOT NULL, occurred_at TEXT NOT NULL, metadata_json TEXT NOT NULL)""")
            c.execute("""CREATE TABLE IF NOT EXISTS relationship_consents(
                consent_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                client_id TEXT NOT NULL, purpose TEXT NOT NULL, granted INTEGER NOT NULL,
                recorded_at TEXT NOT NULL, source TEXT NOT NULL,
                UNIQUE(tenant_id, workspace_id, client_id, purpose))""")
            c.execute("""CREATE TABLE IF NOT EXISTS opportunities(
                opportunity_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                client_id TEXT NOT NULL, name TEXT NOT NULL, stage TEXT NOT NULL,
                value REAL, currency TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_360_events ON relationship_events(tenant_id,workspace_id,client_id,occurred_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_360_relationships ON relationships(tenant_id,workspace_id,client_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_360_opportunities ON opportunities(tenant_id,workspace_id,client_id)")

    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    @staticmethod
    def _scope(tenant_id, workspace_id):
        return str(tenant_id), str(workspace_id)

    @staticmethod
    def _ensure_client(client_id):
        if not str(client_id).strip():
            raise ValueError("client_id_required")

    def add_relationship(self, tenant_id, workspace_id, client_id, relationship_type, subject, metadata=None):
        self._ensure_client(client_id)
        now = datetime.now(timezone.utc).isoformat()
        item = ("REL-" + uuid.uuid4().hex[:16].upper(), *self._scope(tenant_id,workspace_id),
                str(client_id), str(relationship_type), str(subject), "active",
                json.dumps(metadata or {}, sort_keys=True), now)
        with self._db() as c:
            c.execute("INSERT INTO relationships VALUES(?,?,?,?,?,?,?,?,?)", item)
        result = self.relationships(tenant_id, workspace_id, client_id)[-1]
        self.events.publish("crm.relationship.created", tenant_id, workspace_id, "system", "client", client_id, result["relationship_id"], {"relationship_type": relationship_type, "subject": subject})
        return result

    def record_event(self, tenant_id, workspace_id, client_id, channel, event_type, summary, occurred_at=None, metadata=None):
        self._ensure_client(client_id)
        when = occurred_at or datetime.now(timezone.utc).isoformat()
        item = ("EVT-" + uuid.uuid4().hex[:16].upper(), *self._scope(tenant_id,workspace_id),
                str(client_id), str(channel), str(event_type), str(summary), str(when),
                json.dumps(metadata or {}, sort_keys=True))
        with self._db() as c:
            c.execute("INSERT INTO relationship_events VALUES(?,?,?,?,?,?,?,?,?)", item)
        self.events.publish("crm.customer.event_recorded", tenant_id, workspace_id, "system", "client", client_id, item[0], {"channel": channel, "event_type": event_type, "summary": summary})
        return {"event_id":item[0],"client_id":str(client_id),"channel":str(channel),
                "event_type":str(event_type),"summary":str(summary),"occurred_at":str(when),
                "metadata":metadata or {}}

    def set_consent(self, tenant_id, workspace_id, client_id, purpose, granted, source="crm"):
        self._ensure_client(client_id)
        now = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute("""INSERT INTO relationship_consents
                VALUES(?,?,?,?,?,?,?,?)
                ON CONFLICT(tenant_id,workspace_id,client_id,purpose)
                DO UPDATE SET granted=excluded.granted, recorded_at=excluded.recorded_at, source=excluded.source""",
                ("CNS-" + uuid.uuid4().hex[:16].upper(), *self._scope(tenant_id,workspace_id),
                 str(client_id), str(purpose), int(bool(granted)), now, str(source)))
        result = self.consent(tenant_id, workspace_id, client_id, purpose)
        self.events.publish("crm.consent.changed", tenant_id, workspace_id, "system", "client", client_id, result.get("consent_id", str(client_id)), {"purpose": purpose, "granted": bool(granted), "source": source})
        return result

    def consent(self, tenant_id, workspace_id, client_id, purpose):
        with self._db() as c:
            row=c.execute("""SELECT * FROM relationship_consents
                WHERE tenant_id=? AND workspace_id=? AND client_id=? AND purpose=?""",
                (*self._scope(tenant_id,workspace_id),str(client_id),str(purpose))).fetchone()
        if not row:
            return {"granted":False,"known":False,"purpose":str(purpose)}
        item=dict(row)
        item["granted"]=bool(item["granted"])
        return item
    def create_opportunity(self, tenant_id, workspace_id, client_id, name, stage="new", value=None, currency=None):
        self._ensure_client(client_id)
        now=datetime.now(timezone.utc).isoformat()
        oid="OPP-"+uuid.uuid4().hex[:16].upper()
        with self._db() as c:
            c.execute("INSERT INTO opportunities VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (oid,*self._scope(tenant_id,workspace_id),str(client_id),str(name),str(stage),
                 value,str(currency or ""), "open",now,now))
        result = self.opportunities(tenant_id,workspace_id,client_id)[-1]
        self.events.publish("crm.customer.opportunity_created", tenant_id, workspace_id, "system", "client", client_id, oid, {"name": name, "stage": stage, "value": value, "currency": currency})
        return result

    def relationships(self, tenant_id, workspace_id, client_id):
        with self._db() as c:
            rows=c.execute("""SELECT * FROM relationships WHERE tenant_id=? AND workspace_id=? AND client_id=?
                ORDER BY created_at""",(*self._scope(tenant_id,workspace_id),str(client_id))).fetchall()
        return [self._row(r) for r in rows]

    def opportunities(self, tenant_id, workspace_id, client_id):
        with self._db() as c:
            rows=c.execute("""SELECT * FROM opportunities WHERE tenant_id=? AND workspace_id=? AND client_id=?
                ORDER BY created_at""",(*self._scope(tenant_id,workspace_id),str(client_id))).fetchall()
        return [dict(r) for r in rows]
    def timeline(self, tenant_id, workspace_id, client_id, limit=100):
        with self._db() as c:
            rows=c.execute("""SELECT * FROM relationship_events WHERE tenant_id=? AND workspace_id=? AND client_id=?
                ORDER BY occurred_at DESC LIMIT ?""",(*self._scope(tenant_id,workspace_id),str(client_id),int(limit))).fetchall()
        return [self._row(r) for r in rows]

    def customer_360(self, tenant_id, workspace_id, client_id):
        return {"client_id":str(client_id),
                "relationships":self.relationships(tenant_id,workspace_id,client_id),
                "timeline":self.timeline(tenant_id,workspace_id,client_id),
                "opportunities":self.opportunities(tenant_id,workspace_id,client_id),
                "consents":self._consents(tenant_id,workspace_id,client_id)}

    def _consents(self, tenant_id, workspace_id, client_id):
        with self._db() as c:
            rows=c.execute("SELECT * FROM relationship_consents WHERE tenant_id=? AND workspace_id=? AND client_id=?",
                           (*self._scope(tenant_id,workspace_id),str(client_id))).fetchall()
        return [dict(r, granted=bool(r["granted"])) for r in rows]
    @staticmethod
    def _row(row):
        item=dict(row)
        if "metadata_json" in item:
            item["metadata"]=json.loads(item.pop("metadata_json"))
        return item

    def handoff_allowed(self, tenant_id, workspace_id, client_id, purpose):
        return self.consent(tenant_id,workspace_id,client_id,purpose)["granted"]

    def health(self):
        with self._db() as c:
            counts={k:c.execute(f"SELECT COUNT(*) FROM {k}").fetchone()[0]
                    for k in ("relationships","relationship_events","relationship_consents","opportunities")}
        return {"status":"ok","engine":"customer-360-relationship","tenant_workspace_scoped":True,
                "canonical_client_anchor":True,"consent_gate":True,"credentials_exposed":False,**counts}
