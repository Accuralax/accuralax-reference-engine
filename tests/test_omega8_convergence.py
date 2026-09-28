from src.core.omega8_convergence import Omega8Convergence

class Learning:
    def record(self,*a,**k): return {"memory_id":"M1"}
class Strategy:
    def guidance(self,*a,**k): return {"avoid_actions":[],"stats":{}}
class Memory:
    def consolidate(self,*a): return {"allowed":True,"consolidated":1}
class Evaluation:
    def evaluate(self,*a,**k): return {"passed":True,"overall_score":1.0}
class Registry:
    def get_agent(self,*a): return {"agent_id":"A1","status":"active"}
class Governance:
    def check(self,*a,**k): return {"allowed":True,"approval_required":False}
class Audit:
    def record(self,*a,**k): return {"audit_id":"A1"}
class Obs:
    def log(self,*a,**k): return {"id":"L1"}

def build(): return Omega8Convergence(Learning(),Strategy(),Memory(),Evaluation(),Registry(),Governance(),None,None,Audit(),Obs())
def test_outcome_learning(): assert build().outcome_learning("t","w","a","p",{"outcome":"success"})["status"]=="recorded"
def test_strategy_and_memory():
    c=build(); assert c.strategy_guidance("a","t","w","q")["status"]=="ready"; assert c.consolidate_memory("a")["allowed"]
def test_evaluation_governance_lifecycle():
    c=build(); assert c.evaluate("t","w",agent_id="a",model_id="m",dataset_id="d",scores={})["passed"] is True; assert c.govern("t","w","a","read")["allowed"]; assert c.lifecycle("t","w","a")["status"]=="ready"
def test_observability_audit(): assert build().observe("t","w","omega.test")["status"]=="recorded"
def test_health_exposes_boundaries():
    h=build().health(); assert h["status"]=="ok" and h["execution_boundary"] is True
