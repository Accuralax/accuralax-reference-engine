from src.core.agent_planner import AgentPlanner
from src.core.agent_workflow import AgentWorkflow

def test_plan_is_bounded_and_proposed(tmp_path):
    wf=AgentWorkflow(db_path=str(tmp_path/'workflow.sqlite3'))
    planner=AgentPlanner(wf,db_path=str(tmp_path/'planner.sqlite3'),max_actions=2)
    result=planner.plan('t1','w1','c1',lead={'lead_id':'l1','score':90},consent_granted=False)
    assert result['status']=='proposed'
    assert len(result['actions'])<=2
    assert planner.get('t1','w1',result['plan_id'])['plan']['status']=='proposed'

def test_plan_scope(tmp_path):
    wf=AgentWorkflow(db_path=str(tmp_path/'workflow.sqlite3'))
    planner=AgentPlanner(wf,db_path=str(tmp_path/'planner.sqlite3'))
    result=planner.plan('t1','w1','c1')
    try: planner.get('t2','w2',result['plan_id'])
    except ValueError as e: assert str(e)=='plan_not_found'
    else: assert False


def test_event_plan_is_idempotent(tmp_path):
    from src.core.event_bus import EventBus
    wf=AgentWorkflow(db_path=str(tmp_path/'workflow.sqlite3'))
    planner=AgentPlanner(wf,db_path=str(tmp_path/'planner.sqlite3'))
    bus=EventBus(str(tmp_path/'events.sqlite3'))
    event=bus.publish("sales.lead.created","t1","w1","system","lead","L1","R1",{"client_id":"C1"},idempotency_key="e1")
    first=planner.process_event(event)
    second=planner.process_event(event)
    assert first["plan_id"] == second["plan_id"]
    assert planner.get("t1","w1",first["plan_id"])["plan"]["status"] == "proposed"
