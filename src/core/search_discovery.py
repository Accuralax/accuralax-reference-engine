from __future__ import annotations
import json, os, re, sqlite3, uuid
from datetime import datetime, timezone

class SearchDiscovery:
    """Tenant-scoped keyword discovery with transparent relevance and access filtering."""
    def __init__(self, db_path=None):
        self.db_path=db_path or os.path.join("data","search_discovery.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS documents(doc_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,entity_type TEXT,entity_id TEXT,title TEXT,content TEXT,visibility TEXT,metadata TEXT,created_at TEXT,updated_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS queries(query_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,principal_id TEXT,query TEXT,result_count INTEGER,created_at TEXT)")
    def db(self): return sqlite3.connect(self.db_path)
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def now(self): return datetime.now(timezone.utc).isoformat()

    def index(self,t,w,entity_type,entity_id,title,content,visibility="workspace",metadata=None):
        t,w=self.scope(t,w)
        did="IDX-"+uuid.uuid4().hex[:12].upper(); now=self.now()
        with self.db() as c:
            existing=c.execute("SELECT doc_id FROM documents WHERE tenant_id=? AND workspace_id=? AND entity_type=? AND entity_id=?",(t,w,entity_type,entity_id)).fetchone()
            if existing:
                did=existing[0]
                c.execute("UPDATE documents SET title=?,content=?,visibility=?,metadata=?,updated_at=? WHERE doc_id=? AND tenant_id=? AND workspace_id=?",(title,content,visibility,json.dumps(metadata or {}),now,did,t,w))
            else:
                c.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?)",(did,t,w,entity_type,entity_id,title,content,visibility,json.dumps(metadata or {}),now,now))
        return {"doc_id":did,"indexed":True,"visibility":visibility}

    def remove(self,t,w,doc_id):
        t,w=self.scope(t,w)
        with self.db() as c:
            cur=c.execute("DELETE FROM documents WHERE doc_id=? AND tenant_id=? AND workspace_id=?",(doc_id,t,w))
        return {"doc_id":doc_id,"removed":cur.rowcount>0}

    def search(self,t,w,query,principal_id="system",entity_type=None,limit=20):
        t,w=self.scope(t,w)
        terms=[x.lower() for x in re.findall(r"[\w-]+",query or "") if len(x)>1]
        if not terms: return {"query_id":"","query":query,"results":[]}
        with self.db() as c:
            q="SELECT doc_id,entity_type,entity_id,title,content,visibility,metadata FROM documents WHERE tenant_id=? AND workspace_id=?"
            args=[t,w]
            if entity_type: q+=" AND entity_type=?"; args.append(entity_type)
            rows=c.execute(q,args).fetchall()
        results=[]
        for did,etype,eid,title,content,visibility,metadata in rows:
            if visibility=="private" and principal_id=="system": continue
            text=(title+" "+content).lower()
            score=sum(text.count(term) for term in terms)
            title_score=sum(title.lower().count(term) for term in terms)*2
            score+=title_score
            if score<=0: continue
            results.append({"doc_id":did,"entity_type":etype,"entity_id":eid,"title":title,"score":score,"visibility":visibility,"metadata":json.loads(metadata or "{}")})
        results.sort(key=lambda x:(-x["score"],x["title"]))
        results=results[:max(1,min(int(limit),100))]
        qid="QRY-"+uuid.uuid4().hex[:12].upper()
        with self.db() as c:
            c.execute("INSERT INTO queries VALUES(?,?,?,?,?,?,?)",(qid,t,w,principal_id,query,len(results),self.now()))
        return {"query_id":qid,"query":query,"results":results}

    def health(self):
        with self.db() as c:
            docs=c.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
            queries=c.execute("SELECT COUNT(*) FROM queries").fetchone()[0]
        return {"status":"ok","indexed_documents":docs,"queries":queries,"tenant_scoped":True,"relevance_scoring":True,"durable":True}
