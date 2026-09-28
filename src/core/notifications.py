from __future__ import annotations
import json, os, sqlite3, uuid
from datetime import datetime, timezone

class NotificationCenter:
    """Durable provider-neutral notifications and communication job engine."""
    CHANNELS={"email","sms","whatsapp","push","in_app"}
    STATES={"queued","sending","sent","failed","cancelled","dead_letter"}

    def __init__(self, db_path=None, max_retries=3):
        self.db_path=db_path or os.path.join("data","notifications.sqlite3")
        self.max_retries=max(1,int(max_retries))
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS templates(template_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,name TEXT,channel TEXT,subject TEXT,body TEXT,active INTEGER,created_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS preferences(tenant_id TEXT,workspace_id TEXT,recipient TEXT,channel TEXT,enabled INTEGER,PRIMARY KEY(tenant_id,workspace_id,recipient,channel))")
            c.execute("CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,recipient TEXT,channel TEXT,template_id TEXT,subject TEXT,body TEXT,state TEXT,attempts INTEGER,last_error TEXT,idempotency_key TEXT,created_at TEXT,updated_at TEXT,metadata TEXT,UNIQUE(tenant_id,workspace_id,idempotency_key))")
    def db(self): return sqlite3.connect(self.db_path)
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def now(self): return datetime.now(timezone.utc).isoformat()

    def create_template(self,t,w,name,channel,body,subject=""):
        t,w=self.scope(t,w)
        if channel not in self.CHANNELS: return {"allowed":False,"reason":"invalid_channel"}
        tid="TPL-"+uuid.uuid4().hex[:12].upper()
        with self.db() as c:
            c.execute("INSERT INTO templates VALUES(?,?,?,?,?,?,?,?,?)",(tid,t,w,name,channel,subject,body,1,self.now()))
        return {"template_id":tid,"name":name,"channel":channel,"active":True}

    def set_preference(self,t,w,recipient,channel,enabled):
        t,w=self.scope(t,w)
        if channel not in self.CHANNELS: return {"allowed":False,"reason":"invalid_channel"}
        with self.db() as c:
            c.execute("INSERT OR REPLACE INTO preferences VALUES(?,?,?,?,?)",(t,w,recipient,channel,int(bool(enabled))))
        return {"recipient":recipient,"channel":channel,"enabled":bool(enabled)}

    def queue(self,t,w,recipient,channel,subject="",body="",template_id=None,idempotency_key=None,metadata=None):
        t,w=self.scope(t,w)
        if channel not in self.CHANNELS: return {"allowed":False,"reason":"invalid_channel"}
        with self.db() as c:
            pref=c.execute("SELECT enabled FROM preferences WHERE tenant_id=? AND workspace_id=? AND recipient=? AND channel=?",(t,w,recipient,channel)).fetchone()
            if pref and not pref[0]: return {"allowed":False,"reason":"recipient_opted_out"}
            if template_id:
                row=c.execute("SELECT subject,body,channel FROM templates WHERE template_id=? AND tenant_id=? AND workspace_id=? AND active=1",(template_id,t,w)).fetchone()
                if not row: return {"allowed":False,"reason":"template_not_found"}
                subject,body,channel=row
            key=idempotency_key or ("JOB:"+uuid.uuid4().hex)
            existing=c.execute("SELECT job_id,state FROM jobs WHERE tenant_id=? AND workspace_id=? AND idempotency_key=?",(t,w,key)).fetchone()
            if existing: return {"job_id":existing[0],"state":existing[1],"already_queued":True}
            jid="JOB-"+uuid.uuid4().hex[:12].upper(); now=self.now()
            c.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(jid,t,w,recipient,channel,template_id,subject,body,"queued",0,"",key,now,now,json.dumps(metadata or {})))
        return {"job_id":jid,"state":"queued","channel":channel,"recipient":recipient}

    def mark_sending(self,t,w,job_id):
        t,w=self.scope(t,w)
        with self.db() as c:
            row=c.execute("SELECT attempts,state FROM jobs WHERE job_id=? AND tenant_id=? AND workspace_id=?",(job_id,t,w)).fetchone()
            if not row: return {"allowed":False,"reason":"job_not_found"}
            if row[1] not in {"queued","failed"}: return {"allowed":False,"reason":"invalid_job_state"}
            attempts=row[0]+1
            c.execute("UPDATE jobs SET state='sending',attempts=?,updated_at=? WHERE job_id=? AND tenant_id=? AND workspace_id=?",(attempts,self.now(),job_id,t,w))
        return {"job_id":job_id,"state":"sending","attempts":attempts}

    def mark_result(self,t,w,job_id,success,error=""):
        t,w=self.scope(t,w)
        with self.db() as c:
            row=c.execute("SELECT attempts FROM jobs WHERE job_id=? AND tenant_id=? AND workspace_id=?",(job_id,t,w)).fetchone()
            if not row: return {"allowed":False,"reason":"job_not_found"}
            attempts=row[0]
            state="sent" if success else ("dead_letter" if attempts>=self.max_retries else "failed")
            c.execute("UPDATE jobs SET state=?,last_error=?,updated_at=? WHERE job_id=? AND tenant_id=? AND workspace_id=?",(state,error,self.now(),job_id,t,w))
        return {"job_id":job_id,"state":state,"attempts":attempts}

    def history(self,t,w,recipient=None):
        t,w=self.scope(t,w)
        with self.db() as c:
            q="SELECT job_id,recipient,channel,state,attempts,last_error,created_at,updated_at,metadata FROM jobs WHERE tenant_id=? AND workspace_id=?"
            args=[t,w]
            if recipient: q+=" AND recipient=?"; args.append(recipient)
            q+=" ORDER BY created_at DESC"
            rows=c.execute(q,args).fetchall()
        return [{"job_id":a,"recipient":b,"channel":c,"state":d,"attempts":e,"last_error":f,"created_at":g,"updated_at":h,"metadata":json.loads(i or "{}")} for a,b,c,d,e,f,g,h,i in rows]

    def health(self):
        with self.db() as c:
            templates=c.execute("SELECT COUNT(*) FROM templates").fetchone()[0]
            preferences=c.execute("SELECT COUNT(*) FROM preferences").fetchone()[0]
            jobs=c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        return {"status":"ok","templates":templates,"preferences":preferences,"jobs":jobs,"tenant_scoped":True,"provider_neutral":True,"idempotent":True}
