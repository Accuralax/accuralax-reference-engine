import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .core.agentic_workspace import AgenticWorkspace
from .core.creative_api import CreativeAPI
from .core.enterprise_control_plane import EnterpriseControlPlane
from .core.compliance_engine import ComplianceEngine
from .core.lms_training import LMSTraining
from .core.lms_intelligence import LMSIntelligence
from .core.lms_avatar import LMSAvatar
from .core.lms_analytics import LMSAnalytics
from .core.lms_operations import LMSOperations
from .core.lms_accreditation import LMSAccreditation
from .core.internationalization import Internationalization
from .core.currency_engine import CurrencyEngine
from .core.tax_jurisdiction import TaxJurisdictionEngine
from .core.global_context import GlobalContext
from .core.business_identity import BusinessIdentityEngine
from .core.crm_master import CRMIdentityEngine
from .core.customer_360 import Customer360
from .core.sales_pipeline import SalesPipeline
from .core.opportunity_revenue import OpportunityRevenue
from .core.followup_tasks import FollowUpTasks
from .core.agent_workflow import AgentWorkflow
from .core.agent_planner import AgentPlanner
from .core.human_approval import HumanApprovalGateway
from .core.plan_executor import PlanExecutor
from .core.agent_replanning import AgentReplanningEngine
from .core.agent_autonomous_loop import AgentAutonomousLoop
from .core.agent_event_worker import AgentEventWorker
from .core.agent_scheduler import AgentScheduler
from .core.agent_outcome_analytics import AgentOutcomeAnalytics
from .core.compliance_risk_engine import ComplianceRiskEngine
from .core.compliance_intelligence import ComplianceIntelligence
from .core.compliance_report_agent import ComplianceReportAgent
from .core.compliance_agent_bridge import ComplianceAgentBridge
from .core.compliance_orchestrator import ComplianceOrchestrator
from .core.regulatory_intelligence import RegulatoryIntelligence
from .core.event_bus import EventBus
from .core.enterprise_entity_model import EnterpriseEntityModel
from .core.enterprise_event_fabric import EnterpriseEventFabric
from .core.enterprise_integration_layer import EnterpriseIntegrationLayer
from .core.authorization_policy_engine import AuthorizationPolicyEngine
from .core.audit_lineage import AuditLineage
from .core.data_governance_quality import DataGovernanceQuality
from .core.agent_governance import AgentGovernance
from .core.agent_registry import AgentRegistry
from .core.ai_evaluation import AIEvaluationEngine
from .core.model_gateway import ModelGateway
from .core.enterprise_control_center import EnterpriseControlCenter
from .core.observability import Observability
from .core.usage_billing import UsageBilling
from .core.recovery_manager import RecoveryManager
from .core.cybersecurity_runtime import CybersecurityRuntime
from .core.document_evidence_intelligence import DocumentEvidenceIntelligence
from .core.business_intelligence import BusinessIntelligence
from .core.case_management import CaseManagement
from .core.notifications import NotificationCenter
from .core.search_discovery import SearchDiscovery
from .core.records_management import RecordsManagement
from .core.reporting_export import ReportingExport
from .core.sla_escalation import SLAEscalation
from .core.business_rules import BusinessRules
from .core.workflow_automation import WorkflowAutomation
from .core.event_automation import EventAutomation
from .core.task_assignment import TaskAssignment
from .core.operational_execution import OperationalExecution
from .core.approval_execution_gate import ApprovalExecutionGate
from .core.orchestration_plane import OrchestrationPlane
from .core.enterprise_command_control import EnterpriseCommandControl
from .core.event_command_bridge import EventCommandBridge
from .core.api_security import APISecurity
from .core.saas_entitlements import SaaSEntitlements

compliance = ComplianceEngine()
lms = LMSTraining()
intelligence = LMSIntelligence(lms)
avatar = LMSAvatar(lms, intelligence)
analytics = LMSAnalytics(lms)
operations = LMSOperations(lms)
accreditation = LMSAccreditation(lms)
international = Internationalization()
currency_engine = CurrencyEngine()
tax_engine = TaxJurisdictionEngine()
global_context = GlobalContext(international=international)
identity_engine = BusinessIdentityEngine()
crm_master = CRMIdentityEngine()
customer_360 = Customer360()
sales_pipeline = SalesPipeline()
opportunity_revenue = OpportunityRevenue()
followup_tasks = FollowUpTasks()
agent_workflow = AgentWorkflow(
    pipeline=sales_pipeline,
    followup_tasks=followup_tasks,
    opportunities=opportunity_revenue,
    customer_360=customer_360,
)
agent_planner = AgentPlanner(agent_workflow, lms=lms)
human_approval = HumanApprovalGateway()
audit_lineage = AuditLineage()
approval_execution_gate = ApprovalExecutionGate(audit=audit_lineage)
plan_executor = PlanExecutor(agent_planner, agent_workflow, human_approval, learning=agent_planner.learning, execution_gate=approval_execution_gate)
agent_replanning = AgentReplanningEngine(agent_planner, plan_executor)
agent_autonomous_loop = AgentAutonomousLoop(agent_planner, plan_executor, agent_replanning)
agent_event_worker = AgentEventWorker(agent_autonomous_loop)
agent_scheduler = AgentScheduler(agent_event_worker)
agent_outcome_analytics = AgentOutcomeAnalytics(agent_planner.learning.outcomes)
compliance_risk = ComplianceRiskEngine()
compliance_intelligence = ComplianceIntelligence(compliance_risk)
compliance_report_agent = ComplianceReportAgent(compliance_intelligence)
compliance_agent_bridge = ComplianceAgentBridge(compliance_intelligence, compliance_risk, human_approval)
compliance_events = EventBus()
enterprise_entities = EnterpriseEntityModel()
enterprise_events = EnterpriseEventFabric(enterprise_entities, compliance_events)
regulatory_intelligence = RegulatoryIntelligence()
compliance_orchestrator = ComplianceOrchestrator(compliance_report_agent, compliance_agent_bridge, compliance_events, planner=agent_planner, executor=plan_executor, outcome_analytics=agent_outcome_analytics, regulatory_intelligence=regulatory_intelligence)
agent_planner.compliance_orchestrator = compliance_orchestrator
integration_layer = EnterpriseIntegrationLayer(compliance_events, human_approval)
orchestration_plane = OrchestrationPlane(planner=agent_planner, executor=plan_executor, integration=integration_layer, event_bus=compliance_events)
authorization = AuthorizationPolicyEngine()
data_governance = DataGovernanceQuality()
agent_governance = AgentGovernance()
agent_registry = AgentRegistry()
ai_evaluation = AIEvaluationEngine()
model_gateway = ModelGateway()
plan_executor.governance = agent_governance
observability = Observability()
usage_billing = UsageBilling()
recovery_manager = RecoveryManager()
cybersecurity_runtime = CybersecurityRuntime()
document_evidence = DocumentEvidenceIntelligence()
business_intelligence = BusinessIntelligence()
case_management = CaseManagement()
notifications = NotificationCenter()
search_discovery = SearchDiscovery()
records_management = RecordsManagement()
reporting_export = ReportingExport()
sla_escalation = SLAEscalation()
business_rules = BusinessRules()
workflow_automation = WorkflowAutomation()
event_automation = EventAutomation()
task_assignment = TaskAssignment()
api = CreativeAPI()
workspace = AgenticWorkspace()
control_plane = EnterpriseControlPlane()
enterprise_command_control = EnterpriseCommandControl(
    authorization=authorization,
    governance=agent_governance,
    approval_gate=approval_execution_gate,
    audit=audit_lineage,
    observability=observability,
    usage_billing=usage_billing,
    recovery=recovery_manager,
    orchestration=orchestration_plane,
    control_plane=control_plane,
)
enterprise_control_center = EnterpriseControlCenter(
    command_control=enterprise_command_control,
    agent_registry=agent_registry,
    evaluation=ai_evaluation,
    model_gateway=model_gateway,
    observability=observability,
    usage_billing=usage_billing,
    audit=audit_lineage,
)
operational_execution = OperationalExecution(task_assignment, workflows=workflow_automation, sla=sla_escalation, cases=case_management, notifications=notifications, event_automation=event_automation, command_control=enterprise_command_control)
event_command_bridge = EventCommandBridge(compliance_events, enterprise_command_control, operational_execution)
event_command_bridge.subscribe(["case.created", "task.requested", "workflow.requested", "compliance.action.requested", "security.action.requested", "data.deletion.requested", "external.action.requested"])
api_security = APISecurity()
saas_entitlements = SaaSEntitlements(usage_billing=usage_billing)


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload, content_type="application/json"):
        body = payload.encode() if isinstance(payload, str) else (payload if isinstance(payload, bytes) else json.dumps(payload).encode())
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", api_security.cors_origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Timezone, X-Tenant-ID, X-Workspace-ID, X-User-ID, X-API-Key, X-Feature")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _audit_security_event(self, event_type, status, metadata=None):
        ctx = getattr(self, "auth_context", None)
        tenant = getattr(ctx, "tenant_id", self.headers.get("X-Tenant-ID", "default"))
        workspace = getattr(ctx, "workspace_id", self.headers.get("X-Workspace-ID", "default"))
        actor = getattr(ctx, "subject", self.headers.get("X-User-ID", "system"))
        trace_id = self.headers.get("X-Trace-ID")
        correlation_id = self.headers.get("X-Correlation-ID")
        return audit_lineage.record(tenant, workspace, actor, event_type, source="api", status=status, trace_id=trace_id, correlation_id=correlation_id, metadata=metadata or {"path": self.path})

    def _authenticate_request(self):
        context, reason = api_security.authenticate(dict(self.headers.items()))
        if context is None:
            status = 401 if reason.startswith("invalid_") else 503
            self._send(status, {"error": "unauthorized" if status == 401 else "api_auth_unavailable"})
            return None
        return context

    def _require_api_access(self) -> bool:
        mode = api_security.mode
        if mode == "bearer":
            raw = self.headers.get("Authorization", "")
            supplied = raw[7:].strip() if raw.lower().startswith("bearer ") else None
            allowed, reason = api_security.authorize_bearer(supplied)
            if allowed:
                self.auth_context, _ = api_security.authenticate(dict(self.headers.items()))
                return True
            self._send(401 if reason == "invalid_bearer_token" else 503, {"error": "unauthorized" if reason == "invalid_bearer_token" else "api_auth_unavailable"})
            return False
        supplied = self.headers.get("X-API-Key")
        allowed, reason = api_security.authorize(supplied)
        if allowed:
            self.auth_context, _ = api_security.authenticate(dict(self.headers.items()))
            return True
        self._send(401 if reason == "invalid_api_key" else 503, {"error": "unauthorized" if reason == "invalid_api_key" else "api_auth_unavailable"})
        return False

    def do_OPTIONS(self):
        self._send(204, b"")

    def _require_feature(self, feature: str) -> bool:
        """Enforce SaaS entitlements when production enforcement is enabled."""
        if os.getenv("SAAS_ENFORCEMENT_MODE", "disabled").strip().lower() not in {"enforced", "strict"}:
            return True
        tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
        workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
        decision = saas_entitlements.check(tenant_id, workspace_id, feature)
        if decision["allowed"]:
            return True
        self._send(402, {"error": "feature_not_entitled", "entitlement": decision})
        return False

    def _feature_for_path(self, path: str) -> str | None:
        if path.startswith("/lms/"): return "lms"
        if path.startswith("/crm/") or path.startswith("/sales/"): return "crm"
        if path.startswith(("/operational-execution/", "/tasks/", "/cases/", "/sla/", "/notifications/", "/workflow/", "/event-automation/")): return "operations"
        if path.startswith("/cybersecurity/") or path.startswith("/security/"): return "security"
        if path.startswith(("/bi/", "/analytics/", "/business-intelligence/")): return "analytics"
        if path.startswith(("/automation/", "/workflow-automation/")): return "automation"
        if path.startswith("/agent-registry/") or path.startswith("/skill-registry/"): return "custom_agents"
        if path.startswith("/api/"): return "api"
        if path.startswith("/knowledge/"): return "knowledge"
        if path.startswith("/compliance/"): return "compliance"
        if path.startswith("/runtime/"): return "runtime"
        return None

    def do_GET(self):
        feature = self._feature_for_path(self.path)
        if feature and self.path not in {"/cybersecurity/health", "/control-center/health"} and not self._require_feature(feature):
            return
        if self.path == "/health":
            return self._send(200, {"status":"ok", "service":"unified-api", "api_security":api_security.health()})
        if self.path == "/ready":
            auth=api_security.health()
            status=200 if auth["status"] == "ok" else 503
            return self._send(status, {"status":"ready" if status == 200 else "not_ready", "api_security":auth})
        if self.path == "/cybersecurity/health":
            return self._send(200, {"status":"ok", "runtime":cybersecurity_runtime.snapshot(), "api_security":api_security.health()})
        if self.path == "/control-center/health":
            return self._send(200, enterprise_control_center.health())
        if self.path == "/saas/health":
            return self._send(200, saas_entitlements.health())
        if not self._require_api_access():
            return
        if self.path == "/i18n/health":
            return self._send(200, international.health())
        if self.path == "/finance/currency/health":
            return self._send(200, currency_engine.health())
        if self.path == "/finance/currency":
            return self._send(200, currency_engine.metadata())
        if self.path == "/tax/health":
            return self._send(200, tax_engine.health())
        if self.path == "/tax/jurisdictions":
            return self._send(200, tax_engine.jurisdictions())
        if self.path == "/i18n/context":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            user_id = self.headers.get("X-User-ID")
            return self._send(200, global_context.resolve(tenant_id, workspace_id, user_id, dict(self.headers)))
        if self.path == "/global/health":
            return self._send(200, global_context.health())
        if self.path == "/identity/health":
            return self._send(200, identity_engine.health())
        if self.path == "/identity/address-schema":
            country = self.headers.get("X-Country", "ZA")
            return self._send(200, identity_engine.address_schema(country))
        if self.path == "/identity/organisations":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, identity_engine.list_identities(tenant_id, workspace_id))
        if self.path == "/crm/master/health":
            return self._send(200, crm_master.health())
        if self.path == "/crm/360/health":
            return self._send(200, customer_360.health())
        if self.path == "/sales/pipeline/health":
            return self._send(200, sales_pipeline.health())
        if self.path == "/sales/pipeline":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, sales_pipeline.pipeline(tenant_id, workspace_id))
        if self.path == "/sales/opportunities/health":
            return self._send(200, opportunity_revenue.health())
        if self.path == "/sales/opportunities/revenue":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, opportunity_revenue.revenue(tenant_id, workspace_id, self.headers.get("X-Currency")))
        if self.path == "/crm/master/clients":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, crm_master.search(tenant_id, workspace_id))
        if self.path == "/global/preferences":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            user_id = self.headers.get("X-User-ID")
            return self._send(200, global_context.resolve(tenant_id, workspace_id, user_id, dict(self.headers)))
        if self.path == "/health":
            return self._send(200, api.health())
        if self.path == "/runtime/history":
            return self._send(200, {"executions": workspace.state.recent_executions()})
        if self.path.startswith("/runtime/audit/"):
            ref = self.path.split("/", 3)[3]
            return self._send(200, {"reference_id": ref, "events": workspace.state.audit(ref)})
        if self.path == "/runtime/state/health":
            return self._send(200, workspace.state.health())
        if self.path == "/knowledge/health":
            return self._send(200, workspace.knowledge.rag.health())
        if self.path == "/compliance/health":
            return self._send(200, {"risk": compliance_risk.health(), "intelligence": compliance_intelligence.health(), "generated_content_requires_review": True})
        if self.path == "/regulatory/health":
            return self._send(200, regulatory_intelligence.health())
        if self.path == "/regulatory/snapshot":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, regulatory_intelligence.snapshot(tenant_id, workspace_id))
        if self.path == "/regulatory/impact":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            regulation_id = str(self.headers.get("X-Regulation-ID", ""))
            return self._send(200, regulatory_intelligence.impact_assessment(tenant_id, workspace_id, regulation_id, {}))
        if self.path == "/compliance/summary":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, compliance_intelligence.summary(tenant_id, workspace_id))
        if self.path == "/compliance/gaps":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, {"gaps": compliance_intelligence.gaps(tenant_id, workspace_id)})
        if self.path == "/compliance/recommendations":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, {"recommendations": compliance_intelligence.recommendations(tenant_id, workspace_id)})
        if self.path == "/compliance/matrix":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, compliance_risk.matrix_v2(tenant_id, workspace_id))
        if self.path == "/compliance/report/health":
            return self._send(200, compliance_report_agent.health())
        if self.path == "/compliance/orchestrator/health":
            return self._send(200, compliance_orchestrator.health())
        if self.path == "/cybersecurity/health":
            return self._send(200, {"status":"ok", "runtime": cybersecurity_runtime.snapshot()})
        if self.path == "/cybersecurity/snapshot":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, {"tenant_id":tenant_id,"workspace_id":workspace_id,"runtime":cybersecurity_runtime.snapshot(),"authorization":authorization.health(),"agent_governance":agent_governance.health(),"data_governance":data_governance.health(),"audit":audit_lineage.health(),"observability":observability.health(),"recovery":recovery_manager.health()})
        if self.path == "/authz/health":
            return self._send(200, authorization.health())
        if self.path == "/audit/health":
            return self._send(200, audit_lineage.health())
        if self.path == "/data-governance/health":
            return self._send(200, data_governance.health())
        if self.path == "/agent-governance/health":
            return self._send(200, agent_governance.health())
        if self.path == "/agent-registry/health":
            return self._send(200, agent_registry.health())
        if self.path == "/agent-registry/list":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, {"agents": agent_registry.list_agents(tenant_id, workspace_id)})
        if self.path == "/skill-registry/list":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, {"skills": agent_registry.list_skills(tenant_id, workspace_id)})
        if self.path == "/observability/health":
            return self._send(200, observability.health())
        if self.path == "/usage-billing/health":
            return self._send(200, usage_billing.health())
        if self.path == "/saas/subscription":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, saas_entitlements.subscription(tenant_id, workspace_id))
        if self.path == "/saas/entitlement":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            feature = self.headers.get("X-Feature", "runtime")
            return self._send(200, saas_entitlements.check(tenant_id, workspace_id, feature))
        if self.path == "/recovery/health":
            return self._send(200, recovery_manager.health())
        if self.path == "/documents-evidence/health":
            return self._send(200, document_evidence.health())
        if self.path == "/business-intelligence/health":
            return self._send(200, business_intelligence.health())
        if self.path == "/cases/health":
            return self._send(200, case_management.health())
        if self.path == "/notifications/health":
            return self._send(200, notifications.health())
        if self.path == "/search/health":
            return self._send(200, search_discovery.health())
        if self.path == "/records/health":
            return self._send(200, records_management.health())
        if self.path == "/reports/health":
            return self._send(200, reporting_export.health())
        if self.path == "/sla/health":
            return self._send(200, sla_escalation.health())
        if self.path == "/rules/health":
            return self._send(200, business_rules.health())
        if self.path == "/workflows/health":
            return self._send(200, workflow_automation.health())
        if self.path == "/orchestration/health":
            return self._send(200, orchestration_plane.health())
        if self.path == "/enterprise-control/health":
            return self._send(200, enterprise_command_control.health())
        if self.path == "/control-center/health":
            return self._send(200, enterprise_control_center.health())
        if self.path == "/control-center/snapshot":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, enterprise_control_center.snapshot(tenant_id, workspace_id))
        if self.path == "/approval-gate/health":
            return self._send(200, approval_execution_gate.health())
        if self.path == "/approval-gate/history":
            tenant_id=str(self.headers.get("X-Tenant-ID","default")); workspace_id=str(self.headers.get("X-Workspace-ID","default"))
            return self._send(200, approval_execution_gate.history(tenant_id,workspace_id))
        if self.path == "/operational-execution/health":
            return self._send(200, operational_execution.health())
        if self.path == "/operational-execution/history":
            tenant_id=str(self.headers.get("X-Tenant-ID","default")); workspace_id=str(self.headers.get("X-Workspace-ID","default"))
            return self._send(200, operational_execution.history(tenant_id,workspace_id))
        if self.path == "/tasks/health":
            return self._send(200, task_assignment.health())
        if self.path == "/tasks/history":
            tenant_id=str(self.headers.get("X-Tenant-ID","default")); workspace_id=str(self.headers.get("X-Workspace-ID","default"))
            return self._send(200, task_assignment.history(tenant_id,workspace_id))
        if self.path == "/event-automation/health":
            return self._send(200, event_automation.health())
        if self.path == "/event-automation/history":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default")); workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, event_automation.history(tenant_id, workspace_id))
        if self.path == "/workflows/history":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default")); workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, workflow_automation.history(tenant_id, workspace_id))
        if self.path == "/rules/history":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default")); workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, business_rules.history(tenant_id, workspace_id))
        if self.path == "/sla/history":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default")); workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, sla_escalation.history(tenant_id, workspace_id, self.headers.get("X-SLA-Item-ID")))
        if self.path == "/notifications/history":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, notifications.history(tenant_id, workspace_id, self.headers.get("X-Recipient")))
        if self.path == "/cases/history":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, case_management.history(tenant_id, workspace_id, self.headers.get("X-Case-ID", "")))
        if self.path == "/business-intelligence/snapshot":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, business_intelligence.snapshot(tenant_id, workspace_id, self.headers.get("X-KPI-ID")))
        if self.path == "/data-governance/snapshot":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, data_governance.snapshot(tenant_id, workspace_id))
        if self.path == "/observability/snapshot":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, observability.snapshot(tenant_id, workspace_id))
        if self.path == "/recovery/history":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, {"runs": recovery_manager.history(tenant_id, workspace_id)})
        if self.path == "/audit/history":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, {"events": audit_lineage.history(tenant_id, workspace_id)})
        if self.path == "/integration/health":
            return self._send(200, integration_layer.health())
        if self.path == "/integration/connectors":
            return self._send(200, {"connectors": integration_layer.connectors_list()})
        if self.path == "/integration/jobs":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, {"jobs": integration_layer.jobs(tenant_id, workspace_id)})
        if self.path == "/enterprise/events/health":
            return self._send(200, {"entities": enterprise_entities.health(), "events": enterprise_events.events.health(), "fabric": enterprise_events.health()})
        if self.path == "/enterprise/events/history":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, {"events": enterprise_events.history(tenant_id, workspace_id)})
        if self.path == "/compliance/orchestrator/recent":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, {"runs": compliance_orchestrator.recent(tenant_id, workspace_id)})
        if self.path == "/lms/health":
            return self._send(200, lms.health())
        if self.path == "/lms/accreditation/health":
            return self._send(200, accreditation.health())
        if self.path == "/lms/dashboard":
            tenant_id = str(self.headers.get("X-Tenant-ID", "default"))
            workspace_id = str(self.headers.get("X-Workspace-ID", "default"))
            return self._send(200, lms.dashboard(tenant_id, workspace_id))
        if self.path == "/runtime/capabilities":
            return self._send(200, {
                "capabilities": control_plane.list_capabilities(),
                "health": control_plane.health(),
            })
        self._send(404, {"error": "not_found"})

    def _validate_request_scope(self, data: dict) -> dict | None:
        """Reject request bodies that conflict with authenticated scope headers."""
        for field, header in (("tenant_id", "X-Tenant-ID"), ("workspace_id", "X-Workspace-ID")):
            supplied = self.headers.get(header)
            body_value = data.get(field)
            if supplied and body_value is not None and str(body_value) != str(supplied):
                return {"error": "scope_mismatch", "field": field}
        return None
    def do_POST(self):
        if not self._require_api_access():
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length) or b"{}")
            scope_error = self._validate_request_scope(data)
            if scope_error is not None:
                return self._send(403, scope_error)
            feature = self._feature_for_path(self.path)
            if feature and self.path not in {"/saas/subscription", "/saas/override"} and not self._require_feature(feature):
                return
            if self.path == "/i18n/context":
                return self._send(200, international.resolve(
                    user=data.get("user_profile", {}), organisation=data.get("organisation_profile", {}), headers=dict(self.headers)))
            if self.path == "/agent-registry/register":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_registry.register_agent(
                    tenant_id, workspace_id, data["agent_id"], data.get("name", data["agent_id"]),
                    role=data.get("role", "specialist"), version=data.get("version", "1.0.0"),
                    status=data.get("status", "draft"), owner_id=data.get("owner_id", self.headers.get("X-User-ID", "system")),
                    purpose=data.get("purpose", ""), model_policy=data.get("model_policy", {}),
                    knowledge_scopes=data.get("knowledge_scopes", []), capabilities=data.get("capabilities", []),
                    allowed_tools=data.get("allowed_tools", []), allowed_skills=data.get("allowed_skills", []),
                    governance_policy=data.get("governance_policy", {})))
            if self.path == "/agent-registry/status":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_registry.set_status(tenant_id, workspace_id, data["agent_id"], data["status"]))
            if self.path == "/agent-registry/health":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_registry.record_health(tenant_id, workspace_id, data["agent_id"], data["state"], details=data.get("details", {})))
            if self.path == "/agent-registry/resolve":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_registry.resolve(tenant_id, workspace_id, data["agent_id"], required_skill=data.get("required_skill"), required_tool=data.get("required_tool")))
            if self.path == "/skill-registry/publish":
                return self._send(200, agent_registry.publish_skill(str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))), str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default"))), data["skill_id"], data["version"], evaluation_id=data.get("evaluation_id"), approved_by=data.get("approved_by", self.headers.get("X-User-ID"))))
            if self.path == "/skill-registry/deploy":
                return self._send(200, agent_registry.deploy_skill(str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))), str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default"))), data["skill_id"], data["version"], environment=data.get("environment", "production")))
            if self.path == "/skill-registry/retire":
                return self._send(200, agent_registry.retire_skill(str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))), str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default"))), data["skill_id"], data["version"]))
            if self.path == "/skill-registry/register":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_registry.register_skill(
                    tenant_id, workspace_id, data["skill_id"], data.get("name", data["skill_id"]),
                    version=data.get("version", "1.0.0"), status=data.get("status", "active"),
                    owner_id=data.get("owner_id", self.headers.get("X-User-ID", "system")),
                    description=data.get("description", ""), dependencies=data.get("dependencies", []),
                    permissions=data.get("permissions", []), manifest=data.get("manifest", {})))
            # Privileged mutations must be authorized by the authenticated principal.
            privileged_actions = {
                "/authz/membership": "manage_members",
                "/authz/policy": "manage_policies",
                "/agent-registry/status": "manage_agents",
                "/skill-registry/publish": "manage_skills",
                "/skill-registry/deploy": "manage_skills",
                "/skill-registry/retire": "manage_skills",
                "/approval-gate/approve": "approve",
            }
            action = privileged_actions.get(self.path)
            if action:
                ctx = getattr(self, "auth_context", None)
                if ctx is not None and ctx.method != "local":
                    decision = authorization.authorize(ctx.tenant_id, ctx.workspace_id, ctx.subject, action)
                    if not decision["allowed"]:
                        self._audit_security_event("authorization.denied", "denied", {"path": self.path, "action": action, "reason": decision.get("reason")})
                        return self._send(403, {"error": "access_denied", "authorization": decision})
                    self._audit_security_event("authorization.allowed", "authorized", {"path": self.path, "action": action})

            if self.path == "/authz/membership":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, authorization.set_membership(tenant_id, workspace_id, str(data["principal_id"]), data["role"]))
            if self.path == "/authz/policy":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, authorization.add_policy(tenant_id, workspace_id, data["action"], data.get("role"), bool(data.get("allow", True)), bool(data.get("approval", False))))
            if self.path == "/authz/check":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                principal_id = getattr(getattr(self, "auth_context", None), "subject", str(data["principal_id"]))
                return self._send(200, authorization.authorize(tenant_id, workspace_id, principal_id, data["action"], bool(data.get("approved", False))))
            if self.path == "/observability/metric":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, observability.metric(tenant_id, workspace_id, data["name"], data["value"], data.get("labels", {})))
            if self.path == "/observability/log":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, observability.log(tenant_id, workspace_id, data.get("level", "INFO"), data["message"], data.get("trace_id"), data.get("correlation_id"), data.get("metadata", {})))
            if self.path == "/observability/trace":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, observability.trace(tenant_id, workspace_id, data["trace_id"], data["span"], data.get("status", "completed"), data.get("duration_ms", 0), data.get("metadata", {})))
            if self.path == "/enterprise-control/request":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                actor_id = str(data.get("actor_id", self.headers.get("X-User-ID", "system")))
                return self._send(200, enterprise_command_control.request(
                    tenant_id, workspace_id, actor_id, str(data["action"]),
                    risk=str(data.get("risk", "read")), steps=int(data.get("steps", 0)),
                    cost=float(data.get("cost", 0)), tool=data.get("tool"),
                    high_risk=bool(data.get("high_risk", False)),
                    destructive=bool(data.get("destructive", False)),
                    external_side_effect=bool(data.get("external_side_effect", False)),
                    correlation_id=data.get("correlation_id"), trace_id=data.get("trace_id")))
            if self.path == "/approval-gate/request":
                tenant_id=str(data.get("tenant_id",self.headers.get("X-Tenant-ID","default"))); workspace_id=str(data.get("workspace_id",self.headers.get("X-Workspace-ID","default")))
                return self._send(200,approval_execution_gate.request(tenant_id,workspace_id,data["run_id"],data["action"],data.get("risk","normal"),data.get("actor_id",self.headers.get("X-User-ID","system")),data.get("requires_approval"),data.get("trace_id",self.headers.get("X-Trace-ID")),data.get("correlation_id",self.headers.get("X-Correlation-ID"))))
            if self.path == "/approval-gate/approve":
                tenant_id=str(data.get("tenant_id",self.headers.get("X-Tenant-ID","default"))); workspace_id=str(data.get("workspace_id",self.headers.get("X-Workspace-ID","default")))
                return self._send(200,approval_execution_gate.approve(tenant_id,workspace_id,data["decision_id"],data.get("approved_by",self.headers.get("X-User-ID","system")),data.get("approved",True),data.get("reason",""),data.get("trace_id",self.headers.get("X-Trace-ID")),data.get("correlation_id",self.headers.get("X-Correlation-ID"))))
            if self.path == "/approval-gate/check":
                tenant_id=str(data.get("tenant_id",self.headers.get("X-Tenant-ID","default"))); workspace_id=str(data.get("workspace_id",self.headers.get("X-Workspace-ID","default")))
                return self._send(200,approval_execution_gate.can_execute(tenant_id,workspace_id,data["run_id"],data["action"],data.get("actor_id",self.headers.get("X-User-ID","system")),data.get("trace_id",self.headers.get("X-Trace-ID")),data.get("correlation_id",self.headers.get("X-Correlation-ID"))))
            if self.path == "/operational-execution/process":
                tenant_id=str(data.get("tenant_id",self.headers.get("X-Tenant-ID","default"))); workspace_id=str(data.get("workspace_id",self.headers.get("X-Workspace-ID","default")))
                return self._send(200,operational_execution.execute_event(tenant_id,workspace_id,data["event_id"],data["event_type"],data.get("payload",{}),data.get("actor_id",self.headers.get("X-User-ID","system")),data.get("auto_execute",False)))
            if self.path == "/tasks/create":
                tenant_id=str(data.get("tenant_id",self.headers.get("X-Tenant-ID","default"))); workspace_id=str(data.get("workspace_id",self.headers.get("X-Workspace-ID","default")))
                return self._send(200,task_assignment.create(tenant_id,workspace_id,data["title"],data.get("created_by",self.headers.get("X-User-ID","system")),data.get("description",""),data.get("priority","normal"),data.get("assignee_id"),data.get("due_at"),data.get("reference_type"),data.get("reference_id"),data.get("metadata",{})))
            if self.path == "/tasks/assign":
                tenant_id=str(data.get("tenant_id",self.headers.get("X-Tenant-ID","default"))); workspace_id=str(data.get("workspace_id",self.headers.get("X-Workspace-ID","default")))
                return self._send(200,task_assignment.assign(tenant_id,workspace_id,data["task_id"],data["assignee_id"],data.get("actor_id",self.headers.get("X-User-ID","system"))))
            if self.path == "/tasks/transition":
                tenant_id=str(data.get("tenant_id",self.headers.get("X-Tenant-ID","default"))); workspace_id=str(data.get("workspace_id",self.headers.get("X-Workspace-ID","default")))
                return self._send(200,task_assignment.transition(tenant_id,workspace_id,data["task_id"],data["status"],data.get("actor_id",self.headers.get("X-User-ID","system"))))
            if self.path == "/tasks/list":
                tenant_id=str(data.get("tenant_id",self.headers.get("X-Tenant-ID","default"))); workspace_id=str(data.get("workspace_id",self.headers.get("X-Workspace-ID","default")))
                return self._send(200,task_assignment.list(tenant_id,workspace_id,data.get("status"),data.get("assignee_id"),data.get("limit",100)))
            if self.path == "/event-automation/route":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, event_automation.define_route(tenant_id, workspace_id, data["event_type"], data["name"], data["actions"]))
            if self.path == "/event-automation/dispatch":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, event_automation.dispatch(tenant_id, workspace_id, data["event_id"], data["event_type"], data.get("payload", {})))
            if self.path == "/workflows/define":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, workflow_automation.define(tenant_id, workspace_id, data["name"], data["trigger_type"], data["steps"]))
            if self.path == "/workflows/start":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, workflow_automation.start(tenant_id, workspace_id, data["workflow_id"], data.get("context", {})))
            if self.path == "/workflows/execute":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, workflow_automation.execute(tenant_id, workspace_id, data["run_id"], approved=data.get("approved", False)))
            if self.path == "/rules/define":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, business_rules.define(tenant_id, workspace_id, data["name"], data["event_type"], data["condition"], data.get("actions", []), data.get("priority", 100)))
            if self.path == "/rules/evaluate":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, business_rules.evaluate(tenant_id, workspace_id, data["event_type"], data.get("context", {})))
            if self.path == "/sla/policy":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))); workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, sla_escalation.define_policy(tenant_id, workspace_id, data["name"], data["target_type"], data["target_hours"], data.get("escalation_hours", 0), data.get("metadata", {})))
            if self.path == "/sla/start":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))); workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, sla_escalation.start(tenant_id, workspace_id, data["policy_id"], data["reference_type"], data["reference_id"], data.get("owner_id", "")))
            if self.path == "/sla/evaluate":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))); workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, sla_escalation.evaluate(tenant_id, workspace_id, data["item_id"]))
            if self.path == "/sla/resolve":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))); workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, sla_escalation.resolve(tenant_id, workspace_id, data["item_id"], data.get("met", True), data.get("actor_id", "system")))
            if self.path == "/reports/define":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))); workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, reporting_export.define(tenant_id, workspace_id, data["name"], data.get("report_type", "operational"), data.get("definition", {})))
            if self.path == "/reports/generate":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))); workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, reporting_export.generate(tenant_id, workspace_id, data["report_id"], data.get("data", []), data.get("format", "json")))
            if self.path == "/records/create":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, records_management.create_record(tenant_id, workspace_id, data["name"], data.get("record_type", "document"), data.get("classification", "internal"), data.get("retention_days", 365), data.get("metadata", {})))
            if self.path == "/records/version":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, records_management.add_version(tenant_id, workspace_id, data["record_id"], data["content"], data.get("created_by", "system"), data.get("metadata", {})))
            if self.path == "/records/classify":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, records_management.classify(tenant_id, workspace_id, data["record_id"], data["classification"]))
            if self.path == "/records/transition":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, records_management.transition(tenant_id, workspace_id, data["record_id"], data["status"]))
            if self.path == "/records/link":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, records_management.link(tenant_id, workspace_id, data["record_id"], data["target_type"], data["target_id"]))
            if self.path == "/search/index":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, search_discovery.index(tenant_id, workspace_id, data["entity_type"], data["entity_id"], data["title"], data.get("content", ""), data.get("visibility", "workspace"), data.get("metadata", {})))
            if self.path == "/search/remove":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, search_discovery.remove(tenant_id, workspace_id, data["doc_id"]))
            if self.path == "/search/query":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, search_discovery.search(tenant_id, workspace_id, data["query"], data.get("principal_id", "system"), data.get("entity_type"), data.get("limit", 20)))
            if self.path == "/notifications/template":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, notifications.create_template(tenant_id, workspace_id, data["name"], data["channel"], data["body"], data.get("subject", "")))
            if self.path == "/notifications/preference":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, notifications.set_preference(tenant_id, workspace_id, data["recipient"], data["channel"], data["enabled"]))
            if self.path == "/notifications/queue":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, notifications.queue(tenant_id, workspace_id, data["recipient"], data["channel"], data.get("subject", ""), data.get("body", ""), data.get("template_id"), data.get("idempotency_key"), data.get("metadata", {})))
            if self.path == "/notifications/send":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, notifications.mark_sending(tenant_id, workspace_id, data["job_id"]))
            if self.path == "/notifications/result":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, notifications.mark_result(tenant_id, workspace_id, data["job_id"], data["success"], data.get("error", "")))
            if self.path == "/cases/create":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, case_management.create_case(tenant_id, workspace_id, data["title"], data.get("case_type", "general"), data.get("priority", "normal"), data.get("created_by", "system"), data.get("assignee", ""), data.get("due_at"), data.get("metadata", {})))
            if self.path == "/cases/transition":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, case_management.transition(tenant_id, workspace_id, data["case_id"], data["state"], data.get("actor_id", "system"), data.get("reason", "")))
            if self.path == "/cases/assign":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, case_management.assign(tenant_id, workspace_id, data["case_id"], data["assignee"], data.get("actor_id", "system")))
            if self.path == "/cases/task":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, case_management.add_task(tenant_id, workspace_id, data["case_id"], data["title"], data.get("assignee", ""), data.get("due_at")))
            if self.path == "/cases/task/update":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, case_management.update_task(tenant_id, workspace_id, data["task_id"], data["state"], data.get("assignee")))
            if self.path == "/business-intelligence/kpi":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, business_intelligence.define_kpi(tenant_id, workspace_id, data["name"], data.get("description", ""), data.get("unit", "count")))
            if self.path == "/business-intelligence/record":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, business_intelligence.record(tenant_id, workspace_id, data["kpi_id"], data["value"], data["period"], data.get("metadata", {})))
            if self.path == "/documents-evidence/register":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, document_evidence.register_document(tenant_id, workspace_id, data["title"], data["document_type"], data["content"], data.get("metadata", {})))
            if self.path == "/documents-evidence/version":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, document_evidence.add_version(tenant_id, workspace_id, data["document_id"], data["content"], data.get("metadata", {})))
            if self.path == "/documents-evidence/link":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, document_evidence.link_evidence(tenant_id, workspace_id, data["document_id"], data["source"], data["content_hash"], bool(data.get("verified", False)), str(data.get("state", "unverified")), data.get("metadata", {})))
            if self.path == "/documents-evidence/verify":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, document_evidence.verify(tenant_id, workspace_id, data.get("query", ""), data.get("evidence", [])))
            if self.path == "/saas/subscription":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, saas_entitlements.set_subscription(tenant_id, workspace_id, data.get("plan", "free"), data.get("status", "active"), data.get("trial_ends_at")))
            if self.path == "/saas/override":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, saas_entitlements.set_override(tenant_id, workspace_id, data["feature"], bool(data.get("enabled", True))))
            if self.path == "/usage-billing/account":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, usage_billing.account(tenant_id, workspace_id, data.get("plan", "free")))
            if self.path == "/usage-billing/record":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, usage_billing.record(tenant_id, workspace_id, data["metric"], data["units"], data.get("reference_id")))
            if self.path == "/usage-billing/invoice-preview":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, usage_billing.invoice_preview(tenant_id, workspace_id))
            if self.path == "/recovery/checkpoint":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, recovery_manager.checkpoint(tenant_id, workspace_id, data["label"], data.get("state", {})))
            if self.path == "/recovery/restore":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, recovery_manager.recover(tenant_id, workspace_id, data["checkpoint_id"], data.get("action", "restore"), bool(data.get("approved", False))))
            if self.path == "/agent-governance/tool":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_governance.set_tool(tenant_id, workspace_id, data["agent_id"], data["tool"], bool(data.get("allowed", True)), bool(data.get("approval_required", False))))
            if self.path == "/agent-governance/check":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_governance.check(tenant_id, workspace_id, data["agent_id"], data["action"], data.get("risk", "read"), data.get("steps", 0), data.get("cost", 0), data.get("tool"), bool(data.get("approved", False))))
            if self.path == "/data-governance/register":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, data_governance.register(tenant_id, workspace_id, data["name"], data.get("owner", "system"), data.get("classification", "internal"), data.get("status", "active")))
            if self.path == "/data-governance/check":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, data_governance.check(tenant_id, workspace_id, data["dataset"], data["check_type"], data["status"], data["score"], data.get("details", {})))
            if self.path == "/data-governance/lineage":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, data_governance.add_lineage(tenant_id, workspace_id, data["source_dataset"], data["target_dataset"], data.get("transformation", "")))
            if self.path == "/audit/record":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, audit_lineage.record(tenant_id, workspace_id, str(data.get("actor_id", self.headers.get("X-User-ID", "system"))), data["event_type"], data.get("source", "api"), data.get("status", "completed"), data.get("entity_type"), data.get("entity_id"), data.get("reference_id"), data.get("trace_id"), data.get("correlation_id"), data.get("metadata", {})))
            if self.path == "/integration/dispatch":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                result = integration_layer.dispatch(tenant_id, workspace_id, data["connector"], data["action"], data.get("payload", {}), str(data.get("actor_id", self.headers.get("X-User-ID", "system"))), data.get("idempotency_key"), data.get("trace_id"), data.get("correlation_id"), bool(data.get("approval_required", False)), data.get("approval_id"))
                return self._send(200, result)
            if self.path == "/event-command-bridge/health":
                return self._send(200, event_command_bridge.health())
            if self.path == "/event-command-bridge/history":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, {"dispatches": event_command_bridge.history(tenant_id, workspace_id, data.get("limit", 100))})
            if self.path == "/event-command-bridge/dispatch":
                return self._send(200, event_command_bridge.handle(type("BridgeEvent", (), {"event_id": str(data["event_id"]), "tenant_id": str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))), "workspace_id": str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default"))), "actor_id": str(data.get("actor_id", self.headers.get("X-User-ID", "system"))), "event_type": str(data["event_type"]), "payload": data.get("payload", {}), "trace_id": data.get("trace_id") or "api-bridge"})()))
            if self.path == "/event-command-bridge/approve":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, event_command_bridge.approve_and_resume(
                    tenant_id, workspace_id, str(data["command_id"]),
                    str(data.get("approved_by", self.headers.get("X-User-ID", "system"))),
                    bool(data.get("approved", True)), str(data.get("reason", ""))))
            if self.path == "/enterprise/events/publish":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                result = enterprise_events.publish_entity_event(
                    tenant_id, workspace_id, str(data.get("actor_id", self.headers.get("X-User-ID", "system"))),
                    str(data["entity_type"]), data.get("payload", {}), str(data["event_type"]),
                    str(data.get("reference_id", "")), data.get("idempotency_key"), data.get("trace_id"))
                return self._send(200, {"status": result["status"], "entity": result["entity"], "event": result["event"].__dict__})
            if self.path == "/compliance/report/generate":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                report = compliance_report_agent.generate(tenant_id, workspace_id, data.get("report_type", "compliance_status"), data.get("generated_by", "agent"))
                compliance_events.publish("compliance.report.generated", tenant_id, workspace_id, str(data.get("generated_by", "agent")), "report", report["report_id"], report["report_id"], {"report_type": report["report_type"], "status": "draft"}, idempotency_key=f"report:{report['report_id']}")
                return self._send(200, report)
            if self.path == "/compliance/report/review":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                report = compliance_report_agent.review(tenant_id, workspace_id, data["report_id"], data["reviewer"], data.get("approved", False))
                compliance_events.publish("compliance.report.reviewed", tenant_id, workspace_id, str(data["reviewer"]), "report", data["report_id"], data["report_id"], {"status": report["status"]}, idempotency_key=f"report-review:{data['report_id']}:{report['status']}")
                return self._send(200, report)
            if self.path == "/compliance/report/get":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                report = compliance_report_agent.get(tenant_id, workspace_id, data["report_id"])
                return self._send(200, report or {"error": "report_not_found"})
            if self.path == "/compliance/report/recent":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, {"reports": compliance_report_agent.recent(tenant_id, workspace_id, data.get("limit", 10))})
            if self.path == "/identity/address/validate":
                return self._send(200, identity_engine.validate_address(data["country"], data.get("address", {})))
            if self.path == "/identity/phone/validate":
                return self._send(200, identity_engine.validate_phone(data["country"], data.get("phone", "")))
            if self.path == "/identity/organisations":
                return self._send(200, identity_engine.create_identity(
                    str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))),
                    str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default"))),
                    data["legal_name"], data["country"], data["legal_address"],
                    data.get("trading_name", ""), data.get("registration_number", ""),
                    data.get("tax_identifier", ""), data.get("phone", ""),
                    data.get("email", ""), data.get("website", ""),
                    str(data.get("changed_by", "system"))))
            if self.path == "/identity/organisations/get":
                return self._send(200, identity_engine.get_identity(
                    str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))),
                    str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default"))), data["identity_id"]))
            if self.path == "/crm/master/clients":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, crm_master.create_client(
                    tenant_id, workspace_id, data["entity_type"], data["display_name"],
                    data.get("email", ""), data.get("phone", ""), data.get("country", ""),
                    data.get("identity_id", ""), data.get("external_ref", ""),
                    data.get("registration_number", ""), data.get("tax_identifier", ""),
                    data.get("profile", {}), str(data.get("changed_by", "system"))))
            if self.path == "/crm/master/search":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, {"results": crm_master.search(tenant_id, workspace_id, data.get("query", ""), data.get("entity_type"))})
            if self.path == "/crm/master/client":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, crm_master.get_client(tenant_id, workspace_id, data["client_id"]))
            if self.path == "/crm/master/link-identity":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, crm_master.link_identity(tenant_id, workspace_id, data["client_id"], data["identity_id"], str(data.get("changed_by", "system"))))
            if self.path == "/sales/lead":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                lead = sales_pipeline.create_lead(tenant_id, workspace_id, data["client_id"], data.get("source", "api"), data.get("owner_id"), data.get("score"), data.get("notes", ""))
                customer_360.record_event(tenant_id, workspace_id, data["client_id"], data.get("channel", "api"), "lead_created", "Lead created in sales pipeline", metadata={"lead_id": lead["lead_id"], "source": lead["source"]})
                return self._send(200, lead)
            if self.path == "/sales/lead/stage":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                lead = sales_pipeline.move_stage(tenant_id, workspace_id, data["lead_id"], data["to_stage"], str(data.get("changed_by", "system")), str(data.get("reason", "")))
                customer_360.record_event(tenant_id, workspace_id, lead["client_id"], data.get("channel", "api"), "lead_stage_changed", "Sales pipeline stage changed", metadata={"lead_id": lead["lead_id"], "stage": lead["status"]})
                return self._send(200, lead)
            if self.path == "/sales/lead/owner":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                lead = sales_pipeline.assign_owner(tenant_id, workspace_id, data["lead_id"], data["owner_id"])
                customer_360.record_event(tenant_id, workspace_id, lead["client_id"], data.get("channel", "api"), "lead_owner_assigned", "Sales lead owner assigned", metadata={"lead_id": lead["lead_id"], "owner_id": lead["owner_id"]})
                return self._send(200, lead)
            if self.path == "/sales/lead/history":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, {"history": sales_pipeline.history(tenant_id, workspace_id, data["lead_id"])})
            if self.path == "/sales/opportunity":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                opp = opportunity_revenue.create(tenant_id, workspace_id, data["client_id"], data["name"], data.get("value"), data.get("currency"), data.get("probability", 0), data.get("expected_close_date"), data.get("lead_id"))
                customer_360.record_event(tenant_id, workspace_id, data["client_id"], data.get("channel", "api"), "opportunity_created", "Opportunity created", metadata={"opportunity_id": opp["opportunity_id"], "value": opp["value"], "currency": opp["currency"]})
                return self._send(200, opp)
            if self.path == "/sales/opportunity/stage":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                opp = opportunity_revenue.update_stage(tenant_id, workspace_id, data["opportunity_id"], data["stage"], str(data.get("changed_by", "system")), str(data.get("reason", "")))
                customer_360.record_event(tenant_id, workspace_id, opp["client_id"], data.get("channel", "api"), "opportunity_stage_changed", "Opportunity stage changed", metadata={"opportunity_id": opp["opportunity_id"], "stage": opp["stage"]})
                return self._send(200, opp)
            if self.path == "/sales/opportunity/close":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                opp = opportunity_revenue.close(tenant_id, workspace_id, data["opportunity_id"], data["status"], str(data.get("changed_by", "system")), str(data.get("reason", "")))
                event_type = "opportunity_won" if opp["status"] == "won" else "opportunity_closed"
                customer_360.record_event(tenant_id, workspace_id, opp["client_id"], data.get("channel", "api"), event_type, "Opportunity status changed", metadata={"opportunity_id": opp["opportunity_id"], "status": opp["status"], "value": opp["value"], "currency": opp["currency"]})
                return self._send(200, opp)
            if self.path == "/sales/opportunity/get":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, opportunity_revenue.get(tenant_id, workspace_id, data["opportunity_id"]))
            if self.path == "/sales/opportunity/history":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, {"history": opportunity_revenue.history(tenant_id, workspace_id, data["opportunity_id"])})
            if self.path == "/sales/task":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                task = followup_tasks.create(tenant_id, workspace_id, data["client_id"], data["title"], data.get("due_at"), data.get("owner_id"), data.get("lead_id"), data.get("opportunity_id"), data.get("channel", "internal"), data.get("priority", "normal"), data.get("notes", ""))
                customer_360.record_event(tenant_id, workspace_id, data["client_id"], data.get("channel", "api"), "followup_task_created", "Follow-up task created", metadata={"task_id": task["task_id"]})
                return self._send(200, task)
            if self.path == "/sales/task/status":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                task = followup_tasks.update_status(tenant_id, workspace_id, data["task_id"], data["status"], str(data.get("changed_by", "system")), str(data.get("reason", "")))
                return self._send(200, task)
            if self.path == "/sales/tasks/due":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, {"tasks": followup_tasks.due(tenant_id, workspace_id, data.get("as_of"), data.get("owner_id"))})
            if self.path == "/sales/tasks/overdue":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, {"tasks": followup_tasks.mark_overdue(tenant_id, workspace_id, data.get("as_of"))})
            if self.path == "/sales/task/history":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, {"history": followup_tasks.history(tenant_id, workspace_id, data["task_id"])})
            if self.path == "/sales/tasks/health":
                return self._send(200, followup_tasks.health())
            if self.path == "/sales/agent/decide":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_workflow.decide(tenant_id, workspace_id, data["client_id"], data.get("lead"), data.get("opportunity"), data.get("consent_granted", False), data.get("open_tasks", 0)))
            if self.path == "/sales/agent/execute":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_workflow.execute(
                    tenant_id, workspace_id, data["decision_id"],
                    owner_id=data.get("owner_id"), task=data.get("task"),
                    opportunity=data.get("opportunity"), changed_by=str(data.get("changed_by", "agent"))))
            if self.path == "/sales/agent/history":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, {"history": agent_workflow.history(tenant_id, workspace_id, data["client_id"])})
            if self.path == "/sales/agent/approval/request":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, plan_executor.request_approval(
                    tenant_id, workspace_id, data["plan_id"], int(data["position"]),
                    str(data.get("requested_by", self.headers.get("X-User-ID", "system")))))
            if self.path == "/sales/agent/approval/approve":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, human_approval.approve(
                    tenant_id, workspace_id, data["approval_id"],
                    str(data.get("actor_id", self.headers.get("X-User-ID", "system"))), data.get("reason", "")))
            if self.path == "/sales/agent/approval/reject":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, human_approval.reject(
                    tenant_id, workspace_id, data["approval_id"],
                    str(data.get("actor_id", self.headers.get("X-User-ID", "system"))), data.get("reason", "")))
            if self.path == "/sales/agent/replan":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_replanning.propose(
                    tenant_id, workspace_id, data["source_plan_id"],
                    lead=data.get("lead"), opportunity=data.get("opportunity"),
                    consent_granted=bool(data.get("consent_granted", False)),
                    open_tasks=int(data.get("open_tasks", 0))))
            if self.path == "/sales/agent/replan/get":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_replanning.get(tenant_id, workspace_id, data["replan_id"]))
            if self.path == "/sales/agent/replanning/health":
                return self._send(200, agent_replanning.health())
            if self.path == "/sales/agent/autonomous-loop/run":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_autonomous_loop.run(tenant_id, workspace_id, data.get("limit")))
            if self.path == "/sales/agent/autonomous-loop/health":
                return self._send(200, agent_autonomous_loop.health())
            if self.path == "/sales/agent/event-worker/run":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_event_worker.run_once(tenant_id, workspace_id, data.get("limit")))
            if self.path == "/sales/agent/event-worker/state":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_event_worker.state(tenant_id, workspace_id))
            if self.path == "/sales/agent/event-worker/reconcile":
                tenant_id = data.get("tenant_id", self.headers.get("X-Tenant-ID"))
                workspace_id = data.get("workspace_id", self.headers.get("X-Workspace-ID"))
                return self._send(200, {"reconciliation": agent_event_worker.reconcile(tenant_id, workspace_id)})
            if self.path == "/sales/agent/event-worker/health":
                return self._send(200, agent_event_worker.health())
            if self.path == "/sales/agent/scheduler/register":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_scheduler.register(tenant_id, workspace_id, data.get("enabled", True)))
            if self.path == "/sales/agent/scheduler/start":
                return self._send(200, agent_scheduler.start())
            if self.path == "/sales/agent/scheduler/stop":
                return self._send(200, agent_scheduler.stop())
            if self.path == "/sales/agent/scheduler/status":
                return self._send(200, agent_scheduler.status())
            if self.path == "/sales/agent/scheduler/scopes":
                return self._send(200, {"scopes": agent_scheduler.scopes()})
            if self.path == "/sales/agent/scheduler/health":
                return self._send(200, agent_scheduler.health())
            if self.path == "/sales/agent/outcomes":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_planner.learning.outcomes.query(tenant_id, workspace_id, data.get("action"), data.get("context_fingerprint"), data.get("limit", 100)))
            if self.path == "/sales/agent/outcomes/analytics":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_outcome_analytics.analyze(tenant_id, workspace_id, data.get("action"), data.get("context_fingerprint")))
            if self.path == "/sales/agent/outcomes/recommendations":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_outcome_analytics.recommendations(tenant_id, workspace_id, data.get("context_fingerprint")))
            if self.path == "/sales/agent/outcomes/health":
                return self._send(200, agent_outcome_analytics.health())
            if self.path == "/sales/agent/plan/execute":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, plan_executor.execute(
                    tenant_id, workspace_id, data["plan_id"],
                    approver_id=data.get("approver_id"), owner_id=data.get("owner_id"),
                    task=data.get("task"), opportunity=data.get("opportunity"),
                    changed_by=str(data.get("changed_by", "agent"))))
            if self.path == "/sales/agent/approval/health":
                return self._send(200, human_approval.health())
            if self.path == "/sales/agent/executor/health":
                return self._send(200, plan_executor.health())
            if self.path == "/sales/agent/plan":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_planner.plan(tenant_id, workspace_id, data["client_id"], data.get("lead"), data.get("opportunity"), data.get("consent_granted", False), data.get("open_tasks", 0), data.get("trigger", "manual")))
            if self.path == "/sales/agent/plan/get":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_planner.get(tenant_id, workspace_id, data["plan_id"]))
            if self.path == "/sales/agent/planner/health":
                return self._send(200, agent_planner.health())
            if self.path == "/sales/agent/events/process":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, agent_workflow.process_pending_events(tenant_id, workspace_id, data.get("limit", 100)))
            if self.path == "/sales/agent/health":
                return self._send(200, agent_workflow.health())
            if self.path == "/crm/360/relationship":
                return self._send(200, customer_360.add_relationship(
                    str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))),
                    str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default"))),
                    data["client_id"], data["relationship_type"], data["subject"], data.get("metadata", {})))
            if self.path == "/crm/360/event":
                return self._send(200, customer_360.record_event(
                    str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))),
                    str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default"))),
                    data["client_id"], data["channel"], data["event_type"], data.get("summary", ""),
                    data.get("occurred_at"), data.get("metadata", {})))
            if self.path == "/crm/360/consent":
                return self._send(200, customer_360.set_consent(
                    str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))),
                    str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default"))),
                    data["client_id"], data["purpose"], data["granted"], data.get("source", "api")))
            if self.path == "/crm/360/opportunity":
                return self._send(200, customer_360.create_opportunity(
                    str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))),
                    str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default"))),
                    data["client_id"], data["name"], data.get("stage", "new"), data.get("value"), data.get("currency")))
            if self.path == "/crm/360/view":
                return self._send(200, customer_360.customer_360(
                    str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default"))),
                    str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default"))),
                    data["client_id"]))
            if self.path == "/global/preferences":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                scope_type = str(data.get("scope_type", "user"))
                scope_id = str(data.get("scope_id", data.get("user_id", self.headers.get("X-User-ID", "system"))))
                return self._send(200, global_context.set_preferences(
                    tenant_id, workspace_id, scope_type, scope_id,
                    data.get("preferences", {}), str(data.get("changed_by", "system"))))
            if self.path == "/runtime/execute":
                return self._send(200, workspace.run(
                    data.get("request", ""),
                    tenant_id=str(data.get("tenant_id", "default")),
                    workspace_id=str(data.get("workspace_id", "default")),
                    actor_id=str(data.get("actor_id", "system")),
                    channel=str(data.get("channel", "api")),
                    role=str(data.get("role", "agent")),
                    trust=str(data.get("trust", "verified")),
                ))
            if self.path == "/tax/calculate":
                return self._send(200, tax_engine.calculate(data["jurisdiction"], data["taxable_amount"], data.get("tax_type","standard"), data.get("rate"), data.get("source","configured-rule")))
            if self.path == "/finance/currency/convert":
                return self._send(200, currency_engine.convert(data["amount"], data["base_currency"], data["quote_currency"], data["rate"], data["rate_source"]))
            if self.path == "/finance/currency/rate":
                return self._send(200, currency_engine.set_rate(data["base_currency"], data["quote_currency"], data["rate"], data["source"], data.get("observed_at")))
            if self.path == "/knowledge/ingest":
                tenant_id = str(data.get("tenant_id", "default"))
                workspace_id = str(data.get("workspace_id", "default"))
                access = workspace.access.authorize(
                    __import__("src.core.tenant_access", fromlist=["AccessContext"]).AccessContext(
                        tenant_id=tenant_id, workspace_id=workspace_id,
                        actor_id=str(data.get("actor_id", "system")),
                        role=str(data.get("role", "admin")),
                        trust=str(data.get("trust", "verified")),
                    ),
                    "execute_scoped", tenant_id, workspace_id
                )
                if not access["allowed"]:
                    return self._send(403, {"status": "blocked", "reason": "access_denied", "authorization": access})
                return self._send(200, workspace.knowledge.rag.ingest(
                    data.get("content", ""), source=data.get("source", ""),
                    source_type=data.get("source_type", "document"),
                    trust=data.get("knowledge_trust", "unverified"),
                    metadata=data.get("metadata", {}), tenant_id=tenant_id, workspace_id=workspace_id
                ))
            if self.path == "/knowledge/search":
                tenant_id = str(data.get("tenant_id", "default"))
                workspace_id = str(data.get("workspace_id", "default"))
                return self._send(200, {"results": workspace.knowledge.rag.retrieve(
                    data.get("query", ""), minimum_trust=data.get("minimum_trust", "unverified"),
                    tenant_id=tenant_id, workspace_id=workspace_id
                )})
            if self.path == "/lms/learner/profile":
                return self._send(200, intelligence.learner_profile(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["learner_id"]))
            if self.path == "/lms/learner/skill-gaps":
                return self._send(200, intelligence.skill_gaps(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["learner_id"]))
            if self.path == "/lms/learner/performance":
                return self._send(200, intelligence.performance_summary(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["learner_id"]))
            if self.path == "/lms/instructor/dashboard":
                return self._send(200, intelligence.instructor_dashboard(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data.get("instructor_id")))
            if self.path == "/lms/analytics/dashboard":
                return self._send(200, analytics.training_dashboard(str(data.get("tenant_id","default")), str(data.get("workspace_id","default"))))
            if self.path == "/lms/analytics/course":
                return self._send(200, analytics.course_performance(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["course_id"]))
            if self.path == "/lms/analytics/cohort":
                return self._send(200, analytics.cohort_performance(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["cohort_id"]))
            if self.path == "/lms/certification/evidence":
                return self._send(200, analytics.certification_evidence(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["learner_id"], data["course_id"]))
            if self.path == "/lms/operations/health":
                return self._send(200, operations.health())
            if self.path == "/lms/operations/dashboard":
                return self._send(200, operations.operations_dashboard(str(data.get("tenant_id","default")), str(data.get("workspace_id","default"))))
            if self.path == "/lms/operations/dashboard":
                return self._send(200, operations.operations_dashboard(str(data.get("tenant_id","default")), str(data.get("workspace_id","default"))))
            if self.path == "/lms/analytics/health":
                return self._send(200, analytics.health())
            if self.path == "/lms/learning-path":
                return self._send(200, intelligence.recommend_learning_path(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["learner_id"], str(data.get("goal",""))))
            if self.path == "/lms/learning-events":
                return self._send(200, intelligence.record_learning_event(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data.get("learner_id"), str(data.get("event_type","")), str(data.get("entity_type","")), str(data.get("entity_id","")), data.get("payload")))
            if self.path == "/lms/intelligence/health":
                return self._send(200, intelligence.health())
            if self.path == "/lms/avatar/context":
                return self._send(200, avatar.context(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["learner_id"], data.get("course_id")))
            if self.path == "/lms/avatar/start":
                return self._send(200, avatar.start_session(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["learner_id"], data.get("course_id"), str(data.get("mode","tutor"))))
            if self.path == "/lms/avatar/tutor-message":
                return self._send(200, avatar.tutor_message(data["session_id"], str(data.get("message","")), str(data.get("role","learner"))))
            if self.path == "/lms/avatar/health":
                return self._send(200, avatar.health())
            if self.path == "/lms/competencies":
                return self._send(200, lms.create_competency(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), str(data.get("name","")), str(data.get("description","")), str(data.get("level","novice"))))
            if self.path == "/lms/course-competencies":
                return self._send(200, lms.map_competency(data["course_id"], data["competency_id"], str(data.get("target_level","competent"))))
            if self.path == "/lms/course-generator":
                return self._send(200, lms.generate_course_blueprint(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), str(data.get("topic","")), str(data.get("audience","")), str(data.get("level","beginner")), data.get("outcomes",[]), str(data.get("duration","")), data.get("standards")))
            if self.path == "/lms/avatar/sessions":
                return self._send(200, lms.create_avatar_session(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["learner_id"], data.get("course_id"), str(data.get("mode","tutor")), data.get("context")))
            if self.path == "/lms/avatar/messages":
                return self._send(200, lms.append_avatar_message(data["session_id"], str(data.get("role","learner")), str(data.get("message",""))))
            if self.path == "/lms/programmes":
                return self._send(200, lms.create_programme(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), str(data.get("name","")), str(data.get("description",""))))
            if self.path == "/lms/courses":
                return self._send(200, lms.create_course(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), str(data.get("title","")), str(data.get("description","")), data.get("programme_id")))
            if self.path == "/lms/modules":
                return self._send(200, lms.add_module(data["course_id"], data["title"], data.get("description",""), int(data.get("position",1))))
            if self.path == "/lms/lessons":
                return self._send(200, lms.add_lesson(data["module_id"], data["title"], data.get("content",""), int(data.get("position",1)), bool(data.get("ai_generated",False))))
            if self.path == "/lms/learners":
                return self._send(200, lms.create_learner(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), str(data.get("name","")), str(data.get("email","")), str(data.get("external_ref",""))))
            if self.path == "/lms/instructors":
                return self._send(200, lms.create_instructor(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), str(data.get("name","")), str(data.get("email","")), bool(data.get("authorised",False))))
            if self.path == "/lms/cohorts":
                return self._send(200, lms.create_cohort(data["course_id"], data["name"], data.get("start_date"), data.get("end_date"), data.get("capacity")))
            if self.path == "/lms/operations/instructors/assign":
                return self._send(200, lms.assign_instructor(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["cohort_id"], data["instructor_id"], str(data.get("role","lead"))))
            if self.path == "/lms/operations/sessions":
                return self._send(200, lms.schedule_session(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["cohort_id"], data["title"], data["scheduled_start"], data["scheduled_end"], data.get("instructor_id"), str(data.get("mode","classroom")), data.get("location")))
            if self.path == "/lms/operations/sessions/update":
                changes = {k:data[k] for k in ("title","scheduled_start","scheduled_end","instructor_id","mode","location","status") if k in data}
                return self._send(200, lms.update_session(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["session_id"], **changes))
            if self.path == "/lms/operations/session-view":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                user_id = data.get("user_id", self.headers.get("X-User-ID"))
                context = global_context.resolve(tenant_id, workspace_id, user_id, dict(self.headers))
                return self._send(200, lms.session_view(tenant_id, workspace_id, data["session_id"], context["timezone"]))
            if self.path == "/lms/operations/roster":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                user_id = data.get("user_id", self.headers.get("X-User-ID"))
                context = global_context.resolve(tenant_id, workspace_id, user_id, dict(self.headers))
                return self._send(200, lms.cohort_roster(tenant_id, workspace_id, data["cohort_id"], context["timezone"]))
            if self.path == "/lms/operations/assessment-status":
                return self._send(200, lms.set_assessment_status(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["assessment_id"], str(data["status"])))
            if self.path == "/lms/operations/certificate/revoke":
                return self._send(200, lms.revoke_certificate(str(data.get("tenant_id","default")), str(data.get("workspace_id","default")), data["certificate_id"], str(data.get("reason",""))))
            if self.path == "/lms/enrolments":
                return self._send(200, lms.enrol(data["learner_id"], data["course_id"], data.get("cohort_id")))
            if self.path == "/lms/progress":
                return self._send(200, lms.record_progress(data["learner_id"], data["course_id"], data["completion_pct"], data.get("lesson_id"), data.get("competency")))
            if self.path == "/lms/attendance":
                return self._send(200, lms.record_attendance(data["learner_id"], data["cohort_id"], data["session_date"], data["status"], str(data.get("recorded_by","system"))))
            if self.path == "/lms/assessments":
                return self._send(200, lms.create_assessment(data["course_id"], data["title"], data.get("pass_mark",50), data.get("module_id"), bool(data.get("high_impact",False))))
            if self.path == "/lms/questions":
                return self._send(200, lms.add_question(data["assessment_id"], data["prompt"], data.get("options"), data.get("answer"), data.get("points",1)))
            if self.path == "/lms/attempts":
                return self._send(200, lms.submit_attempt(data["assessment_id"], data["learner_id"], data.get("answers",{})))
            if self.path == "/lms/attempts/grade":
                return self._send(200, lms.grade_attempt(data["attempt_id"], data["score"], data["passed"], str(data["graded_by"]), str(data.get("provenance","human_review"))))
            if self.path == "/lms/ai/generate":
                return self._send(200, lms.generate_content(data["course_id"], data["request"], data["output"], str(data.get("model","governed-generator")), data.get("module_id")))
            if self.path == "/lms/ai/review":
                return self._send(200, lms.review_content(data["generation_id"], bool(data.get("approved",False)), str(data["reviewer"])))
            if self.path == "/lms/certificates/issue":
                return self._send(200, lms.issue_certificate(data["learner_id"], data["course_id"], data.get("certificate_no")))
            if self.path == "/lms/courses/publish":
                return self._send(200, lms.publish_course(data["course_id"], str(data["approver"])))
            if self.path == "/lms/accreditation/qualification":
                return self._send(200, accreditation.register_qualification(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),str(data["name"]),str(data.get("code","")),str(data.get("authority","")),str(data.get("nqf_level","")),data.get("credits",0),str(data.get("status","draft")),str(data.get("version","1.0")),data.get("effective_from"),data.get("effective_to")))
            if self.path == "/lms/accreditation/requirement":
                return self._send(200, accreditation.add_requirement(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["qualification_id"],str(data["requirement_type"]),str(data["name"]),data.get("target"),str(data.get("unit","")),bool(data.get("mandatory",True)),str(data.get("evidence_type",""))))
            if self.path == "/lms/accreditation/programme-map":
                return self._send(200, accreditation.map_programme(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["qualification_id"],data["programme_id"],data.get("coverage_pct",0),str(data.get("status","draft"))))
            if self.path == "/lms/accreditation/assessor":
                return self._send(200, accreditation.assign_assessor(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["assessor_id"],data.get("course_id"),data.get("cohort_id"),str(data.get("role","assessor"))))
            if self.path == "/lms/accreditation/submit":
                return self._send(200, accreditation.submit_accreditation(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["qualification_id"],str(data.get("authority","")),str(data.get("reference_no",""))))
            if self.path == "/lms/accreditation/decision":
                return self._send(200, accreditation.decide_accreditation(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["application_id"],str(data["status"]),str(data.get("actor_id","system")),str(data.get("notes",""))))
            if self.path == "/lms/accreditation/portfolio":
                return self._send(200, accreditation.create_portfolio(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["learner_id"],data["qualification_id"]))
            if self.path == "/lms/accreditation/evidence":
                return self._send(200, accreditation.add_evidence(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["portfolio_id"],str(data["evidence_type"]),str(data["title"]),str(data.get("source_ref","")),data.get("requirement_id"),data.get("metadata")))
            if self.path == "/lms/accreditation/evidence/verify":
                return self._send(200, accreditation.verify_evidence(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["evidence_id"],bool(data.get("verified",True)),str(data.get("reviewer_id",data.get("actor_id","system")))))
            if self.path == "/lms/accreditation/moderation":
                return self._send(200, accreditation.moderate_assessment(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data.get("learner_id"),data.get("course_id"),data.get("assessment_id"),data.get("assessor_id"),data.get("moderator_id")))
            if self.path == "/lms/accreditation/moderation/decision":
                return self._send(200, accreditation.decide_moderation(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["moderation_id"],str(data["status"]),str(data.get("moderator_id",data.get("actor_id","system"))),str(data.get("findings",""))))
            if self.path == "/lms/accreditation/portfolio/submit":
                return self._send(200, accreditation.submit_portfolio(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["portfolio_id"]))
            if self.path == "/lms/accreditation/certificate/register":
                return self._send(200, accreditation.register_certificate(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["learner_id"],data["qualification_id"],str(data["certificate_no"]),str(data.get("verification_hash","")),data.get("issued_at")))
            if self.path == "/lms/accreditation/transcript":
                return self._send(200, accreditation.transcript(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["learner_id"],data.get("qualification_id")))
            if self.path == "/lms/accreditation/certificate/verify":
                return self._send(200, accreditation.verify_certificate(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),str(data["certificate_no"])))
            if self.path == "/lms/accreditation/eligibility":
                return self._send(200, accreditation.eligibility(str(data.get("tenant_id","default")),str(data.get("workspace_id","default")),data["learner_id"],data["qualification_id"]))
            if self.path == "/compliance/summary":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, compliance_intelligence.summary(tenant_id, workspace_id))
            if self.path == "/compliance/gaps":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, {"gaps": compliance_intelligence.gaps(tenant_id, workspace_id)})
            if self.path == "/compliance/recommendations":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, {"recommendations": compliance_intelligence.recommendations(tenant_id, workspace_id)})
            if self.path == "/compliance/agent/assess":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, compliance_agent_bridge.assess(tenant_id, workspace_id, str(data.get("agent_id", "default"))))
            if self.path == "/compliance/agent/execute":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, compliance_agent_bridge.execute(tenant_id, workspace_id, data["proposal_id"], str(data.get("actor_id", "default"))))
            if self.path == "/compliance/agent/health":
                return self._send(200, compliance_agent_bridge.health())
            if self.path == "/compliance/orchestrator/assess":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, compliance_orchestrator.assess(
                    tenant_id, workspace_id, str(data.get("requested_by", data.get("agent_id", "system"))),
                    regulation_id=data.get("regulation_id"), organization_profile=data.get("organization_profile") or {}
                ))
            if self.path == "/regulatory/change/process":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, compliance_orchestrator.process_regulatory_change(
                    tenant_id, workspace_id, data["regulation_id"], data["new_version"],
                    organization_profile=data.get("organization_profile") or {},
                    requested_by=str(data.get("requested_by", data.get("actor_id", "system"))),
                    impact=str(data.get("impact", "medium")), checksum=str(data.get("checksum", "")),
                    proposed_obligations=data.get("proposed_obligations")
                ))
            if self.path == "/compliance/orchestrator/get":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                result = compliance_orchestrator.get(tenant_id, workspace_id, data["run_id"])
                return self._send(200, result or {"error": "run_not_found"})
            if self.path == "/compliance/orchestrator/approve":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, compliance_orchestrator.approve_proposal(tenant_id, workspace_id, data["run_id"], data["proposal_id"], bool(data.get("approved", False)), str(data["actor_id"]), str(data.get("reason", ""))))
            if self.path == "/compliance/orchestrator/execute":
                tenant_id = str(data.get("tenant_id", self.headers.get("X-Tenant-ID", "default")))
                workspace_id = str(data.get("workspace_id", self.headers.get("X-Workspace-ID", "default")))
                return self._send(200, compliance_orchestrator.execute(tenant_id, workspace_id, data["run_id"], str(data.get("actor_id", "system"))))
            if self.path == "/compliance/assess":
                controls = data.get("controls", [])
                if not isinstance(controls, list):
                    return self._send(400, {"error": "controls_must_be_list"})
                return self._send(200, compliance.assess(controls))
            if self.path == "/agent/run":
                return self._send(200, workspace.run(data.get("request", "")))
            if self.path == "/creative/assets":
                return self._send(200, api.create(data))
            if self.path.startswith("/creative/assets/") and self.path.endswith("/edit"):
                asset_id = self.path.split("/")[3]
                return self._send(200, api.edit(
                    asset_id, data["operation"], data.get("instruction", "")
                ))
            if self.path.startswith("/creative/assets/") and self.path.endswith("/render"):
                asset_id = self.path.split("/")[3]
                return self._send(200, api.render(asset_id, data.get("theme")), "text/html")
            if self.path.startswith("/creative/assets/") and self.path.endswith("/manifest"):
                asset_id = self.path.split("/")[3]
                return self._send(200, api.manifest(asset_id, data.get("formats", [])))
            self._send(404, {"error": "not_found"})
        except Exception as exc:
            self._send(400, {"error": str(exc)})

    def log_message(self, *_):
        pass


def run(host="127.0.0.1", port=None):
    selected_port = int(port or os.getenv("CREATIVE_API_PORT", "8788"))
    server = ThreadingHTTPServer((host, selected_port), Handler)
    print(f"Unified API listening on http://{host}:{selected_port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run()
