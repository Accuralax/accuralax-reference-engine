from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from contextlib import contextmanager
import json, sqlite3, uuid

@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    event_type: str
    tenant_id: str
    workspace_id: str
    actor_id: str
    entity_type: str
    entity_id: str
    reference_id: str
    payload: dict[str, Any]
    occurred_at: str
    trace_id: str | None = None

class EventBus:
    BLOCKED={"password","api_key","apikey","token","secret","cvv","card_number"}
    def __init__(self, db_path="data/event_bus.sqlite3", max_handlers=16):
        import os
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path=db_path; self.max_handlers=max_handlers; self.handlers={}
        with self._db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS domain_events(event_id TEXT PRIMARY KEY,event_type TEXT NOT NULL,tenant_id TEXT NOT NULL,workspace_id TEXT NOT NULL,actor_id TEXT NOT NULL,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,reference_id TEXT NOT NULL,payload_json TEXT NOT NULL,occurred_at TEXT NOT NULL,trace_id TEXT,idempotency_key TEXT,UNIQUE(tenant_id,workspace_id,idempotency_key))")
            c.execute("CREATE INDEX IF NOT EXISTS idx_events_scope ON domain_events(tenant_id,workspace_id,occurred_at)")
    @contextmanager
    def _db(self):
        c=sqlite3.connect(self.db_path); c.row_factory=sqlite3.Row
        try: yield c; c.commit()
        finally: c.close()
    @classmethod
    def _safe(cls,value):
        if isinstance(value,dict): return {str(k):cls._safe(v) for k,v in value.items() if str(k).lower() not in cls.BLOCKED}
        if isinstance(value,list): return [cls._safe(v) for v in value]
        return value

    def subscribe(self,event_type,handler):
        hs=self.handlers.setdefault(event_type,[])
        if len(hs)>=self.max_handlers: raise ValueError("handler_limit_reached")
        hs.append(handler)

    def publish(self,event_type,tenant_id,workspace_id,actor_id,entity_type,entity_id,reference_id,payload=None,*,trace_id=None,idempotency_key=None):
        safe=self._safe(payload or {})
        with self._db() as c:
            if idempotency_key:
                row=c.execute("SELECT * FROM domain_events WHERE tenant_id=? AND workspace_id=? AND idempotency_key=?",(str(tenant_id),str(workspace_id),idempotency_key)).fetchone()
                if row: return self._row(row)
            event=DomainEvent("EVT-"+uuid.uuid4().hex[:12].upper(),event_type,str(tenant_id),str(workspace_id),str(actor_id),str(entity_type),str(entity_id),str(reference_id),safe,datetime.now(timezone.utc).isoformat(),trace_id)
            c.execute("INSERT INTO domain_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",(event.event_id,event.event_type,event.tenant_id,event.workspace_id,event.actor_id,event.entity_type,event.entity_id,event.reference_id,json.dumps(event.payload,sort_keys=True),event.occurred_at,event.trace_id,idempotency_key))
        for handler in tuple(self.handlers.get(event_type,[])):
            try: handler(event)
            except Exception: pass
        return event
    def publish_entity_change(self,entity_model,event_type,tenant_id,workspace_id,actor_id,entity_type,payload,reference_id="",idempotency_key=None,trace_id=None):
        record=entity_model.upsert(tenant_id,workspace_id,entity_type,payload)
        return self.publish(event_type,tenant_id,workspace_id,actor_id,entity_type,record["entity_id"],reference_id or record["entity_id"],payload,idempotency_key=idempotency_key,trace_id=trace_id)

    @staticmethod
    def _row(row):
        return DomainEvent(row["event_id"],row["event_type"],row["tenant_id"],row["workspace_id"],row["actor_id"],row["entity_type"],row["entity_id"],row["reference_id"],json.loads(row["payload_json"]),row["occurred_at"],row["trace_id"])

    def history(self,tenant_id,workspace_id,*,entity_id=None,event_type=None,limit=100):
        sql="SELECT * FROM domain_events WHERE tenant_id=? AND workspace_id=?"; params=[tenant_id,workspace_id]
        if entity_id: sql+=" AND entity_id=?"; params.append(entity_id)
        if event_type: sql+=" AND event_type=?"; params.append(event_type)
        sql+=" ORDER BY occurred_at DESC LIMIT ?"; params.append(max(1,min(int(limit),500)))
        with self._db() as c: return [self._row(x) for x in c.execute(sql,tuple(params)).fetchall()]

    def replay(self,tenant_id,workspace_id,handler,**filters):
        events=list(reversed(self.history(tenant_id,workspace_id,**filters)))
        for event in events: handler(event)
        return len(events)

    def health(self):
        with self._db() as c: count=c.execute("SELECT COUNT(*) FROM domain_events").fetchone()[0]
        return {"status":"ok","durable":True,"event_count":count,"tenant_isolation":True,"workspace_isolation":True,"idempotency":True,"credential_filtering":True}
