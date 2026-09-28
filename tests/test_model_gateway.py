from src.core.model_gateway import ModelGateway


def test_gateway_bootstrap_and_generation_policy(tmp_path):
    g=ModelGateway(str(tmp_path/'models.sqlite3'))
    assert g.health()['generation_provider']=='anthropic_claude'
    assert g.get_model('anthropic','claude','1')['provider']=='anthropic'
    assert g.register_model('openai','bad-generation','generation','1')['reason']=='generation_provider_must_be_claude'


def test_policy_resolution_and_budget(tmp_path):
    g=ModelGateway(str(tmp_path/'models.sqlite3'))
    g.register_policy('t','w','p','generation',allowed_models=['claude'],max_input_tokens=100,max_cost=2.0)
    ok=g.resolve('t','w',agent_id='a',purpose='generation',policy_id='p',input_tokens=50,estimated_cost=1)
    assert ok['allowed'] and ok['model']['provider']=='anthropic'
    blocked=g.resolve('t','w',agent_id='a',purpose='generation',policy_id='p',input_tokens=101)
    assert blocked['reason']=='input_budget_exceeded'


def test_embedding_is_provider_abstract(tmp_path):
    g=ModelGateway(str(tmp_path/'models.sqlite3'))
    r=g.resolve('t','w',purpose='embedding')
    assert r['allowed'] and r['model']['purpose']=='embedding'


def test_evaluation_gate_blocks_regression(tmp_path):
    from src.core.ai_evaluation import AIEvaluationEngine
    g=ModelGateway(str(tmp_path/'models.sqlite3'))
    e=AIEvaluationEngine(str(tmp_path/'eval.sqlite3'))
    ds=e.create_dataset('t','w','quality',[{'input':{},'expected':{}}])
    scores={k:1 for k in e.DIMENSIONS}
    ok=g.evaluate_gate(e,'t','w',agent_id='a',model_id='claude',dataset_id=ds['dataset_id'],scores=scores)
    assert ok['allowed']
    low={k:0.4 for k in e.DIMENSIONS}
    blocked=g.evaluate_gate(e,'t','w',agent_id='a',model_id='claude',dataset_id=ds['dataset_id'],scores=low,previous_score=1.0)
    assert not blocked['allowed'] and blocked['reason']=='evaluation_regression'


def test_policy_tenant_isolation(tmp_path):
    g=ModelGateway(str(tmp_path/'models.sqlite3'))
    g.register_policy('t1','w','p','generation')
    assert g.get_policy('t2','w','p') is None
