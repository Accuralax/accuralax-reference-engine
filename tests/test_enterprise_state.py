from src.core.enterprise_state import EnterpriseState
from src.core.agentic_workspace import AgenticWorkspace

def test_state_persists_execution_and_audit(tmp_path):
    store=EnterpriseState(tmp_path/'state.sqlite3')
    contract={'reference_id':'CFS-AI-TEST','request_id':'req','trace_id':'trace','request':'test','status':'completed','risk_level':'low','approval_state':'not_required','tenant_id':'t','workspace_id':'w','actor_id':'a','channel':'test','created_at':'now','agent':'agent','domain':'test'}
    store.save_execution(contract)
    store.append_audit('CFS-AI-TEST','supervisor','completed',{'safe':True,'token':'removed'})
    assert store.recent_executions(1)[0]['reference_id']=='CFS-AI-TEST'
    assert store.audit('CFS-AI-TEST')[0]['details']=={'safe':True}

def test_workspace_creates_durable_state():
    result=AgenticWorkspace().run('I need help with cybersecurity')
    assert result['reference_id']
    store=AgenticWorkspace().state
    assert any(x['reference_id']==result['reference_id'] for x in store.recent_executions())
    assert store.audit(result['reference_id'])
