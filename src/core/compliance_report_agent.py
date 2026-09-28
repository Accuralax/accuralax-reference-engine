import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

class ComplianceReportAgent:
    """Deterministic, evidence-backed compliance reporting agent."""

    def __init__(self, intelligence, db_path=None):
        self.intelligence = intelligence
        self.db_path = db_path or os.path.join("data", "compliance_reports.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        with self._db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS reports(
                report_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
                report_type TEXT NOT NULL, status TEXT NOT NULL, generated_at TEXT NOT NULL,
                generated_by TEXT NOT NULL, report_json TEXT NOT NULL, reviewed_by TEXT,
                reviewed_at TEXT, review_status TEXT)""")
            c.execute("CREATE INDEX IF NOT EXISTS idx_compliance_reports_scope ON reports(tenant_id,workspace_id,generated_at)")

    @contextmanager
    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _id():
        return f"CRPT-{uuid.uuid4().hex[:12]}"

    def generate(self, tenant_id, workspace_id, report_type="compliance_status", generated_by="agent"):
        summary = self.intelligence.summary(tenant_id, workspace_id)
        gaps = self.intelligence.gaps(tenant_id, workspace_id)
        recommendations = self.intelligence.recommendations(tenant_id, workspace_id)
        matrix = self.intelligence.engine.matrix(tenant_id, workspace_id)
        matrix_v2 = self.intelligence.engine.matrix_v2(tenant_id, workspace_id)
        traceability = self._build_traceability(matrix_v2)
        report = {
            "report_id": self._id(),
            "report_type": str(report_type),
            "generated_at": self._now(),
            "generated_by": str(generated_by),
            "scope": {"tenant_id": str(tenant_id), "workspace_id": str(workspace_id)},
            "executive_summary": self._executive_summary(summary),
            "summary": summary,
            "obligations": matrix["obligations"],
            "controls": self.intelligence._controls(tenant_id, workspace_id),
            "risks": matrix["risks"],
            "evidence": matrix["evidence"],
            "remediation_actions": matrix["actions"],
            "gaps": gaps,
            "recommendations": recommendations,
            "traceability": traceability,
            "matrix_v2": matrix_v2,
            "assurance": {
                "evidence_backed": True,
                "human_review_required": True,
                "legal_conclusion": False,
                "certification_claim": False,
            },
        }
        with self._db() as c:
            c.execute(
                "INSERT INTO reports VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (report["report_id"], str(tenant_id), str(workspace_id), str(report_type),
                 "draft", report["generated_at"], str(generated_by), json.dumps(report),
                 None, None, "pending"),
            )
        return report

    def _build_traceability(self, matrix):
        rows = matrix.get("rows", [])
        return {
            "obligation_rows": len(rows),
            "covered_controls": sum(1 for row in rows if row.get("control_coverage")),
            "covered_evidence": sum(1 for row in rows if row.get("evidence_coverage")),
            "verified_evidence": sum(1 for row in rows if row.get("verified_evidence_coverage")),
            "unlinked_controls": len(matrix.get("unlinked_controls", [])),
            "unlinked_evidence": len(matrix.get("unlinked_evidence", [])),
            "risk_count": len(matrix.get("risks", [])),
            "action_count": len(matrix.get("actions", [])),
            "source": "compliance_risk_matrix_v2",
        }

    def review(self, tenant_id, workspace_id, report_id, reviewer, approved):
        if not reviewer:
            raise ValueError("reviewer_required")
        with self._db() as c:
            row = c.execute(
                "SELECT * FROM reports WHERE report_id=? AND tenant_id=? AND workspace_id=?",
                (report_id, str(tenant_id), str(workspace_id)),
            ).fetchone()
            if not row:
                raise ValueError("report_not_found")
            status = "approved" if bool(approved) else "rejected"
            c.execute(
                "UPDATE reports SET status=?,reviewed_by=?,reviewed_at=?,review_status=? WHERE report_id=?",
                (status, str(reviewer), self._now(), status, report_id),
            )
        return self.get(tenant_id, workspace_id, report_id)

    def get(self, tenant_id, workspace_id, report_id):
        with self._db() as c:
            row = c.execute(
                "SELECT * FROM reports WHERE report_id=? AND tenant_id=? AND workspace_id=?",
                (report_id, str(tenant_id), str(workspace_id)),
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["report"] = json.loads(result.pop("report_json"))
        return result

    def recent(self, tenant_id, workspace_id, limit=10):
        limit = max(1, min(int(limit), 50))
        with self._db() as c:
            rows = c.execute(
                "SELECT report_id,report_type,status,generated_at,generated_by,reviewed_by,reviewed_at,review_status FROM reports WHERE tenant_id=? AND workspace_id=? ORDER BY generated_at DESC LIMIT ?",
                (str(tenant_id), str(workspace_id), limit),
            ).fetchall()
        return [dict(x) for x in rows]

    @staticmethod
    def _executive_summary(summary):
        return {
            "obligations": summary["obligations"],
            "gaps": summary["gaps"],
            "open_high_or_critical_risks": summary["open_high_or_critical_risks"],
            "open_actions": summary["open_actions"],
            "verified_evidence": summary["verified_evidence"],
            "message": (
                "Report is evidence-backed and requires authorized human review before being treated as an approved compliance assessment."
            ),
        }

    def health(self):
        return {
            "status": "ok",
            "engine": "compliance-report-agent",
            "evidence_backed": True,
            "persistent_reports": True,
            "human_review_required": True,
            "legal_conclusions": False,
            "certification_claims": False,
        }
