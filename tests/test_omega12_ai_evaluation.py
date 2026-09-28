from src.core.omega12_ai_evaluation import Omega12AdvancedAIEvaluation
from src.core.ai_evaluation import AIEvaluationEngine

def test_omega12_release(tmp_path):
 o=Omega12AdvancedAIEvaluation(AIEvaluationEngine(str(tmp_path/"e.sqlite3")))
 d=o.create_dataset("t","w","d",[{"input":{},"expected":{}}])
 r=o.evaluate("t","w",agent_id="a",model_id="m",dataset_id=d["dataset_id"],scores={k:1 for k in o.engine.DIMENSIONS})
 assert r["passed"] and o.release_gate("t","w","a","m",d["dataset_id"])["release_allowed"]

def test_omega12_controls():
 o=Omega12AdvancedAIEvaluation()
 assert o.regression(.7,.9)["regression"]
 assert o.composite({"a":1,"b":.5})["score"]==.75
 assert o.safety()["status"]=="passed"
 assert o.red_team([{"severity":"critical"}])["status"]=="blocked"

def test_omega12_bounded(tmp_path):
 o=Omega12AdvancedAIEvaluation(AIEvaluationEngine(str(tmp_path/"e.sqlite3")))
 o.create_dataset("t","w","d",[])
 assert len(o.adversarial(range(5000))["cases"])==1000
 assert o.health()["tenant_scoped"] and o.production_readiness()["ready"]
