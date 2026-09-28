from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone


class ModelGateway:
    """Governed provider-neutral AI model gateway.

    Claude is the governed generation provider; embeddings remain provider-abstract.
    The gateway resolves only registered models and records every decision.
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join("data", "model_gateway.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self.db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS models (
                model_id TEXT, provider TEXT, purpose TEXT, version TEXT, status TEXT,
                context_window INTEGER, input_cost REAL, output_cost REAL,
                capabilities TEXT, policy TEXT, created_at TEXT, updated_at TEXT,
                PRIMARY KEY (provider, model_id, version)
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS policies (
                policy_id TEXT PRIMARY KEY, tenant_id TEXT, workspace_id TEXT,
                purpose TEXT, preferred_provider TEXT, allowed_models TEXT,
                max_input_tokens INTEGER, max_output_tokens INTEGER, max_cost REAL,
                require_grounding INTEGER, require_evaluation INTEGER, created_at TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY, tenant_id TEXT, workspace_id TEXT,
                agent_id TEXT, purpose TEXT, provider TEXT, model_id TEXT,
                version TEXT, allowed INTEGER, reason TEXT, input_tokens INTEGER,
                output_tokens INTEGER, cost REAL, latency_ms REAL, created_at TEXT
            )""")
        self._bootstrap()

    def db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        class C:
            def __enter__(s): return c
            def __exit__(s, *a): c.commit(); c.close()
        return C()

    @staticmethod
    def _now(): return datetime.now(timezone.utc).isoformat()

    def _bootstrap(self):
        with self.db() as c:
            if c.execute("SELECT COUNT(*) FROM models").fetchone()[0]: return
        self.register_model("anthropic", "claude", "generation", "1", capabilities=["generation", "reasoning", "tool_use"], policy={"governed": True})
        self.register_model("openai", "embedding-default", "embedding", "1", capabilities=["embeddings"], policy={"provider_abstract": True})

    def register_model(self, provider, model_id, purpose, version="1", *, status="active", context_window=0,
                       input_cost=0.0, output_cost=0.0, capabilities=None, policy=None):
        if purpose == "generation" and provider != "anthropic":
            return {"status": "blocked", "reason": "generation_provider_must_be_claude"}
        now = self._now()
        with self.db() as c:
            c.execute("""INSERT OR REPLACE INTO models VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (str(model_id), str(provider), str(purpose), str(version), str(status), int(context_window),
                       float(input_cost), float(output_cost), json.dumps(capabilities or []),
                       json.dumps(policy or {}, sort_keys=True), now, now))
        return self.get_model(provider, model_id, version)

    def get_model(self, provider, model_id, version="1"):
        with self.db() as c:
            r = c.execute("SELECT * FROM models WHERE provider=? AND model_id=? AND version=?", (str(provider),str(model_id),str(version))).fetchone()
        if not r: return None
        d=dict(r); d["capabilities"]=json.loads(d["capabilities"]); d["policy"]=json.loads(d["policy"]); return d

    def register_policy(self, tenant_id, workspace_id, policy_id, purpose, *, preferred_provider="anthropic",
                        allowed_models=None, max_input_tokens=0, max_output_tokens=0, max_cost=0.0,
                        require_grounding=True, require_evaluation=True):
        if purpose == "generation" and preferred_provider != "anthropic":
            return {"status":"blocked", "reason":"generation_provider_must_be_claude"}
        with self.db() as c:
            c.execute("""INSERT OR REPLACE INTO policies VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                      (str(policy_id),str(tenant_id),str(workspace_id),str(purpose),str(preferred_provider),
                       json.dumps(allowed_models or []),int(max_input_tokens),int(max_output_tokens),float(max_cost),
                       int(bool(require_grounding)),int(bool(require_evaluation)),self._now()))
        return self.get_policy(tenant_id, workspace_id, policy_id)

    def get_policy(self, tenant_id, workspace_id, policy_id):
        with self.db() as c:
            r=c.execute("SELECT * FROM policies WHERE tenant_id=? AND workspace_id=? AND policy_id=?",(str(tenant_id),str(workspace_id),str(policy_id))).fetchone()
        if not r:return None
        d=dict(r); d["allowed_models"]=json.loads(d["allowed_models"]); return d

    def resolve(self, tenant_id, workspace_id, *, agent_id="system", purpose="generation", policy_id=None,
                requested_model=None, input_tokens=0, output_tokens=0, estimated_cost=0.0):
        t,w=str(tenant_id),str(workspace_id)
        policy=self.get_policy(t,w,policy_id) if policy_id else None
        provider="anthropic" if purpose=="generation" else "openai"
        candidates=[]
        if requested_model:
            with self.db() as c:
                rows=c.execute("SELECT * FROM models WHERE model_id=? AND purpose=? AND status='active'",(str(requested_model),str(purpose))).fetchall()
        else:
            with self.db() as c:
                rows=c.execute("SELECT * FROM models WHERE provider=? AND purpose=? AND status='active' ORDER BY updated_at DESC",(provider,str(purpose))).fetchall()
        for row in rows:
            m=dict(row); m["capabilities"]=json.loads(m["capabilities"]); m["policy"]=json.loads(m["policy"]); candidates.append(m)
        if policy:
            if policy["preferred_provider"] != provider: return self._decision(t,w,agent_id,purpose,False,"provider_policy_denied",None,0,0,0)
            if policy["allowed_models"]:
                candidates=[m for m in candidates if m["model_id"] in policy["allowed_models"]]
            if policy["max_input_tokens"] and input_tokens>policy["max_input_tokens"]: return self._decision(t,w,agent_id,purpose,False,"input_budget_exceeded",None,input_tokens,output_tokens,estimated_cost)
            if policy["max_output_tokens"] and output_tokens>policy["max_output_tokens"]: return self._decision(t,w,agent_id,purpose,False,"output_budget_exceeded",None,input_tokens,output_tokens,estimated_cost)
            if policy["max_cost"] and estimated_cost>policy["max_cost"]: return self._decision(t,w,agent_id,purpose,False,"cost_budget_exceeded",None,input_tokens,output_tokens,estimated_cost)
        if not candidates: return self._decision(t,w,agent_id,purpose,False,"no_approved_model",None,input_tokens,output_tokens,estimated_cost)
        m=candidates[0]
        return self._decision(t,w,agent_id,purpose,True,"approved",m,input_tokens,output_tokens,estimated_cost)

    def _decision(self,t,w,agent_id,purpose,allowed,reason,m,input_tokens,output_tokens,cost):
        now=self._now(); did="MG-"+uuid.uuid4().hex[:12].upper()
        with self.db() as c:
            c.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(did,t,w,str(agent_id),str(purpose),m["provider"] if m else None,m["model_id"] if m else None,m["version"] if m else None,int(allowed),str(reason),int(input_tokens),int(output_tokens),float(cost),0.0,now))
        return {"allowed":allowed,"reason":reason,"decision_id":did,"model":m}

    def evaluate_gate(self, evaluation_engine, tenant_id, workspace_id, *, agent_id, model_id,
                      dataset_id, scores, threshold=0.8, previous_score=None):
        result = evaluation_engine.evaluate(
            tenant_id, workspace_id, agent_id=agent_id, model_id=model_id,
            dataset_id=dataset_id, scores=scores, threshold=threshold,
            previous_score=previous_score,
        )
        return {
            "allowed": bool(result.get("passed")),
            "reason": "evaluation_passed" if result.get("passed") else (
                "evaluation_regression" if result.get("regression") else "evaluation_threshold_failed"
            ),
            "evaluation": result,
        }

    def health(self):
        with self.db() as c:
            models=c.execute("SELECT COUNT(*) FROM models").fetchone()[0]; policies=c.execute("SELECT COUNT(*) FROM policies").fetchone()[0]; decisions=c.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        return {"status":"ok","durable":True,"generation_provider":"anthropic_claude","embedding_provider":"abstract","models":models,"policies":policies,"decisions":decisions,"credentials_exposed":False}
