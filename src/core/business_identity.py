import re
import sqlite3
import os
import uuid
from datetime import datetime, timezone

from .internationalization import COUNTRIES

DB_PATH = os.getenv("IDENTITY_DB_PATH", os.path.join("data", "business_identity.sqlite3"))

ADDRESS_RULES = {
    "ZA": {"required": ["address_line1", "city", "province", "postal_code"], "postal_pattern": r"^\d{4}$", "region_label": "province"},
    "US": {"required": ["address_line1", "city", "state", "zip_code"], "postal_pattern": r"^\d{5}(-\d{4})?$", "region_label": "state"},
    "GB": {"required": ["address_line1", "city", "postcode"], "postal_pattern": r"^[A-Z0-9 ]{5,8}$", "region_label": "county"},
    "DE": {"required": ["address_line1", "postal_code", "city"], "postal_pattern": r"^\d{5}$", "region_label": "state"},
    "FR": {"required": ["address_line1", "postal_code", "city"], "postal_pattern": r"^\d{5}$", "region_label": "region"},
    "NG": {"required": ["address_line1", "city", "state"], "postal_pattern": r"^\d{6}$", "region_label": "state"},
    "KE": {"required": ["address_line1", "city", "postal_code"], "postal_pattern": r"^\d{5}$", "region_label": "county"},
    "GH": {"required": ["address_line1", "city", "region"], "postal_pattern": None, "region_label": "region"},
    "BR": {"required": ["address_line1", "city", "state", "postal_code"], "postal_pattern": r"^\d{5}-?\d{3}$", "region_label": "state"},
    "IN": {"required": ["address_line1", "city", "state", "postal_code"], "postal_pattern": r"^\d{6}$", "region_label": "state"},
    "AU": {"required": ["address_line1", "suburb", "state", "postcode"], "postal_pattern": r"^\d{4}$", "region_label": "state"},
    "CA": {"required": ["address_line1", "city", "province", "postal_code"], "postal_pattern": r"^[A-Z]\d[A-Z] ?\d[A-Z]\d$", "region_label": "province"},
    "AE": {"required": ["address_line1", "area", "city", "emirate"], "postal_pattern": None, "region_label": "emirate"},
}

PHONE_PATTERNS = {
    "ZA": r"^\+27[1-8]\d{8}$",
    "US": r"^\+1[2-9]\d{9}$",
    "GB": r"^\+44\d{9,10}$",
    "NG": r"^\+234\d{10}$",
    "KE": r"^\+254\d{9}$",
    "GH": r"^\+233\d{9}$",
    "DE": r"^\+49\d{7,13}$",
    "FR": r"^\+33\d{9}$",
    "BR": r"^\+55\d{10,11}$",
    "IN": r"^\+91\d{10}$",
    "AU": r"^\+61\d{9}$",
    "CA": r"^\+1[2-9]\d{9}$",
    "AE": r"^\+971\d{9}$",
}

class BusinessIdentityEngine:
    """International organisation identity, legal-address validation and audit.

    Identity facts are explicit records. Browser locale can help presentation but
    never creates or changes a legal identity or legal address.
    """

    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS organisation_identities(
                identity_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                legal_name TEXT NOT NULL, trading_name TEXT, registration_number TEXT,
                tax_identifier TEXT, country TEXT NOT NULL, legal_address_json TEXT NOT NULL,
                phone TEXT, email TEXT, website TEXT, status TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                UNIQUE(tenant_id, workspace_id, legal_name)
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS identity_audit(
                audit_id TEXT PRIMARY KEY, identity_id TEXT NOT NULL, tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL, action TEXT NOT NULL, changes_json TEXT NOT NULL,
                changed_by TEXT NOT NULL, created_at TEXT NOT NULL
            )""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_identity_scope ON organisation_identities(tenant_id, workspace_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_identity_audit_scope ON identity_audit(tenant_id, workspace_id, created_at)")

    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _country(self, country):
        code = str(country or "").upper()
        if code not in COUNTRIES:
            raise ValueError("unsupported_country")
        return code

    def address_schema(self, country):
        code = self._country(country)
        rule = ADDRESS_RULES.get(code, {"required": ["address_line1", "city"], "postal_pattern": None, "region_label": "region"})
        profile = COUNTRIES[code]
        return {
            "country": code,
            "country_name": profile["name"],
            "required_fields": rule["required"],
            "postal_field": profile["postal"],
            "region_label": rule["region_label"],
            "address_order": profile["address_order"],
            "phone_country_code": profile["phone"],
        }

    def validate_address(self, country, address):
        code = self._country(country)
        if not isinstance(address, dict):
            raise ValueError("address_must_be_object")
        rule = ADDRESS_RULES.get(code, {"required": ["address_line1", "city"], "postal_pattern": None, "region_label": "region"})
        missing = [field for field in rule["required"] if not str(address.get(field, "")).strip()]
        errors = []
        postal_field = COUNTRIES[code]["postal"]
        postal = str(address.get(postal_field, "")).strip()
        if postal and rule["postal_pattern"] and not re.fullmatch(rule["postal_pattern"], postal, re.IGNORECASE):
            errors.append({"field": postal_field, "code": "invalid_postal_code"})
        if not postal and postal_field in rule["required"]:
            errors.append({"field": postal_field, "code": "postal_code_required"})
        normalized = {str(k): str(v).strip() for k, v in address.items() if v is not None}
        return {"valid": not missing and not errors, "country": code, "missing_fields": missing, "errors": errors, "normalized_address": normalized}

    def validate_phone(self, country, phone):
        code = self._country(country)
        value = str(phone or "").strip().replace(" ", "")
        pattern = PHONE_PATTERNS.get(code)
        valid = bool(value) and (re.fullmatch(pattern, value) is not None if pattern else value.startswith("+"))
        return {"valid": valid, "country": code, "phone": value, "country_code": COUNTRIES[code]["phone"]}

    def create_identity(self, tenant_id, workspace_id, legal_name, country, legal_address,
                        trading_name="", registration_number="", tax_identifier="",
                        phone="", email="", website="", changed_by="system"):
        tenant_id, workspace_id = str(tenant_id), str(workspace_id)
        legal_name = str(legal_name or "").strip()
        if not legal_name:
            raise ValueError("legal_name_required")
        code = self._country(country)
        address_result = self.validate_address(code, legal_address)
        if not address_result["valid"]:
            raise ValueError({"code": "invalid_legal_address", "details": address_result})
        if phone:
            phone_result = self.validate_phone(code, phone)
            if not phone_result["valid"]:
                raise ValueError("invalid_phone")
        now = datetime.now(timezone.utc).isoformat()
        identity_id = "ORG-" + uuid.uuid4().hex[:16].upper()
        record = {
            "identity_id": identity_id, "tenant_id": tenant_id, "workspace_id": workspace_id,
            "legal_name": legal_name, "trading_name": str(trading_name or "").strip(),
            "registration_number": str(registration_number or "").strip(),
            "tax_identifier": str(tax_identifier or "").strip(), "country": code,
            "legal_address": address_result["normalized_address"], "phone": str(phone or "").strip(),
            "email": str(email or "").strip(), "website": str(website or "").strip(),
            "status": "active", "created_at": now, "updated_at": now
        }
        import json
        with self._db() as c:
            c.execute("""INSERT INTO organisation_identities
                (identity_id,tenant_id,workspace_id,legal_name,trading_name,registration_number,tax_identifier,country,
                 legal_address_json,phone,email,website,status,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (identity_id, tenant_id, workspace_id, legal_name, record["trading_name"],
                 record["registration_number"], record["tax_identifier"], code,
                 json.dumps(record["legal_address"], sort_keys=True), record["phone"], record["email"],
                 record["website"], "active", now, now))
            c.execute("""INSERT INTO identity_audit
                VALUES(?,?,?,?,?,?,?,?)""",
                ("AUD-" + uuid.uuid4().hex[:16].upper(), identity_id, tenant_id, workspace_id,
                 "created", json.dumps({"country": code, "legal_address": record["legal_address"]}, sort_keys=True),
                 str(changed_by), now))
        return record

    def get_identity(self, tenant_id, workspace_id, identity_id):
        import json
        with self._db() as c:
            row = c.execute("SELECT * FROM organisation_identities WHERE tenant_id=? AND workspace_id=? AND identity_id=?",
                            (str(tenant_id), str(workspace_id), str(identity_id))).fetchone()
        if not row:
            raise ValueError("identity_not_found")
        result = dict(row)
        result["legal_address"] = json.loads(result.pop("legal_address_json"))
        return result

    def list_identities(self, tenant_id, workspace_id):
        import json
        with self._db() as c:
            rows = c.execute("SELECT * FROM organisation_identities WHERE tenant_id=? AND workspace_id=? ORDER BY legal_name",
                             (str(tenant_id), str(workspace_id))).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["legal_address"] = json.loads(item.pop("legal_address_json"))
            result.append(item)
        return result

    def health(self):
        with self._db() as c:
            identities = c.execute("SELECT COUNT(*) FROM organisation_identities").fetchone()[0]
            audits = c.execute("SELECT COUNT(*) FROM identity_audit").fetchone()[0]
        return {
            "status": "ok", "engine": "business-identity-address",
            "countries_supported": len(COUNTRIES), "identity_records": identities,
            "audit_records": audits, "legal_address_explicit": True,
            "browser_location_creates_identity": False
        }
