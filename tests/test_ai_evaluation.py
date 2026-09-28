from src.core.ai_evaluation import AIEvaluationEngine


def test_dataset_and_evaluation(tmp_path):
    e=AIEvaluationEngine(str(tmp_path/'eval.sqlite3'))
    ds=e.create_dataset('t','w','core',[{'input':{'q':'x'},'expected':{'answer':'yes'}}])
    r=e.evaluate('t','w',agent_id='a',model_id='claude',dataset_id=ds['dataset_id'],scores={k:1 for k in e.DIMENSIONS})
    assert r['passed'] and r['overall_score']==1.0
    assert e.latest('t','w','a')['evaluation_id']==r['evaluation_id']


def test_output_grounding_gate(tmp_path):
    e=AIEvaluationEngine(str(tmp_path/'eval.sqlite3'))
    ds=e.create_dataset('t','w','core',[{'input':{},'expected':{}}])
    r=e.evaluate_output('t','w',agent_id='a',model_id='claude',dataset_id=ds['dataset_id'],output='A useful answer')
    assert not r['passed'] and 'grounding_or_policy_evidence_missing' in r['findings']
    r=e.evaluate_output('t','w',agent_id='a',model_id='claude',dataset_id=ds['dataset_id'],output='A useful grounded answer',citations=['s1'],retrieved_sources=['s1'])
    assert r['passed']


def test_regression_detection(tmp_path):
    e=AIEvaluationEngine(str(tmp_path/'eval.sqlite3'))
    ds=e.create_dataset('t','w','core',[{'input':{},'expected':{}}])
    r=e.evaluate('t','w',agent_id='a',model_id='claude',dataset_id=ds['dataset_id'],scores={k:1 for k in e.DIMENSIONS})
    low=e.evaluate('t','w',agent_id='a',model_id='claude',dataset_id=ds['dataset_id'],scores={k:0.5 for k in e.DIMENSIONS},previous_score=r['overall_score'])
    assert low['regression'] and not low['passed']


def test_tenant_isolation(tmp_path):
    e=AIEvaluationEngine(str(tmp_path/'eval.sqlite3'))
    ds=e.create_dataset('t1','w','core',[])
    assert e.get_dataset('t2','w',ds['dataset_id']) is None
