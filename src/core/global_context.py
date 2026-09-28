import json
import os
import sqlite3
from datetime import datetime, timezone
from .internationalization import Internationalization, COUNTRIES, LANGUAGE_NAMES

DB_PATH = os.getenv("GLOBAL_CONTEXT_DB_PATH", os.path.join("data", "global_context.sqlite3"))

class GlobalContext:
    """Persistent global preferences shared by every product module."""
    FIELDS = ("country","language","locale","currency","timezone","measurement_system")

    def __init__(self, db_path=DB_PATH, international=None):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        self.i18n = international or Internationalization()
        self._init()

    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _init(self):
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS global_preferences(
              scope_type TEXT NOT NULL, scope_id TEXT NOT NULL,
              tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              preferences_json TEXT NOT NULL, updated_at TEXT NOT NULL,
              updated_by TEXT, PRIMARY KEY(scope_type,scope_id,tenant_id,workspace_id))""")
            c.execute("""CREATE TABLE IF NOT EXISTS global_preference_audit(
              event_id INTEGER PRIMARY KEY AUTOINCREMENT, scope_type TEXT NOT NULL,
              scope_id TEXT NOT NULL, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              changes_json TEXT NOT NULL, changed_by TEXT, changed_at TEXT NOT NULL)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_global_pref_scope ON global_preferences(tenant_id,workspace_id,scope_type)")

    def _validate(self, prefs):
        clean = {}
        for key in self.FIELDS:
            if key in prefs and prefs[key] not in (None, ""):
                clean[key] = str(prefs[key])
        if "country" in clean:
            clean["country"] = clean["country"].upper()
            if clean["country"] not in COUNTRIES:
                raise ValueError("unsupported_country")
        if "timezone" in clean:
            from zoneinfo import ZoneInfo
            try: ZoneInfo(clean["timezone"])
            except Exception: raise ValueError("invalid_timezone")
        if "language" in clean:
            clean["language"] = clean["language"].split("-")[0].lower()
            if clean["language"] not in LANGUAGE_NAMES:
                raise ValueError("unsupported_language")
        if "currency" in clean: clean["currency"] = clean["currency"].upper()
        return clean
    def get_preferences(self, tenant_id, workspace_id, user_id=None):
        rows = []
        with self._db() as c:
            if user_id:
                rows.append(c.execute("SELECT * FROM global_preferences WHERE scope_type='user' AND scope_id=? AND tenant_id=? AND workspace_id=?", (str(user_id),tenant_id,workspace_id)).fetchone())
            rows.append(c.execute("SELECT * FROM global_preferences WHERE scope_type='workspace' AND scope_id=? AND tenant_id=? AND workspace_id=?", (workspace_id,tenant_id,workspace_id)).fetchone())
            rows.append(c.execute("SELECT * FROM global_preferences WHERE scope_type='tenant' AND scope_id=? AND tenant_id=? AND workspace_id=?", (tenant_id,tenant_id,workspace_id)).fetchone())
        merged = {}
        sources = []
        for row in reversed(rows):
            if row:
                merged.update(json.loads(row["preferences_json"]))
                sources.append(row["scope_type"])
        return merged, sources

    def resolve(self, tenant_id="default", workspace_id="default", user_id=None, headers=None):
        prefs, sources = self.get_preferences(tenant_id, workspace_id, user_id)
        user = prefs if user_id else {}
        ctx = self.i18n.resolve(user=user, headers=headers or {})
        ctx["preference_sources"] = sources
        ctx["tenant_id"] = tenant_id
        ctx["workspace_id"] = workspace_id
        ctx["user_id"] = user_id
        return ctx

    def set_preferences(self, tenant_id, workspace_id, scope_type, scope_id, preferences, changed_by="system"):
        if scope_type not in {"tenant","workspace","user"}: raise ValueError("invalid_scope_type")
        if not scope_id: raise ValueError("scope_id_required")
        clean = self._validate(preferences or {})
        ts = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            old = c.execute("SELECT preferences_json FROM global_preferences WHERE scope_type=? AND scope_id=? AND tenant_id=? AND workspace_id=?", (scope_type,str(scope_id),tenant_id,workspace_id)).fetchone()
            previous = json.loads(old["preferences_json"]) if old else {}
            c.execute("""INSERT INTO global_preferences VALUES (?,?,?,?,?,?,?)
              ON CONFLICT(scope_type,scope_id,tenant_id,workspace_id) DO UPDATE SET preferences_json=excluded.preferences_json,updated_at=excluded.updated_at,updated_by=excluded.updated_by""", (scope_type,str(scope_id),tenant_id,workspace_id,json.dumps(clean,sort_keys=True),ts,changed_by))
            changes = {k: {"from": previous.get(k), "to": clean.get(k)} for k in set(previous)|set(clean) if previous.get(k) != clean.get(k)}
            c.execute("INSERT INTO global_preference_audit(scope_type,scope_id,tenant_id,workspace_id,changes_json,changed_by,changed_at) VALUES (?,?,?,?,?,?,?)", (scope_type,str(scope_id),tenant_id,workspace_id,json.dumps(changes,sort_keys=True),changed_by,ts))
        return self.resolve(tenant_id, workspace_id, scope_id if scope_type=="user" else None)
    def health(self):
        with self._db() as c:
            preferences = c.execute("SELECT COUNT(*) FROM global_preferences").fetchone()[0]
            audits = c.execute("SELECT COUNT(*) FROM global_preference_audit").fetchone()[0]
        return {"status":"ok","engine":"global-system-context","preferences":preferences,"audit_events":audits,"automatic_switch":True,"utc_audit_timestamps":True,"identity_inference_from_ip":False}
