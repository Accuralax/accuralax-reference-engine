import sqlite3
from src.core.agent_governance import AgentGovernance
from src.core.autonomous_decision_engine import AutonomousDecisionEngine
def test_decision_requires_governance_for_high_risk(tmp_path):
 g=AgentGovernance(str(tmp_path/"g.sqlite3"));d=AutonomousDecisionEngine(g,db_path=str(tmp_path/"d.sqlite3"));s={"signal_id":"SIG-1"}
 x=d.decide("t","w","a",s,"execute","external");assert x["status"]=="approval_required" and x["execution_allowed"] is False
def test_decision_allows_registered_read_tool(tmp_path):
 g=AgentGovernance(str(tmp_path/"g.sqlite3"));g.set_tool("t","w","a","lookup",True,False);d=AutonomousDecisionEngine(g,db_path=str(tmp_path/"d.sqlite3"));x=d.decide("t","w","a",{"signal_id":"S"},"lookup","read",tool="lookup");assert x["status"]=="approved"
def test_decision_budget_is_bounded(tmp_path):
 g=AgentGovernance(str(tmp_path/"g.sqlite3"));d=AutonomousDecisionEngine(g,max_decisions=1,db_path=str(tmp_path/"d.sqlite3"));d.decide("t","w","a",{"signal_id":"S"})
 try:d.decide("t","w","a",{"signal_id":"S2"});assert False
 except RuntimeError as e:assert str(e)=="decision_budget_exhausted"
