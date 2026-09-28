from src.core.enterprise_control_center import EnterpriseControlCenter
from src.core.agent_registry import AgentRegistry
from src.core.ai_evaluation import AIEvaluationEngine
from src.core.model_gateway import ModelGateway
from src.core.observability import Observability
from src.core.usage_billing import UsageBilling


def test_control_center_snapshot(tmp_path):
    r=AgentRegistry(str(tmp_path/'registry.sqlite3'))
    e=AIEvaluationEngine(str(tmp_path/'eval.sqlite3'))
    g=ModelGateway(str(tmp_path/'model.sqlite3'))
    o=Observability(str(tmp_path/'obs.sqlite3'))
    u=UsageBilling(str(tmp_path/'usage.sqlite3'))
    r.register_agent('t','w','a','Agent',status='active')
    r.register_skill('t','w','s','Skill',status='active')
    ds=e.create_dataset('t','w','d',[{'input':{},'expected':{}}])
    e.evaluate('t','w',agent_id='a',model_id='claude',dataset_id=ds['dataset_id'],scores={k:1 for k in e.DIMENSIONS})
    u.account('t','w','starter');u.record('t','w','agent.run',3)
    c=EnterpriseControlCenter(agent_registry=r,evaluation=e,model_gateway=g,observability=o,usage_billing=u)
    s=c.snapshot('t','w')
    assert s['agents']['active']==1
    assert s['skills']['active']==1
    assert s['evaluation']['healthy']
    assert s['usage']['used_units']==3


def test_control_center_is_tenant_scoped(tmp_path):
    r=AgentRegistry(str(tmp_path/'registry.sqlite3'))
    r.register_agent('t1','w','a','One',status='active')
    c=EnterpriseControlCenter(agent_registry=r)
    assert c.snapshot('t2','w')['agents']['total']==0
