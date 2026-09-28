from datetime import datetime, timezone
import os, sqlite3

JURISDICTIONS = {
    "ZA": {"name": "South Africa", "tax_currency": "ZAR", "tax_name": "VAT", "standard_rate": 0.15},
    "GB": {"name": "United Kingdom", "tax_currency": "GBP", "tax_name": "VAT", "standard_rate": 0.20},
    "DE": {"name": "Germany", "tax_currency": "EUR", "tax_name": "VAT", "standard_rate": 0.19},
    "FR": {"name": "France", "tax_currency": "EUR", "tax_name": "VAT", "standard_rate": 0.20},
    "NG": {"name": "Nigeria", "tax_currency": "NGN", "tax_name": "VAT", "standard_rate": 0.075},
    "KE": {"name": "Kenya", "tax_currency": "KES", "tax_name": "VAT", "standard_rate": 0.16},
    "GH": {"name": "Ghana", "tax_currency": "GHS", "tax_name": "VAT", "standard_rate": 0.15},
    "US": {"name": "United States", "tax_currency": "USD", "tax_name": "SALES_TAX", "standard_rate": None},
    "AU": {"name": "Australia", "tax_currency": "AUD", "tax_name": "GST", "standard_rate": 0.10},
    "CA": {"name": "Canada", "tax_currency": "CAD", "tax_name": "GST_HST", "standard_rate": 0.05},
    "AE": {"name": "United Arab Emirates", "tax_currency": "AED", "tax_name": "VAT", "standard_rate": 0.05},
    "IN": {"name": "India", "tax_currency": "INR", "tax_name": "GST", "standard_rate": None},
    "BR": {"name": "Brazil", "tax_currency": "BRL", "tax_name": "INDIRECT_TAX", "standard_rate": None},
}
DB_PATH = os.getenv("TAX_DB_PATH", os.path.join("data", "tax_jurisdiction.sqlite3"))

class TaxJurisdictionEngine:
    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        with self._db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS tax_audit (audit_id TEXT PRIMARY KEY, jurisdiction TEXT NOT NULL, tax_type TEXT NOT NULL, taxable_amount REAL NOT NULL, tax_amount REAL NOT NULL, rate REAL, source TEXT NOT NULL, created_at TEXT NOT NULL)")

    def _db(self):
        c = sqlite3.connect(self.db_path, uri=self.db_path.startswith("file:"))
        c.row_factory = sqlite3.Row
        return c

    def jurisdictions(self, code=None):
        if code:
            code = code.upper()
            if code not in JURISDICTIONS:
                raise ValueError("unsupported_jurisdiction")
            return {"code": code, **JURISDICTIONS[code]}
        return {k: {"code": k, **v} for k, v in JURISDICTIONS.items()}

    def calculate(self, jurisdiction, taxable_amount, tax_type="standard", rate=None, source="configured-rule"):
        j = jurisdiction.upper()
        if j not in JURISDICTIONS:
            raise ValueError("unsupported_jurisdiction")
        configured = JURISDICTIONS[j]["standard_rate"]
        effective = configured if rate is None else float(rate)
        if effective is None:
            raise ValueError("tax_rate_required")
        if effective < 0 or effective > 1:
            raise ValueError("invalid_tax_rate")
        amount = float(taxable_amount)
        tax = amount * effective
        audit_id = "TAX-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        created = datetime.now(timezone.utc).isoformat()
        with self._db() as c:
            c.execute("INSERT INTO tax_audit VALUES(?,?,?,?,?,?,?,?)", (audit_id, j, tax_type, amount, tax, effective, source, created))
        return {"audit_id": audit_id, "jurisdiction": j, "tax_type": tax_type, "taxable_amount": amount, "tax_amount": tax, "rate": effective, "source": source, "created_at": created}

    def health(self):
        with self._db() as c:
            audits = c.execute("SELECT COUNT(*) FROM tax_audit").fetchone()[0]
        return {"status": "ok", "engine": "tax-jurisdiction", "jurisdictions_supported": len(JURISDICTIONS), "audit_records": audits, "jurisdiction_required": True, "rates_are_configurable": True}
