from __future__ import annotations
import hashlib, json, os, sqlite3, uuid
from datetime import datetime, timezone

class RecordsManagement:
    """Durable tenant-scoped records, versions, classification and retention controls."""
    STATUSES={"active","archived","disposed","legal_hold"}
    CLASSIFICATIONS={"public","internal","confidential","restricted"}

    def __init__(self, db_path=None):
        self.db_path=db_path or os.path.join("data","records_management.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS records(record_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,name TEXT,record_type TEXT,classification TEXT,status TEXT,retention_days INTEGER,created_at TEXT,updated_at TEXT,metadata TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS versions(version_id TEXT PRIMARY KEY,record_id TEXT,tenant_id TEXT,workspace_id TEXT,version_no INTEGER,content_hash TEXT,size_bytes INTEGER,created_at TEXT,created_by TEXT,metadata TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS links(link_id TEXT PRIMARY KEY,record_id TEXT,tenant_id TEXT,workspace_id TEXT,target_type TEXT,target_id TEXT,created_at TEXT)")
    def db(self): return sqlite3.connect(self.db_path)
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def now(self): return datetime.now(timezone.utc).isoformat()

    def create_record(self,t,w,name,record_type="document",classification="internal",retention_days=365,metadata=None):
        t,w=self.scope(t,w)
        if classification not in self.CLASSIFICATIONS: return {"allowed":False,"reason":"invalid_classification"}
        rid="REC-"+uuid.uuid4().hex[:12].upper(); now=self.now()
        with self.db() as c:
            c.execute("INSERT INTO records VALUES(?,?,?,?,?,?,?,?,?,?,?)",(rid,t,w,name,record_type,classification,"active",int(retention_days),now,now,json.dumps(metadata or {})))
        return self.get(t,w,rid)

    def get(self,t,w,record_id):
        t,w=self.scope(t,w)
        with self.db() as c:
            row=c.execute("SELECT record_id,name,record_type,classification,status,retention_days,created_at,updated_at,metadata FROM records WHERE record_id=? AND tenant_id=? AND workspace_id=?",(record_id,t,w)).fetchone()
        if not row: return None
        keys=("record_id","name","record_type","classification","status","retention_days","created_at","updated_at","metadata")
        out=dict(zip(keys,row)); out["metadata"]=json.loads(out["metadata"] or "{}"); return out

    def add_version(self,t,w,record_id,content,created_by="system",metadata=None):
        t,w=self.scope(t,w)
        if not self.get(t,w,record_id): return {"allowed":False,"reason":"record_not_found"}
        digest=hashlib.sha256(str(content).encode()).hexdigest()
        size=len(str(content).encode())
        with self.db() as c:
            n=c.execute("SELECT COALESCE(MAX(version_no),0)+1 FROM versions WHERE record_id=? AND tenant_id=? AND workspace_id=?",(record_id,t,w)).fetchone()[0]
            vid="VER-"+uuid.uuid4().hex[:12].upper(); now=self.now()
            c.execute("INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?)",(vid,record_id,t,w,n,digest,size,now,created_by,json.dumps(metadata or {})))
            c.execute("UPDATE records SET updated_at=? WHERE record_id=? AND tenant_id=? AND workspace_id=?",(now,record_id,t,w))
        return {"version_id":vid,"record_id":record_id,"version_no":n,"content_hash":digest,"size_bytes":size}

    def classify(self,t,w,record_id,classification):
        t,w=self.scope(t,w)
        if classification not in self.CLASSIFICATIONS: return {"allowed":False,"reason":"invalid_classification"}
        with self.db() as c:
            if not c.execute("SELECT 1 FROM records WHERE record_id=? AND tenant_id=? AND workspace_id=?",(record_id,t,w)).fetchone(): return {"allowed":False,"reason":"record_not_found"}
            c.execute("UPDATE records SET classification=?,updated_at=? WHERE record_id=? AND tenant_id=? AND workspace_id=?",(classification,self.now(),record_id,t,w))
        return self.get(t,w,record_id)

    def transition(self,t,w,record_id,status):
        t,w=self.scope(t,w)
        if status not in self.STATUSES: return {"allowed":False,"reason":"invalid_status"}
        with self.db() as c:
            row=c.execute("SELECT status FROM records WHERE record_id=? AND tenant_id=? AND workspace_id=?",(record_id,t,w)).fetchone()
            if not row: return {"allowed":False,"reason":"record_not_found"}
            if row[0]=="legal_hold" and status=="disposed": return {"allowed":False,"reason":"legal_hold_blocks_disposal"}
            c.execute("UPDATE records SET status=?,updated_at=? WHERE record_id=? AND tenant_id=? AND workspace_id=?",(status,self.now(),record_id,t,w))
        return self.get(t,w,record_id)

    def link(self,t,w,record_id,target_type,target_id):
        t,w=self.scope(t,w)
        if not self.get(t,w,record_id): return {"allowed":False,"reason":"record_not_found"}
        lid="LNK-"+uuid.uuid4().hex[:12].upper()
        with self.db() as c:
            c.execute("INSERT INTO links VALUES(?,?,?,?,?,?,?)",(lid,record_id,t,w,target_type,target_id,self.now()))
        return {"link_id":lid,"record_id":record_id,"target_type":target_type,"target_id":target_id}

    def health(self):
        with self.db() as c:
            records=c.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            versions=c.execute("SELECT COUNT(*) FROM versions").fetchone()[0]
            links=c.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        return {"status":"ok","records":records,"versions":versions,"links":links,"tenant_scoped":True,"retention_controls":True,"classification_controls":True}
