from __future__ import annotations
import json,os,sqlite3,uuid
from datetime import datetime,timezone

class AgentGovernance:
    """Bounded agent safety policy: tools, risk, budgets and approval gates."""
    RISK={'read':0,'write':1,'execute':2,'external':3,'destructive':4}
    def __init__(self,db_path=None,max_steps=20,max_cost=100):
        self.db_path=db_path or os.path.join('data','agent_governance.sqlite3');self.max_steps=max(1,int(max_steps));self.max_cost=max(1,float(max_cost));os.makedirs(os.path.dirname(self.db_path) or '.',exist_ok=True)
        with self.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS tool_policies(tenant_id TEXT,workspace_id TEXT,agent_id TEXT,tool TEXT,allowed INTEGER,approval_required INTEGER,PRIMARY KEY(tenant_id,workspace_id,agent_id,tool))')
            c.execute('CREATE TABLE IF NOT EXISTS safety_decisions(decision_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,agent_id TEXT,action TEXT,risk TEXT,allowed INTEGER,reason TEXT,created_at TEXT)')
    def db(self):
        c=sqlite3.connect(self.db_path);c.row_factory=sqlite3.Row
        class C:
            def __enter__(s):return c
            def __exit__(s,*a):c.commit();c.close()
        return C()
    def set_tool(self,t,w,agent,tool,allowed=True,approval_required=False):
        with self.db() as c:c.execute('INSERT OR REPLACE INTO tool_policies VALUES(?,?,?,?,?,?)',(str(t),str(w),str(agent),str(tool),int(allowed),int(approval_required)))
        return {'tool':tool,'allowed':bool(allowed),'approval_required':bool(approval_required)}
    def check(self,t,w,agent,action,risk='read',steps=0,cost=0,tool=None,approved=False):
        risk=str(risk).lower();reasons=[];allowed=True
        if risk not in self.RISK:reasons.append('unknown_risk');allowed=False
        if int(steps)>self.max_steps:reasons.append('step_budget_exceeded');allowed=False
        if float(cost)>self.max_cost:reasons.append('cost_budget_exceeded');allowed=False
        if tool:
            with self.db() as c:r=c.execute('SELECT * FROM tool_policies WHERE tenant_id=? AND workspace_id=? AND agent_id=? AND tool=?',(str(t),str(w),str(agent),str(tool))).fetchone()
            if not r:reasons.append('tool_not_registered');allowed=False
            elif not r['allowed']:reasons.append('tool_denied');allowed=False
            elif r['approval_required'] and not approved:reasons.append('tool_approval_required');allowed=False
        if self.RISK.get(risk,4)>=3 and not approved:reasons.append('high_risk_requires_approval');allowed=False
        reason='allowed' if allowed else reasons[0]
        d={'decision_id':'AGD-'+uuid.uuid4().hex[:12].upper(),'tenant_id':str(t),'workspace_id':str(w),'agent_id':str(agent),'action':str(action),'risk':risk,'allowed':allowed,'reason':reason,'created_at':datetime.now(timezone.utc).isoformat()}
        with self.db() as c:c.execute('INSERT INTO safety_decisions VALUES(?,?,?,?,?,?,?,?,?)',(d['decision_id'],d['tenant_id'],d['workspace_id'],d['agent_id'],d['action'],d['risk'],int(allowed),reason,d['created_at']))
        d['reasons']=reasons;d['approval_required']=not allowed and any('approval' in x for x in reasons);return d
    def health(self):
        with self.db() as c:t=c.execute('SELECT COUNT(*) FROM tool_policies').fetchone()[0];d=c.execute('SELECT COUNT(*) FROM safety_decisions').fetchone()[0]
        return {'status':'ok','bounded':True,'max_steps':self.max_steps,'max_cost':self.max_cost,'tool_allowlist':True,'approval_gates':True,'decisions':d,'tool_policies':t}
