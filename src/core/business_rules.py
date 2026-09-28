from __future__ import annotations
import json, os, sqlite3, uuid
from datetime import datetime, timezone

class BusinessRules:
    """Tenant-scoped deterministic rules with durable evaluation history."""
    OPERATORS={"eq","neq","gt","gte","lt","lte","contains","in"}
    def __init__(self, db_path=None):
        self.db_path=db_path or os.path.join("data","business_rules.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS rules(rule_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,name TEXT,event_type TEXT,condition TEXT,actions TEXT,priority INTEGER,active INTEGER,created_at TEXT,updated_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS evaluations(evaluation_id TEXT PRIMARY KEY,rule_id TEXT,tenant_id TEXT,workspace_id TEXT,event_type TEXT,matched INTEGER,result TEXT,created_at TEXT)")
    def db(self): return sqlite3.connect(self.db_path)
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def now(self): return datetime.now(timezone.utc).isoformat()
    def define(self,t,w,name,event_type,condition,actions,priority=100):
        t,w=self.scope(t,w)
        if condition.get("operator") not in self.OPERATORS:return {"allowed":False,"reason":"invalid_operator"}
        rid="RULE-"+uuid.uuid4().hex[:12].upper(); now=self.now()
        with self.db() as c:c.execute("INSERT INTO rules VALUES(?,?,?,?,?,?,?,?,?,?,?)",(rid,t,w,name,event_type,json.dumps(condition),json.dumps(actions),int(priority),1,now,now))
        return self.get(t,w,rid)
    def get(self,t,w,rid):
        t,w=self.scope(t,w)
        with self.db() as c:r=c.execute("SELECT rule_id,name,event_type,condition,actions,priority,active,created_at,updated_at FROM rules WHERE rule_id=? AND tenant_id=? AND workspace_id=?",(rid,t,w)).fetchone()
        if not r:return None
        out=dict(zip(("rule_id","name","event_type","condition","actions","priority","active","created_at","updated_at"),r)); out["condition"]=json.loads(out["condition"]); out["actions"]=json.loads(out["actions"]); return out
    def _match(self,value,op,target):
        if op=="eq":return value==target
        if op=="neq":return value!=target
        if op=="gt":return value>target
        if op=="gte":return value>=target
        if op=="lt":return value<target
        if op=="lte":return value<=target
        if op=="contains":return target in value
        if op=="in":return value in target
        return False
    def evaluate(self,t,w,event_type,context):
        t,w=self.scope(t,w); rows=[]
        with self.db() as c: rows=c.execute("SELECT rule_id,name,condition,actions,priority FROM rules WHERE tenant_id=? AND workspace_id=? AND event_type=? AND active=1 ORDER BY priority ASC",(t,w,event_type)).fetchall()
        results=[]
        for rid,name,cond,actions,priority in rows:
            cond=json.loads(cond); actions=json.loads(actions); value=context.get(cond.get("field"))
            matched=False
            try: matched=self._match(value,cond["operator"],cond.get("value"))
            except (TypeError,ValueError): matched=False
            result={"rule_id":rid,"name":name,"priority":priority,"matched":matched,"actions":actions if matched else []}
            eid="EVAL-"+uuid.uuid4().hex[:12].upper()
            with self.db() as c:c.execute("INSERT INTO evaluations VALUES(?,?,?,?,?,?,?,?)",(eid,rid,t,w,event_type,int(matched),json.dumps(result),self.now()))
            results.append(result)
        return {"event_type":event_type,"matched_count":sum(1 for x in results if x["matched"]),"rules":results}
    def history(self,t,w,limit=100):
        t,w=self.scope(t,w)
        with self.db() as c:rows=c.execute("SELECT evaluation_id,rule_id,event_type,matched,result,created_at FROM evaluations WHERE tenant_id=? AND workspace_id=? ORDER BY created_at DESC LIMIT ?",(t,w,int(limit))).fetchall()
        return [dict(zip(("evaluation_id","rule_id","event_type","matched","result","created_at"),r)) for r in rows]
    def health(self):
        with self.db() as c:a=c.execute("SELECT COUNT(*) FROM rules").fetchone()[0]; b=c.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]
        return {"status":"ok","rules":a,"evaluations":b,"tenant_scoped":True,"deterministic":True}
