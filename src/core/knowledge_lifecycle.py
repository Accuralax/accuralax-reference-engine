from __future__ import annotations
import os, sqlite3, uuid
from datetime import datetime, timezone, timedelta

class KnowledgeLifecycle:
    TRUST={"unverified":0,"low":1,"medium":2,"high":3,"authoritative":4}
    def __init__(self,db_path=None):
        self.db_path=db_path or os.path.join("data","knowledge_lifecycle.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS sources(source_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,name TEXT,source_type TEXT,trust TEXT,authority TEXT,refresh_days INTEGER,status TEXT,created_at TEXT,updated_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS policies(tenant_id TEXT,workspace_id TEXT,source_id TEXT,role TEXT,allowed INTEGER,PRIMARY KEY(tenant_id,workspace_id,source_id,role))")
            c.execute("CREATE TABLE IF NOT EXISTS freshness(source_id TEXT PRIMARY KEY,last_verified TEXT,next_review TEXT,state TEXT)")
    def db(self): return sqlite3.connect(self.db_path)
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def now(self): return datetime.now(timezone.utc)
    def register_source(self,t,w,name,source_type,trust="unverified",authority="",refresh_days=30):
        t,w=self.scope(t,w)
        if trust not in self.TRUST:return {"allowed":False,"reason":"invalid_trust"}
        if not name.strip() or not source_type.strip():return {"allowed":False,"reason":"source_identity_required"}
        sid="SRC-"+uuid.uuid4().hex[:12].upper(); n=self.now(); nxt=n+timedelta(days=max(1,int(refresh_days)))
        with self.db() as c:
            c.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?,?,?)",(sid,t,w,name,source_type,trust,authority,max(1,int(refresh_days)),"active",n.isoformat(),n.isoformat()))
            c.execute("INSERT INTO freshness VALUES(?,?,?,?)",(sid,n.isoformat(),nxt.isoformat(),"fresh"))
        return {"source_id":sid,"status":"active","trust":trust,"next_review":nxt.isoformat()}
    def set_access(self,t,w,sid,role,allowed):
        t,w=self.scope(t,w)
        with self.db() as c:
            if not c.execute("SELECT 1 FROM sources WHERE source_id=? AND tenant_id=? AND workspace_id=?",(sid,t,w)).fetchone():return {"allowed":False,"reason":"source_not_found"}
            c.execute("INSERT OR REPLACE INTO policies VALUES(?,?,?,?,?)",(t,w,sid,role,int(bool(allowed))))
        return {"source_id":sid,"role":role,"allowed":bool(allowed)}

    def verify_source(self,t,w,sid,verified_by):
        t,w=self.scope(t,w); n=self.now()
        with self.db() as c:
            row=c.execute("SELECT refresh_days FROM sources WHERE source_id=? AND tenant_id=? AND workspace_id=?",(sid,t,w)).fetchone()
            if not row:return {"allowed":False,"reason":"source_not_found"}
            nxt=n+timedelta(days=int(row[0]))
            c.execute("UPDATE freshness SET last_verified=?,next_review=?,state='fresh' WHERE source_id=?",(n.isoformat(),nxt.isoformat(),sid))
            c.execute("UPDATE sources SET status='active',updated_at=? WHERE source_id=? AND tenant_id=? AND workspace_id=?",(n.isoformat(),sid,t,w))
        return {"source_id":sid,"verified_by":verified_by,"state":"fresh","next_review":nxt.isoformat()}

    def authorize(self,t,w,sid,role,minimum_trust="unverified"):
        t,w=self.scope(t,w)
        with self.db() as c:
            row=c.execute("SELECT trust,status FROM sources WHERE source_id=? AND tenant_id=? AND workspace_id=?",(sid,t,w)).fetchone()
            if not row:return {"allowed":False,"reason":"source_not_found"}
            trust,status=row; access=c.execute("SELECT allowed FROM policies WHERE tenant_id=? AND workspace_id=? AND source_id=? AND role=?",(t,w,sid,role)).fetchone()
            fresh=c.execute("SELECT state FROM freshness WHERE source_id=?",(sid,)).fetchone()
        if self.TRUST.get(trust,0)<self.TRUST.get(minimum_trust,0):return {"allowed":False,"reason":"trust_below_minimum"}
        if status!="active":return {"allowed":False,"reason":"source_inactive"}
        if access is not None and not bool(access[0]):return {"allowed":False,"reason":"access_denied"}
        if not fresh or fresh[0]=="stale":return {"allowed":False,"reason":"source_stale"}
        return {"allowed":True,"source_id":sid,"trust":trust,"freshness":"fresh"}

    def refresh_status(self):
        n=self.now(); changed=0
        with self.db() as c:
            for sid,review in c.execute("SELECT source_id,next_review FROM freshness").fetchall():
                if datetime.fromisoformat(review)<=n:
                    c.execute("UPDATE freshness SET state='stale' WHERE source_id=?",(sid,))
                    c.execute("UPDATE sources SET status='review_required' WHERE source_id=?",(sid,)); changed+=1
        return {"status":"ok","stale_sources":changed}

    def health(self):
        with self.db() as c:
            sources=c.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
            stale=c.execute("SELECT COUNT(*) FROM freshness WHERE state='stale'").fetchone()[0]
            policies=c.execute("SELECT COUNT(*) FROM policies").fetchone()[0]
        return {"status":"ok","sources":sources,"stale_sources":stale,"access_policies":policies,"tenant_scoped":True,"authority_levels":list(self.TRUST),"credentials_exposed":False}

    def list_sources(self,t,w):
        t,w=self.scope(t,w)
        with self.db() as c:
            rows=c.execute("SELECT source_id,name,source_type,trust,authority,refresh_days,status,created_at,updated_at FROM sources WHERE tenant_id=? AND workspace_id=? ORDER BY name",(t,w)).fetchall()
        return [dict(zip(["source_id","name","source_type","trust","authority","refresh_days","status","created_at","updated_at"],r)) for r in rows]
