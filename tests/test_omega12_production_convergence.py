from src.core.omega12_ai_evaluation import Omega12AdvancedAIEvaluation
from src.core.omega12_production_convergence import Omega12ProductionConvergence
from src.core.ai_evaluation import AIEvaluationEngine

def test_production_gate_and_quarantine(tmp_path):
 o=Omega12AdvancedAIEvaluation(AIEvaluationEngine(str(tmp_path/'e.sqlite3')))
 d=o.create_dataset('t','w','d',[{'input':{},'expected':{}}])
 o.evaluate('t','w',agent_id='a',model_id='m',dataset_id=d['dataset_id'],scores={k:1 for k in o.engine.DIMENSIONS})
 p=Omega12ProductionConvergence(o)
 assert p.production_gate('t','w','a','m',d['dataset_id'])['release_allowed']
 p.quarantine('t','w','a','regression')
 assert not p.production_gate('t','w','a','m',d['dataset_id'])['release_allowed']
 assert p.unquarantine('t','w','a',False)['status']=='blocked'

def test_full_stack_fail_closed(tmp_path):
 o=Omega12AdvancedAIEvaluation(AIEvaluationEngine(str(tmp_path/'e.sqlite3')))
 p=Omega12ProductionConvergence(o)
 g=p.full_stack_gate({'omega8':{'ready':True},'omega9':{'ready':True},'omega10':{'ready':True},'omega11':{'ready':True}})
 assert not g['release_allowed'] and 'omega12' in g['missing_layers']
 assert p.readiness()['ready'] and p.health()['bounded']
