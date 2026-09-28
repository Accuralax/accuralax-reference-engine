from pathlib import Path
from src.core.event_bus import EventBus
from src.core.intelligence_event_fabric import IntelligenceEventFabric
def test_signal_classification_and_persistence(tmp_path:Path):
 b=EventBus(str(tmp_path/"e.sqlite3"));f=IntelligenceEventFabric(str(tmp_path/"s.sqlite3"));e=b.publish("compliance.assessment.requested","t1","w1","a","case","C1","R1",{"risk":"high"});s=f.ingest(e);assert s["category"]=="compliance" and s["priority"]=="high" and s["confidence"]>=.9;assert len(f.list_signals("t1","w1"))==1
def test_signal_idempotency_and_scope(tmp_path:Path):
 b=EventBus(str(tmp_path/"e.sqlite3"));f=IntelligenceEventFabric(str(tmp_path/"s.sqlite3"));e1=b.publish("security.alert.created","t1","w1","a","alert","A1","R1",{});e2=b.publish("security.alert.created","t2","w2","a","alert","A1","R2",{});s1=f.ingest(e1);assert s1["signal_id"]==f.ingest(e1)["signal_id"];assert s1["signal_id"]!=f.ingest(e2)["signal_id"];assert len(f.list_signals("t1","w1"))==1 and len(f.list_signals("t2","w2"))==1
def test_signal_budget_is_bounded(tmp_path:Path):
 b=EventBus(str(tmp_path/"e.sqlite3"));f=IntelligenceEventFabric(str(tmp_path/"s.sqlite3"),1);e1=b.publish("risk.alert","t1","w1","a","risk","R1","R1",{});e2=b.publish("risk.alert","t1","w1","a","risk","R2","R2",{});f.ingest(e1)
 try:f.ingest(e2);assert False
 except RuntimeError as x:assert str(x)=="intelligence_signal_budget_exhausted"
