from src.core.enterprise_integration_layer import EnterpriseIntegrationLayer
from src.core.human_approval import HumanApprovalGateway

def test_success_idempotency_and_scope(tmp_path):
    x=EnterpriseIntegrationLayer(db_path=str(tmp_path/"jobs.sqlite3"), max_attempts=2)
    x.register_connector("ok", lambda a,p,j: {"ok":True})
    a=x.dispatch("t1","w1","ok","sync",{"x":1},idempotency_key="same")
    b=x.dispatch("t1","w1","ok","sync",{"x":2},idempotency_key="same")
    assert a["status"]=="completed" and b["job_id"]==a["job_id"]
    assert x.jobs("t2","w2")==[]

def test_retry_and_dead_letter(tmp_path):
    x=EnterpriseIntegrationLayer(db_path=str(tmp_path/"jobs.sqlite3"), max_attempts=2)
    def bad(a,p,j): raise RuntimeError("boom")
    x.register_connector("bad",bad)
    r=x.dispatch("t","w","bad","run")
    assert r["status"]=="failed" and r["attempts"]==1
    r=x.retry("t","w",r["job_id"])
    assert r["status"]=="dead_letter" and r["attempts"]==2

def test_approval_blocks_then_runs(tmp_path):
    approvals=HumanApprovalGateway(str(tmp_path/"approvals.sqlite3"))
    x=EnterpriseIntegrationLayer(approval_gateway=approvals,db_path=str(tmp_path/"jobs.sqlite3"))
    x.register_connector("ok", lambda a,p,j: {"ok":True})
    approval=approvals.request("t","w","PLAN-1",1,"DEC-1")
    r=x.dispatch("t","w","ok","sync",approval_required=True,approval_id=approval["approval_id"])
    assert r["status"]=="blocked"
    approvals.approve("t","w",approval["approval_id"],"human")
    r=x.run("t","w",r["job_id"])
    assert r["status"]=="completed"
