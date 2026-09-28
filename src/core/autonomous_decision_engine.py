import os,sqlite3,uuid
from datetime import datetime,timezone
class AutonomousDecisionEngine:
 def __init__(self,governance,max_decisions=1000,db_path="data/autonomous_decisions.sqlite3"):
  self.governance=governance;self.max_decisions=max(1,min(int(max_decisions),10000));self.db_path=db_path;os.makedirs(os.path.dirname(db_path) or ".",exist_ok=True)
  with sqlite3.connect(db_path) as c:c.execute("CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY,tenant TEXT,workspace TEXT,agent TEXT,signal TEXT,action TEXT,risk TEXT,status TEXT,reason TEXT,created_at TEXT)")
 def decide(self,tenant,workspace,agent,signal,action="review",risk="read",steps=0,cost=0,approved=False,tool=None):
  gate=self.governance.check(tenant,workspace,agent,action,risk,steps,cost,tool,approved);status="approved" if gate["allowed"] else ("approval_required" if gate["approval_required"] else "blocked");did="DEC-"+uuid.uuid4().hex[:16].upper();now=datetime.now(timezone.utc).isoformat()
  with sqlite3.connect(self.db_path) as c:
   n=c.execute("SELECT COUNT(*) FROM decisions WHERE tenant=? AND workspace=?",(str(tenant),str(workspace))).fetchone()[0]
   if n>=self.max_decisions:raise RuntimeError("decision_budget_exhausted")
   c.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?)",(did,str(tenant),str(workspace),str(agent),str(signal.get("signal_id","")),str(action),str(risk),status,gate["reason"],now))
  return {"decision_id":did,"status":status,"action":action,"risk":risk,"governance":gate,"execution_allowed":False,"created_at":now}
 def health(self):
  with sqlite3.connect(self.db_path) as c:n=c.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
  return {"status":"ok","engine":"autonomous-decision-engine","bounded":True,"max_decisions":self.max_decisions,"decision_count":n,"execution_separate":True,"governance_required":True}
