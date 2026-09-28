from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


class AgentRegistry:
    """Durable, tenant-scoped registry for governed agents and capabilities."""

    STATUSES = {"draft", "active", "paused", "retired"}

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.path.join("data", "agent_registry.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self.db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT, tenant_id TEXT, workspace_id TEXT, name TEXT,
                role TEXT, version TEXT, status TEXT, owner_id TEXT,
                purpose TEXT, model_policy TEXT, knowledge_scopes TEXT,
                capabilities TEXT, allowed_tools TEXT, allowed_skills TEXT,
                governance_policy TEXT, health TEXT, created_at TEXT, updated_at TEXT,
                PRIMARY KEY (tenant_id, workspace_id, agent_id)
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS agent_versions (
                version_id TEXT PRIMARY KEY, tenant_id TEXT, workspace_id TEXT,
                agent_id TEXT, version TEXT, manifest_json TEXT, created_at TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS skills (
                skill_id TEXT, tenant_id TEXT, workspace_id TEXT, name TEXT,
                version TEXT, status TEXT, owner_id TEXT, description TEXT,
                dependencies TEXT, permissions TEXT, manifest_json TEXT,
                created_at TEXT, updated_at TEXT,
                PRIMARY KEY (tenant_id, workspace_id, skill_id)
            )""")
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS skill_versions (version_id TEXT PRIMARY KEY, tenant_id TEXT, workspace_id TEXT, skill_id TEXT, version TEXT, manifest_json TEXT, created_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS skill_publications (publication_id TEXT PRIMARY KEY, tenant_id TEXT, workspace_id TEXT, skill_id TEXT, version TEXT, state TEXT, evaluation_id TEXT, approved_by TEXT, published_at TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS skill_deployments (deployment_id TEXT PRIMARY KEY, tenant_id TEXT, workspace_id TEXT, skill_id TEXT, version TEXT, environment TEXT, state TEXT, deployed_at TEXT, retired_at TEXT)")
        if db_path is None:
            self.bootstrap_static_catalog()

    def db(self):
        c = sqlite3.connect(self.db_path, timeout=15.0)
        c.execute("PRAGMA busy_timeout=15000")
        c.row_factory = sqlite3.Row
        class C:
            def __enter__(s): return c
            def __exit__(s, *a): c.commit(); c.close()
        return C()

    @staticmethod
    def _scope(tenant_id, workspace_id):
        return str(tenant_id), str(workspace_id)

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _decode(row):
        if not row:
            return None
        d = dict(row)
        for key in ("model_policy", "knowledge_scopes", "capabilities", "allowed_tools", "allowed_skills", "governance_policy", "health", "dependencies", "permissions", "manifest_json"):
            if key in d:
                try: d[key] = json.loads(d[key])
                except (TypeError, ValueError): pass
        return d

    def bootstrap_static_catalog(self, tenant_id="default", workspace_id="default"):
        """Import the governed static agent/skill catalogue once into the runtime registry."""
        root = Path(__file__).resolve().parents[1]
        permissions = yaml.safe_load((root / "config" / "agent_permissions.yaml").read_text(encoding="utf-8")) or {}
        brains = yaml.safe_load((root / "config" / "agent_brains.yaml").read_text(encoding="utf-8")) or {}
        skills = yaml.safe_load((root / "knowledge" / "skills.yaml").read_text(encoding="utf-8")) or {}
        existing = {a["agent_id"] for a in self.list_agents(tenant_id, workspace_id)}
        for agent_id, item in (permissions.get("agents") or {}).items():
            if agent_id in existing:
                continue
            brain = (brains.get("agents") or {}).get(agent_id, {})
            self.register_agent(
                tenant_id, workspace_id, agent_id, agent_id.replace("_", " ").title(),
                role=item.get("role", "specialist"), version=str(brain.get("version", "1.0.0")),
                status="active", owner_id="platform", purpose=", ".join(brain.get("domains", [])),
                capabilities=brain.get("domains", []), allowed_tools=item.get("allowed_tools", []),
                allowed_skills=item.get("allowed_skills", []),
                governance_policy={"requires_human_approval": bool(item.get("requires_human_approval", False))}
            )
        existing_skills = {s["skill_id"] for s in self.list_skills(tenant_id, workspace_id)}
        for skill_id, item in (skills.get("skills") or {}).items():
            if skill_id in existing_skills:
                continue
            self.register_skill(
                tenant_id, workspace_id, skill_id, item.get("name", skill_id),
                version="1.0.0", status="active", owner_id="platform",
                description=item.get("purpose", ""), permissions={
                    "requires_consent": bool(item.get("requires_consent", False)),
                    "human_review": bool(item.get("human_review", False))
                },
                manifest=item
            )
        return {"agents": len(self.list_agents(tenant_id, workspace_id)),
                "skills": len(self.list_skills(tenant_id, workspace_id))}

    def register_agent(self, tenant_id, workspace_id, agent_id, name, *, role="specialist",
                       version="1.0.0", status="draft", owner_id="system", purpose="",
                       model_policy=None, knowledge_scopes=None, capabilities=None,
                       allowed_tools=None, allowed_skills=None, governance_policy=None):
        t, w = self._scope(tenant_id, workspace_id)
        status = str(status).lower()
        if status not in self.STATUSES:
            return {"status": "blocked", "reason": "invalid_status"}
        now = self._now()
        health = {"state": "unknown", "last_checked_at": None}
        values = (t, w, str(agent_id), str(name), str(role), str(version), status, str(owner_id), str(purpose),
                  json.dumps(model_policy or {}, sort_keys=True), json.dumps(knowledge_scopes or []),
                  json.dumps(capabilities or []), json.dumps(allowed_tools or []), json.dumps(allowed_skills or []),
                  json.dumps(governance_policy or {}, sort_keys=True), json.dumps(health), now, now)
        with self.db() as c:
            c.execute("""INSERT OR REPLACE INTO agents
                (tenant_id,workspace_id,agent_id,name,role,version,status,owner_id,purpose,model_policy,
                 knowledge_scopes,capabilities,allowed_tools,allowed_skills,governance_policy,health,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", values)
            c.execute("INSERT INTO agent_versions VALUES (?,?,?,?,?,?,?)", (
                "AGV-" + uuid.uuid4().hex[:12].upper(), t, w, str(agent_id), str(version),
                json.dumps({"name": name, "role": role, "purpose": purpose, "capabilities": capabilities or [],
                            "allowed_tools": allowed_tools or [], "allowed_skills": allowed_skills or []}, sort_keys=True), now))
        return self.get_agent(t, w, agent_id)

    def get_agent(self, tenant_id, workspace_id, agent_id):
        t, w = self._scope(tenant_id, workspace_id)
        with self.db() as c:
            row = c.execute("SELECT * FROM agents WHERE tenant_id=? AND workspace_id=? AND agent_id=?", (t, w, str(agent_id))).fetchone()
        return self._decode(row)

    def list_agents(self, tenant_id, workspace_id, status=None):
        t, w = self._scope(tenant_id, workspace_id)
        with self.db() as c:
            if status:
                rows = c.execute("SELECT * FROM agents WHERE tenant_id=? AND workspace_id=? AND status=? ORDER BY name", (t, w, str(status))).fetchall()
            else:
                rows = c.execute("SELECT * FROM agents WHERE tenant_id=? AND workspace_id=? ORDER BY name", (t, w)).fetchall()
        return [self._decode(r) for r in rows]

    def set_status(self, tenant_id, workspace_id, agent_id, status):
        status = str(status).lower()
        if status not in self.STATUSES:
            return {"status": "blocked", "reason": "invalid_status"}
        t, w = self._scope(tenant_id, workspace_id)
        with self.db() as c:
            cur = c.execute("UPDATE agents SET status=?,updated_at=? WHERE tenant_id=? AND workspace_id=? AND agent_id=?", (status, self._now(), t, w, str(agent_id)))
        return self.get_agent(t, w, agent_id) if cur.rowcount else None

    def record_health(self, tenant_id, workspace_id, agent_id, state, *, details=None):
        t, w = self._scope(tenant_id, workspace_id)
        health = {"state": str(state), "details": details or {}, "last_checked_at": self._now()}
        with self.db() as c:
            cur = c.execute("UPDATE agents SET health=?,updated_at=? WHERE tenant_id=? AND workspace_id=? AND agent_id=?", (json.dumps(health, sort_keys=True), self._now(), t, w, str(agent_id)))
        return self.get_agent(t, w, agent_id) if cur.rowcount else None

    def register_skill(self, tenant_id, workspace_id, skill_id, name, *, version="1.0.0", status="active",
                       owner_id="system", description="", dependencies=None, permissions=None, manifest=None):
        status = str(status).lower()
        if status not in self.STATUSES:
            return {"status": "blocked", "reason": "invalid_status"}
        t, w = self._scope(tenant_id, workspace_id); now = self._now()
        with self.db() as c:
            c.execute("""INSERT OR REPLACE INTO skills
                (skill_id,tenant_id,workspace_id,name,version,status,owner_id,description,dependencies,permissions,manifest_json,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", (str(skill_id),t,w,str(name),str(version),status,str(owner_id),str(description),
                json.dumps(dependencies or []),json.dumps(permissions or []),json.dumps(manifest or {}, sort_keys=True),now,now))
        return self.get_skill(t, w, skill_id)

    def get_skill(self, tenant_id, workspace_id, skill_id):
        t, w = self._scope(tenant_id, workspace_id)
        with self.db() as c: row = c.execute("SELECT * FROM skills WHERE tenant_id=? AND workspace_id=? AND skill_id=?", (t,w,str(skill_id))).fetchone()
        return self._decode(row)

    def list_skills(self, tenant_id, workspace_id, status=None):
        t, w = self._scope(tenant_id, workspace_id)
        with self.db() as c:
            q = "SELECT * FROM skills WHERE tenant_id=? AND workspace_id=?"
            args = [t,w]
            if status: q += " AND status=?"; args.append(str(status))
            q += " ORDER BY name"
            rows = c.execute(q, tuple(args)).fetchall()
        return [self._decode(r) for r in rows]

    def resolve(self, tenant_id, workspace_id, agent_id, *, required_skill=None, required_tool=None):
        agent = self.get_agent(tenant_id, workspace_id, agent_id)
        if not agent: return {"allowed": False, "reason": "agent_not_registered"}
        if agent["status"] != "active": return {"allowed": False, "reason": "agent_not_active", "agent": agent}
        if required_skill and required_skill not in agent["allowed_skills"]: return {"allowed": False, "reason": "skill_not_granted", "agent": agent}
        if required_tool and required_tool not in agent["allowed_tools"]: return {"allowed": False, "reason": "tool_not_granted", "agent": agent}
        return {"allowed": True, "agent": agent}

    def resolve_model(self, tenant_id, workspace_id, agent_id, model_gateway, *, purpose="generation",
                      input_tokens=0, output_tokens=0, estimated_cost=0.0):
        agent = self.get_agent(tenant_id, workspace_id, agent_id)
        if not agent:
            return {"allowed": False, "reason": "agent_not_registered"}
        if agent["status"] != "active":
            return {"allowed": False, "reason": "agent_not_active"}
        policy = agent.get("model_policy") or {}
        policy_id = policy.get("policy_id")
        result = model_gateway.resolve(
            tenant_id, workspace_id, agent_id=agent_id, purpose=purpose,
            policy_id=policy_id, requested_model=policy.get("model_id"),
            input_tokens=input_tokens, output_tokens=output_tokens,
            estimated_cost=estimated_cost,
        )
        if result.get("allowed") and policy.get("provider") and result["model"]["provider"] != policy["provider"]:
            return {"allowed": False, "reason": "agent_model_provider_mismatch", "model": result.get("model")}
        return result

    def publish_skill(self, tenant_id, workspace_id, skill_id, version, evaluation_id=None, approved_by=None):
        skill=self.get_skill(tenant_id,workspace_id,skill_id)
        if not skill: return {"allowed":False,"reason":"skill_not_registered"}
        if str(skill["version"]) != str(version): return {"allowed":False,"reason":"version_not_registered"}
        if not evaluation_id or not approved_by: return {"allowed":False,"reason":"evaluation_and_approval_required"}
        t,w=self._scope(tenant_id,workspace_id); pid="PUB-"+uuid.uuid4().hex[:12].upper()
        with self.db() as c:
            c.execute("INSERT INTO skill_publications VALUES (?,?,?,?,?,?,?,?,?)",(pid,t,w,str(skill_id),str(version),"published",str(evaluation_id),str(approved_by),self._now()))
        return {"allowed":True,"publication_id":pid,"state":"published"}

    def deploy_skill(self, tenant_id, workspace_id, skill_id, version, environment="production"):
        t,w=self._scope(tenant_id,workspace_id)
        with self.db() as c:
            p=c.execute("SELECT 1 FROM skill_publications WHERE tenant_id=? AND workspace_id=? AND skill_id=? AND version=? AND state='published' LIMIT 1",(t,w,str(skill_id),str(version))).fetchone()
        if not p: return {"allowed":False,"reason":"skill_not_published"}
        did="DEP-"+uuid.uuid4().hex[:12].upper()
        with self.db() as c:
            c.execute("INSERT INTO skill_deployments VALUES (?,?,?,?,?,?,?,?,?)",(did,t,w,str(skill_id),str(version),str(environment),"deployed",self._now(),None))
        return {"allowed":True,"deployment_id":did,"state":"deployed"}

    def retire_skill(self, tenant_id, workspace_id, skill_id, version):
        t,w=self._scope(tenant_id,workspace_id)
        with self.db() as c:
            cur=c.execute("UPDATE skill_deployments SET state='retired',retired_at=? WHERE tenant_id=? AND workspace_id=? AND skill_id=? AND version=? AND state='deployed'",(self._now(),t,w,str(skill_id),str(version)))
        return {"retired":cur.rowcount}

    def health(self):
        with self.db() as c:
            agents = c.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
            active = c.execute("SELECT COUNT(*) FROM agents WHERE status='active'").fetchone()[0]
            skills = c.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
            versions = c.execute("SELECT COUNT(*) FROM agent_versions").fetchone()[0]
        return {"status":"ok", "durable":True, "tenant_scoped":True, "agents":agents,
                "active_agents":active, "skills":skills, "versions":versions,
                "lifecycle":sorted(self.STATUSES), "credentials_exposed":False}
