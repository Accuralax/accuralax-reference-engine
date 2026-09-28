from __future__ import annotations
import os
import sqlite3
from datetime import datetime, timezone


class SaaSEntitlements:
    """Tenant/workspace subscription and feature-entitlement control plane."""

    FEATURES = {
        "free": {"runtime", "knowledge", "compliance"},
        "starter": {"runtime", "knowledge", "compliance", "lms", "crm", "operations"},
        "business": {"runtime", "knowledge", "compliance", "lms", "crm", "operations", "security", "analytics", "automation"},
        "enterprise": {"runtime", "knowledge", "compliance", "lms", "crm", "operations", "security", "analytics", "automation", "custom_agents", "api"},
    }

    def __init__(self, db_path=None, usage_billing=None):
        self.db_path = db_path or os.path.join("data", "saas_entitlements.sqlite3")
        self.usage_billing = usage_billing
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS subscriptions(tenant_id TEXT,workspace_id TEXT,plan TEXT,status TEXT,trial_ends_at TEXT,updated_at TEXT,PRIMARY KEY(tenant_id,workspace_id))")
            c.execute("CREATE TABLE IF NOT EXISTS feature_overrides(tenant_id TEXT,workspace_id TEXT,feature TEXT,enabled INTEGER,updated_at TEXT,PRIMARY KEY(tenant_id,workspace_id,feature))")

    def db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        class C:
            def __enter__(s): return c
            def __exit__(s, *a): c.commit(); c.close()
        return C()

    def set_subscription(self, tenant_id, workspace_id, plan, status="active", trial_ends_at=None):
        plan = str(plan).lower()
        if plan not in self.FEATURES:
            raise ValueError("invalid_plan")
        status = str(status).lower()
        if status not in {"active", "trialing", "past_due", "suspended", "cancelled"}:
            raise ValueError("invalid_subscription_status")
        now = datetime.now(timezone.utc).isoformat()
        with self.db() as c:
            c.execute("INSERT OR REPLACE INTO subscriptions VALUES(?,?,?,?,?,?)", (str(tenant_id), str(workspace_id), plan, status, trial_ends_at, now))
        if self.usage_billing is not None:
            self.usage_billing.account(str(tenant_id), str(workspace_id), plan)
        return self.subscription(tenant_id, workspace_id)

    def subscription(self, tenant_id, workspace_id):
        with self.db() as c:
            r = c.execute("SELECT * FROM subscriptions WHERE tenant_id=? AND workspace_id=?", (str(tenant_id), str(workspace_id))).fetchone()
        if not r:
            return {"tenant_id": str(tenant_id), "workspace_id": str(workspace_id), "plan": "free", "status": "active", "trial_ends_at": None}
        return dict(r)

    def set_override(self, tenant_id, workspace_id, feature, enabled):
        with self.db() as c:
            c.execute("INSERT OR REPLACE INTO feature_overrides VALUES(?,?,?,?,?)", (str(tenant_id), str(workspace_id), str(feature), 1 if enabled else 0, datetime.now(timezone.utc).isoformat()))
        return self.check(tenant_id, workspace_id, feature)

    def check(self, tenant_id, workspace_id, feature):
        s = self.subscription(tenant_id, workspace_id)
        feature = str(feature)
        with self.db() as c:
            r = c.execute("SELECT enabled FROM feature_overrides WHERE tenant_id=? AND workspace_id=? AND feature=?", (str(tenant_id), str(workspace_id), feature)).fetchone()
        enabled = bool(r[0]) if r is not None else feature in self.FEATURES[s["plan"]]
        return {"allowed": enabled and s["status"] in {"active", "trialing"}, "feature": feature, "plan": s["plan"], "status": s["status"], "tenant_id": str(tenant_id), "workspace_id": str(workspace_id), "source": "override" if r is not None else "plan"}

    def health(self):
        with self.db() as c:
            n = c.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
        return {"status": "ok", "tenant_workspace_scoped": True, "plans": sorted(self.FEATURES), "subscriptions": n, "credentials_exposed": False}
