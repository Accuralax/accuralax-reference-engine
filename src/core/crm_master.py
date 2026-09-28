import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = os.getenv("CRM_MASTER_DB_PATH", os.path.join("data", "crm_master.sqlite3"))

class CRMIdentityEngine:
    """Persistent canonical customer/organisation master-data registry.

    Uses deterministic normalized keys for duplicate detection. A browser locale,
    display name, or inferred geography never becomes an identity key.
    """

    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS master_clients(
                client_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                entity_type TEXT NOT NULL, display_name TEXT NOT NULL,
                email TEXT, phone TEXT, country TEXT, identity_id TEXT,
                external_ref TEXT, status TEXT NOT NULL, profile_json TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS client_keys(
                key_id TEXT PRIMARY KEY, client_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                key_type TEXT NOT NULL, key_value TEXT NOT NULL,
                UNIQUE(tenant_id, workspace_id, key_type, key_value)
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS client_audit(
                audit_id TEXT PRIMARY KEY, client_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                action TEXT NOT NULL, details_json TEXT NOT NULL,
                changed_by TEXT NOT NULL, created_at TEXT NOT NULL
            )""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_master_clients_scope ON master_clients(tenant_id, workspace_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_client_keys_lookup ON client_keys(tenant_id, workspace_id, key_type, key_value)")

    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    @staticmethod
    def _norm_email(value):
        return str(value or "").strip().casefold()

    @staticmethod
    def _norm_phone(value):
        return re.sub(r"[^0-9+]", "", str(value or "").strip())

    @staticmethod
    def _norm_text(value):
        return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())

    @classmethod
    def _stable_key(cls, entity_type, email="", phone="", registration_number="", tax_identifier=""):
        candidates = []
        if email:
            candidates.append(("email", cls._norm_email(email)))
        if phone:
            candidates.append(("phone", cls._norm_phone(phone)))
        if registration_number:
            candidates.append(("registration_number", cls._norm_text(registration_number)))
        if tax_identifier:
            candidates.append(("tax_identifier", cls._norm_text(tax_identifier)))
        return [(k, v) for k, v in candidates if v]

    def _validate_type(self, entity_type):
        value = str(entity_type or "").lower()
        if value not in {"person", "organisation"}:
            raise ValueError("invalid_entity_type")
        return value

    def find_duplicates(self, tenant_id, workspace_id, email="", phone="", registration_number="", tax_identifier=""):
        keys = self._stable_key("", email, phone, registration_number, tax_identifier)
        if not keys:
            return []
        with self._db() as c:
            found = {}
            for key_type, key_value in keys:
                rows = c.execute(
                    "SELECT client_id FROM client_keys WHERE tenant_id=? AND workspace_id=? AND key_type=? AND key_value=?",
                    (str(tenant_id), str(workspace_id), key_type, key_value)
                ).fetchall()
                for row in rows:
                    found[row["client_id"]] = True
        return sorted(found)

    def create_client(self, tenant_id, workspace_id, entity_type, display_name,
                      email="", phone="", country="", identity_id="", external_ref="",
                      registration_number="", tax_identifier="", profile=None,
                      changed_by="system"):
        tenant_id, workspace_id = str(tenant_id), str(workspace_id)
        entity_type = self._validate_type(entity_type)
        display_name = str(display_name or "").strip()
        if not display_name:
            raise ValueError("display_name_required")
        keys = self._stable_key(entity_type, email, phone, registration_number, tax_identifier)
        duplicate_ids = self.find_duplicates(tenant_id, workspace_id, email, phone, registration_number, tax_identifier)
        if duplicate_ids:
            return {"created": False, "duplicate": True, "existing_client_ids": duplicate_ids}
        now = datetime.now(timezone.utc).isoformat()
        client_id = "CLI-" + uuid.uuid4().hex[:16].upper()
        profile_data = dict(profile or {})
        if registration_number:
            profile_data["registration_number"] = str(registration_number).strip()
        if tax_identifier:
            profile_data["tax_identifier"] = str(tax_identifier).strip()
        record = {
            "client_id": client_id, "tenant_id": tenant_id, "workspace_id": workspace_id,
            "entity_type": entity_type, "display_name": display_name,
            "email": self._norm_email(email), "phone": self._norm_phone(phone),
            "country": str(country or "").upper(), "identity_id": str(identity_id or ""),
            "external_ref": str(external_ref or ""), "status": "active",
            "profile": profile_data, "created_at": now, "updated_at": now
        }
        with self._db() as c:
            c.execute("""INSERT INTO master_clients
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (client_id, tenant_id, workspace_id, entity_type, display_name,
                 record["email"], record["phone"], record["country"], record["identity_id"],
                 record["external_ref"], "active", json.dumps(profile_data, sort_keys=True), now, now))
            for key_type, key_value in keys:
                c.execute("INSERT INTO client_keys VALUES(?,?,?,?,?,?)",
                          ("KEY-" + uuid.uuid4().hex[:16].upper(), client_id, tenant_id, workspace_id, key_type, key_value))
            c.execute("INSERT INTO client_audit VALUES(?,?,?,?,?,?,?,?)",
                      ("AUD-" + uuid.uuid4().hex[:16].upper(), client_id, tenant_id, workspace_id,
                       "created", json.dumps({"entity_type": entity_type, "keys": keys, "identity_id": identity_id}, sort_keys=True),
                       str(changed_by), now))
        return record | {"created": True, "duplicate": False}

    def get_client(self, tenant_id, workspace_id, client_id):
        with self._db() as c:
            row = c.execute("SELECT * FROM master_clients WHERE tenant_id=? AND workspace_id=? AND client_id=?",
                            (str(tenant_id), str(workspace_id), str(client_id))).fetchone()
        if not row:
            raise ValueError("client_not_found")
        result = dict(row)
        result["profile"] = json.loads(result.pop("profile_json"))
        result["stable_key"] = hashlib.sha256(f"{result['tenant_id']}:{result['workspace_id']}:{result['client_id']}".encode()).hexdigest()[:20]
        return result

    def search(self, tenant_id, workspace_id, query="", entity_type=None):
        q = str(query or "").strip().casefold()
        sql = "SELECT * FROM master_clients WHERE tenant_id=? AND workspace_id=?"
        args = [str(tenant_id), str(workspace_id)]
        if entity_type:
            sql += " AND entity_type=?"
            args.append(self._validate_type(entity_type))
        if q:
            sql += " AND (lower(display_name) LIKE ? OR lower(email) LIKE ? OR phone LIKE ? OR external_ref LIKE ?)"
            like = f"%{q}%"
            args.extend([like, like, f"%{q}%", like])
        sql += " ORDER BY display_name LIMIT 100"
        with self._db() as c:
            rows = c.execute(sql, args).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["profile"] = json.loads(item.pop("profile_json"))
            result.append(item)
        return result

    def link_identity(self, tenant_id, workspace_id, client_id, identity_id, changed_by="system"):
        current = self.get_client(tenant_id, workspace_id, client_id)
        now = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute("UPDATE master_clients SET identity_id=?, updated_at=? WHERE tenant_id=? AND workspace_id=? AND client_id=?",
                      (str(identity_id), now, str(tenant_id), str(workspace_id), str(client_id)))
            c.execute("INSERT INTO client_audit VALUES(?,?,?,?,?,?,?,?)",
                      ("AUD-" + uuid.uuid4().hex[:16].upper(), client_id, str(tenant_id), str(workspace_id),
                       "identity_linked", json.dumps({"previous_identity_id": current["identity_id"], "identity_id": str(identity_id)}),
                       str(changed_by), now))
        return self.get_client(tenant_id, workspace_id, client_id)

    def health(self):
        with self._db() as c:
            clients = c.execute("SELECT COUNT(*) FROM master_clients").fetchone()[0]
            keys = c.execute("SELECT COUNT(*) FROM client_keys").fetchone()[0]
            audits = c.execute("SELECT COUNT(*) FROM client_audit").fetchone()[0]
        return {"status":"ok","engine":"crm-master-identity","clients":clients,"stable_keys":keys,"audit_records":audits,
                "tenant_workspace_scoped":True,"duplicate_detection":True,"credentials_exposed":False}
