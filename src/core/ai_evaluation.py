from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone


class AIEvaluationEngine:
    """Durable evaluation and regression engine for agents and model outputs."""

    DIMENSIONS = ("grounding", "retrieval", "tool_selection", "instruction_following", "policy_compliance", "response_quality")

    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join("data", "ai_evaluation.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self.db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY, tenant_id TEXT, workspace_id TEXT,
                name TEXT, version TEXT, cases_json TEXT, created_at TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS evaluations (
                evaluation_id TEXT PRIMARY KEY, tenant_id TEXT, workspace_id TEXT,
                agent_id TEXT, model_id TEXT, model_version TEXT, dataset_id TEXT,
                scores_json TEXT, overall_score REAL, passed INTEGER, threshold REAL,
                regression INTEGER, findings_json TEXT, created_at TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS evaluation_cases (
                case_id TEXT PRIMARY KEY, dataset_id TEXT, input_json TEXT,
                expected_json TEXT, created_at TEXT
            )""")

    def db(self):
        c=sqlite3.connect(self.db_path, timeout=15.0)
        c.execute("PRAGMA busy_timeout=15000")
        c.row_factory=sqlite3.Row
        class C:
            def __enter__(s): return c
            def __exit__(s,*a): c.commit(); c.close()
        return C()

    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()

    def create_dataset(self, tenant_id, workspace_id, name, cases, version="1.0"):
        did="EVALDS-"+uuid.uuid4().hex[:12].upper(); now=self._now()
        with self.db() as c:
            c.execute("INSERT INTO datasets VALUES (?,?,?,?,?,?,?)",(did,str(tenant_id),str(workspace_id),str(name),str(version),json.dumps(cases),now))
            for case in cases:
                c.execute("INSERT INTO evaluation_cases VALUES (?,?,?,?,?)",(
                    "CASE-"+uuid.uuid4().hex[:12].upper(),did,json.dumps(case.get("input",{})),json.dumps(case.get("expected",{})),now))
        return {"dataset_id":did,"name":name,"version":version,"case_count":len(cases)}

    def get_dataset(self, tenant_id, workspace_id, dataset_id):
        with self.db() as c:r=c.execute("SELECT * FROM datasets WHERE dataset_id=? AND tenant_id=? AND workspace_id=?",(str(dataset_id),str(tenant_id),str(workspace_id))).fetchone()
        if not r:return None
        d=dict(r);d["cases"]=json.loads(d.pop("cases_json"));return d

    @staticmethod
    def _score(value):
        try:return max(0.0,min(1.0,float(value)))
        except (TypeError,ValueError):return 0.0

    def evaluate(self, tenant_id, workspace_id, *, agent_id, model_id, model_version="1", dataset_id,
                 scores, findings=None, threshold=0.8, previous_score=None):
        ds=self.get_dataset(tenant_id,workspace_id,dataset_id)
        if not ds:return {"status":"blocked","reason":"dataset_not_found"}
        normalized={k:self._score(scores.get(k,0)) for k in self.DIMENSIONS}
        overall=round(sum(normalized.values())/len(normalized),4)
        regression=previous_score is not None and overall < float(previous_score)-0.05
        passed=overall>=float(threshold) and not regression
        eid="EVAL-"+uuid.uuid4().hex[:12].upper(); now=self._now()
        payload={"evaluation_id":eid,"dataset_id":dataset_id,"agent_id":str(agent_id),"model_id":str(model_id),"model_version":str(model_version),"scores":normalized,"overall_score":overall,"passed":passed,"threshold":float(threshold),"regression":regression,"findings":findings or []}
        with self.db() as c:c.execute("INSERT INTO evaluations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(eid,str(tenant_id),str(workspace_id),str(agent_id),str(model_id),str(model_version),str(dataset_id),json.dumps(normalized),overall,int(passed),float(threshold),int(regression),json.dumps(findings or []),now))
        return payload

    def evaluate_output(self, tenant_id, workspace_id, *, agent_id, model_id, dataset_id, output, expected=None,
                         citations=None, retrieved_sources=None, tools_used=None, required_policy=True, threshold=0.8):
        output=str(output or ""); citations=citations or []; retrieved_sources=retrieved_sources or []; tools_used=tools_used or []
        grounding=1.0 if (not required_policy or (citations and retrieved_sources)) else 0.0
        retrieval=1.0 if retrieved_sources else 0.0
        tool_selection=1.0 if not tools_used or all(isinstance(x,(str,dict)) for x in tools_used) else 0.0
        instruction=1.0 if output.strip() and (expected is None or str(expected).strip().lower() in output.lower()) else (0.5 if output.strip() else 0.0)
        policy=1.0 if required_policy and citations else (1.0 if not required_policy else 0.0)
        quality=1.0 if len(output.strip())>=10 else (0.5 if output.strip() else 0.0)
        return self.evaluate(tenant_id,workspace_id,agent_id=agent_id,model_id=model_id,dataset_id=dataset_id,
            scores={"grounding":grounding,"retrieval":retrieval,"tool_selection":tool_selection,"instruction_following":instruction,"policy_compliance":policy,"response_quality":quality},
            findings=[] if all(x>0 for x in (grounding,retrieval,policy)) else ["grounding_or_policy_evidence_missing"],threshold=threshold)

    def latest(self, tenant_id, workspace_id, agent_id=None, model_id=None):
        q="SELECT * FROM evaluations WHERE tenant_id=? AND workspace_id=?";args=[str(tenant_id),str(workspace_id)]
        if agent_id:q+=" AND agent_id=?";args.append(str(agent_id))
        if model_id:q+=" AND model_id=?";args.append(str(model_id))
        q+=" ORDER BY created_at DESC LIMIT 1"
        with self.db() as c:r=c.execute(q,tuple(args)).fetchone()
        if not r:return None
        d=dict(r);d["scores"]=json.loads(d.pop("scores_json"));d["findings"]=json.loads(d.pop("findings_json"));return d

    def health(self):
        with self.db() as c:ds=c.execute("SELECT COUNT(*) FROM datasets").fetchone()[0];ev=c.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]
        return {"status":"ok","durable":True,"tenant_scoped":True,"datasets":ds,"evaluations":ev,"dimensions":list(self.DIMENSIONS),"regression_detection":True}
