from src.core.omega13_autonomous_optimization import Omega13AutonomousOptimization
def test_omega13():
 o=Omega13AutonomousOptimization(); z=o.objective("t","w","q"); p=o.propose("t","w",z["objective_id"],[{"score":.9}]); assert o.approve(p["proposal_id"],"a",True)["status"]=="approved"; assert o.continuous("t","w",p["proposal_id"],metrics={"q":.9},approval=True)["release_allowed"]; assert len(o.layer_status())==40
def test_omega13_closed():
 o=Omega13AutonomousOptimization(); assert o.canary("x",approval=False)["status"]=="blocked"
