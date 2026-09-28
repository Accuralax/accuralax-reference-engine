import hashlib,json,os,sqlite3,uuid
from datetime import datetime,timezone
class IntelligenceEventFabric:
 RULES=(("compliance","compliance.","high"),("security","security.","critical"),("incident","it.incident.","critical"),("risk","risk.","high"),("sales","sales.","normal"),("lms","lms.","normal"))
 def __init__(self,db_path="data/intelligence_event_fabric.sqlite3",max_signals=1000):
  self.db_path=db_path;self.max_signals=max(1,min(int(max_signals),10000));os.makedirs(os.path.dirname(db_path) or ".",exist_ok=True)
  with sqlite3.connect(db_path) as c:c.execute("CREATE TABLE IF NOT EXISTS signals(id TEXT PRIMARY KEY,event_id TEXT,tenant TEXT,workspace TEXT,category TEXT,priority TEXT,confidence REAL,fingerprint TEXT,created_at TEXT,evidence TEXT,UNIQUE(tenant,workspace,fingerprint))")
 def _classify(self,t):
  for c,p,r in self.RULES:
   if str(t).startswith(p):return c,r,.95
  return "general","low",.65
 def ingest(self,event):
  cat,pri,conf=self._classify(event.event_type);d={"tenant":str(event.tenant_id),"workspace":str(event.workspace_id),"type":event.event_type,"entity":event.entity_id,"payload":event.payload};fp=hashlib.sha256(json.dumps(d,sort_keys=True,default=str).encode()).hexdigest();now=datetime.now(timezone.utc).isoformat()
  with sqlite3.connect(self.db_path) as c:
   row=c.execute("SELECT * FROM signals WHERE tenant=? AND workspace=? AND fingerprint=?",(d["tenant"],d["workspace"],fp)).fetchone()
   if row:return self._row(row)
   n=c.execute("SELECT COUNT(*) FROM signals WHERE tenant=? AND workspace=?",(d["tenant"],d["workspace"])).fetchone()[0]
   if n>=self.max_signals:raise RuntimeError("intelligence_signal_budget_exhausted")
   sid="SIG-"+uuid.uuid4().hex[:16].upper();ev={"event_type":event.event_type,"entity_type":event.entity_type,"entity_id":event.entity_id,"reference_id":event.reference_id,"trace_id":event.trace_id};c.execute("INSERT INTO signals VALUES(?,?,?,?,?,?,?,?,?,?)",(sid,event.event_id,d["tenant"],d["workspace"],cat,pri,conf,fp,now,json.dumps(ev)))
  return {"signal_id":sid,"event_id":event.event_id,"tenant_id":d["tenant"],"workspace_id":d["workspace"],"category":cat,"priority":pri,"confidence":conf,"fingerprint":fp,"evidence":ev,"created_at":now}
 def list_signals(self,t,w,priority=None,limit=100):
  q="SELECT * FROM signals WHERE tenant=? AND workspace=?";p=[str(t),str(w)]
  if priority:q+=" AND priority=?";p.append(priority)
  q+=" ORDER BY created_at DESC LIMIT ?";p.append(max(1,min(int(limit),self.max_signals)))
  with sqlite3.connect(self.db_path) as c:return [self._row(x) for x in c.execute(q,p).fetchall()]
 def _row(self,r):return {"signal_id":r[0],"event_id":r[1],"tenant_id":r[2],"workspace_id":r[3],"category":r[4],"priority":r[5],"confidence":r[6],"fingerprint":r[7],"created_at":r[8],"evidence":json.loads(r[9])}
 def health(self):
  with sqlite3.connect(self.db_path) as c:n=c.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
  return {"status":"ok","engine":"intelligence-event-fabric","bounded":True,"max_signals":self.max_signals,"signal_count":n,"execution_separate":True,"tenant_isolation":True,"deduplication":True}
