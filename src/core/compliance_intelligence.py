from .compliance_risk_engine import ComplianceRiskEngine

class ComplianceIntelligence:
    """Evidence-driven compliance gap detection and monitoring layer."""

    def __init__(self, engine=None):
        self.engine = engine or ComplianceRiskEngine()

    def gaps(self, tenant_id, workspace_id):
        matrix = self.engine.matrix(tenant_id, workspace_id)
        obligations = {x["obligation_id"]: x for x in matrix["obligations"]}
        controls = self._controls(tenant_id, workspace_id)
        evidence = matrix["evidence"]
        risks = matrix["risks"]
        actions = matrix["actions"]
        gaps = []

        for obligation in matrix["obligations"]:
            oid = obligation["obligation_id"]
            linked_controls = [x for x in controls if x["obligation_id"] == oid]
            linked_evidence = [x for x in evidence if x["obligation_id"] == oid]
            if not linked_controls:
                gaps.append(self._gap("missing_control", "high", oid, obligation["name"], "No control is linked to this obligation."))
            if not linked_evidence:
                gaps.append(self._gap("missing_evidence", "high", oid, obligation["name"], "No evidence is recorded for this obligation."))
            elif not any(x["verified"] for x in linked_evidence):
                gaps.append(self._gap("unverified_evidence", "medium", oid, obligation["name"], "Evidence exists but none is verified."))
            if obligation["status"] in ("non_compliant", "open"):
                gaps.append(self._gap("obligation_status", "medium", oid, obligation["name"], f"Obligation status is {obligation['status']}."))

        for risk in risks:
            if risk["status"] in ("open", "in_progress") and risk["level"] in ("high", "critical"):
                linked = [x for x in actions if x["risk_id"] == risk["risk_id"] and x["status"] not in ("completed", "closed")]
                if not linked:
                    gaps.append(self._gap("unremediated_risk", risk["level"], risk["risk_id"], risk["title"], "High or critical risk has no active remediation action."))

        return gaps

    def summary(self, tenant_id, workspace_id):
        matrix = self.engine.matrix(tenant_id, workspace_id)
        gaps = self.gaps(tenant_id, workspace_id)
        risks = matrix["risks"]
        return {
            "tenant_id": str(tenant_id),
            "workspace_id": str(workspace_id),
            "obligations": len(matrix["obligations"]),
            "controls": len(self._controls(tenant_id, workspace_id)),
            "evidence": len(matrix["evidence"]),
            "verified_evidence": sum(int(x["verified"]) for x in matrix["evidence"]),
            "risks": len(risks),
            "open_high_or_critical_risks": sum(1 for x in risks if x["status"] in ("open","in_progress") and x["level"] in ("high","critical")),
            "open_actions": sum(1 for x in matrix["actions"] if x["status"] not in ("completed","closed")),
            "gaps": len(gaps),
            "gap_breakdown": self._breakdown(gaps),
        }

    def recommendations(self, tenant_id, workspace_id):
        gaps = self.gaps(tenant_id, workspace_id)
        return [
            {
                "gap_type": gap["type"],
                "priority": gap["priority"],
                "recommendation": self._recommendation(gap["type"]),
                "reference_id": gap["reference_id"],
            }
            for gap in gaps
        ]

    def _controls(self, tenant_id, workspace_id):
        with self.engine._db() as c:
            rows = c.execute(
                "SELECT * FROM controls WHERE tenant_id=? AND workspace_id=? ORDER BY name",
                (str(tenant_id), str(workspace_id)),
            ).fetchall()
        return [dict(x) for x in rows]

    @staticmethod
    def _gap(gap_type, priority, reference_id, title, detail):
        return {"type": gap_type, "priority": priority, "reference_id": reference_id, "title": title, "detail": detail}

    @staticmethod
    def _breakdown(gaps):
        result = {}
        for gap in gaps:
            result[gap["type"]] = result.get(gap["type"], 0) + 1
        return result

    @staticmethod
    def _recommendation(gap_type):
        return {
            "missing_control": "Define and assign a control for the obligation.",
            "missing_evidence": "Collect authoritative evidence and link it to the obligation.",
            "unverified_evidence": "Have an authorized reviewer verify the recorded evidence.",
            "obligation_status": "Review the obligation status and record the current compliance position.",
            "unremediated_risk": "Create and assign a remediation action with a due date.",
        }.get(gap_type, "Review the compliance gap and assign an accountable owner.")

    def health(self):
        return {"status": "ok", "engine": "compliance-intelligence", "gap_detection": True, "evidence_driven": True, "tenant_isolation": True}
