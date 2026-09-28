from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sqlite3, uuid

@dataclass(frozen=True)
class GraphFact:
    fact_id: str; tenant_id: str; workspace_id: str; subject_id: str; predicate: str; object_id: str
    valid_from: str; valid_until: str | None; observed_at: str; source: str; confidence: float
    reference_id: str | None; agent_id: str | None

class TemporalContextGraph:
    """Tenant-isolated temporal facts with durable, provenance-aware history."""
    def __init__(self, db_path: str | Path | None = None) -> None:
        root=Path(__file__).resolve().parents[2]; self.db_path=Path(db_path) if db_path else root/"data"/"context_graph.sqlite3"
        self.db_path.parent.mkdir(parents=True,exist_ok=True); self._init_db()
    @contextmanager
    def _db(self):
        db=sqlite3.connect(self.db_path)
        try: yield db; db.commit()
        finally: db.close()
    def _init_db(self):
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS graph_facts (fact_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,workspace_id TEXT NOT NULL,subject_id TEXT NOT NULL,predicate TEXT NOT NULL,object_id TEXT NOT NULL,valid_from TEXT NOT NULL,valid_until TEXT,observed_at TEXT NOT NULL,source TEXT NOT NULL,confidence REAL NOT NULL,reference_id TEXT,agent_id TEXT)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_graph_scope ON graph_facts(tenant_id,workspace_id)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_graph_subject ON graph_facts(tenant_id,workspace_id,subject_id)")
    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()
    def add_fact(self,tenant_id,workspace_id,subject_id,predicate,object_id,*,source,confidence=.5,valid_from=None,reference_id=None,agent_id=None):
        if not all([tenant_id,workspace_id,subject_id,predicate,object_id,source]): return {"allowed":False,"reason":"identity_fact_source_required"}
        now=self._now(); fact_id="GF-"+uuid.uuid4().hex[:12].upper(); vf=valid_from or now; confidence=max(0.,min(1.,float(confidence)))
        with self._db() as db: db.execute("INSERT INTO graph_facts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(fact_id,tenant_id,workspace_id,subject_id,predicate,object_id,vf,None,now,source,confidence,reference_id,agent_id))
        return {"allowed":True,"fact_id":fact_id,"valid_from":vf,"observed_at":now}
    def invalidate(self,fact_id,*,tenant_id,workspace_id,valid_until=None):
        end=valid_until or self._now()
        with self._db() as db:
            row=db.execute("SELECT fact_id FROM graph_facts WHERE fact_id=? AND tenant_id=? AND workspace_id=?",(fact_id,tenant_id,workspace_id)).fetchone()
            if not row: return {"allowed":False,"reason":"fact_not_found"}
            db.execute("UPDATE graph_facts SET valid_until=? WHERE fact_id=?",(end,fact_id))
        return {"allowed":True,"fact_id":fact_id,"valid_until":end}
    def _rows(self,sql,args):
        with self._db() as db: rows=db.execute(sql,args).fetchall()
        return [GraphFact(*r) for r in rows]
    def current(self,tenant_id,workspace_id,subject_id,predicate=None):
        sql="SELECT fact_id,tenant_id,workspace_id,subject_id,predicate,object_id,valid_from,valid_until,observed_at,source,confidence,reference_id,agent_id FROM graph_facts WHERE tenant_id=? AND workspace_id=? AND subject_id=? AND valid_until IS NULL"; args=[tenant_id,workspace_id,subject_id]
        if predicate: sql+=" AND predicate=?"; args.append(predicate)
        return self._rows(sql+" ORDER BY observed_at DESC",tuple(args))
    def at(self,tenant_id,workspace_id,subject_id,when,predicate=None):
        sql="SELECT fact_id,tenant_id,workspace_id,subject_id,predicate,object_id,valid_from,valid_until,observed_at,source,confidence,reference_id,agent_id FROM graph_facts WHERE tenant_id=? AND workspace_id=? AND subject_id=? AND valid_from<=? AND (valid_until IS NULL OR valid_until>?)"; args=[tenant_id,workspace_id,subject_id,when,when]
        if predicate: sql+=" AND predicate=?"; args.append(predicate)
        return self._rows(sql+" ORDER BY valid_from DESC",tuple(args))
    def history(self,tenant_id,workspace_id,subject_id,predicate=None):
        sql="SELECT fact_id,tenant_id,workspace_id,subject_id,predicate,object_id,valid_from,valid_until,observed_at,source,confidence,reference_id,agent_id FROM graph_facts WHERE tenant_id=? AND workspace_id=? AND subject_id=?"; args=[tenant_id,workspace_id,subject_id]
        if predicate: sql+=" AND predicate=?"; args.append(predicate)
        return self._rows(sql+" ORDER BY valid_from DESC",tuple(args))
    def neighbors(self,tenant_id,workspace_id,subject_id,predicate=None): return self.current(tenant_id,workspace_id,subject_id,predicate)
    def health(self):
        with self._db() as db: count=db.execute("SELECT COUNT(*) FROM graph_facts").fetchone()[0]
        return {"status":"ok","fact_count":count,"temporal":True,"tenant_isolation":True,"provenance":True,"immutable_history":True}
    @staticmethod
    def as_dict(f): return {"fact_id":f.fact_id,"tenant_id":f.tenant_id,"workspace_id":f.workspace_id,"subject_id":f.subject_id,"predicate":f.predicate,"object_id":f.object_id,"valid_from":f.valid_from,"valid_until":f.valid_until,"observed_at":f.observed_at,"source":f.source,"confidence":f.confidence,"reference_id":f.reference_id,"agent_id":f.agent_id}
