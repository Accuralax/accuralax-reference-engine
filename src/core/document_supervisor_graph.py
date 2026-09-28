from __future__ import annotations
from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END

from .document_classifier import classify_request
from .document_template_engine import DocumentTemplateEngine
from .document_theme_engine import DocumentThemeEngine
from .document_specialists import select_specialist
from .document_editor import DocumentEditor
from .document_quality import DocumentQualityGate
from .document_versions import DocumentVersionStore
from .document_trace import DocumentTrace
from .references import ReferenceGenerator

class DocumentGraphState(TypedDict, total=False):
    request: str
    document_type: str | None
    template_id: str | None
    theme_id: str
    specialist: str | None
    operation: str
    content: str
    version: int
    qa: dict[str, Any]
    status: str
    approval_required: bool
    approved: bool
    credentials_exposed: bool
    history: list[str]
    reference_id: str

class DocumentSupervisorGraph:
    def __init__(self):
        self.templates = DocumentTemplateEngine()
        self.themes = DocumentThemeEngine()
        self.editor = DocumentEditor()
        self.qa = DocumentQualityGate()
        self.versions = DocumentVersionStore()
        self.references = ReferenceGenerator()
        graph = StateGraph(DocumentGraphState)
        graph.add_node("classify", self.classify)
        graph.add_node("select_template", self.select_template)
        graph.add_node("select_theme", self.select_theme)
        graph.add_node("select_specialist", self.select_specialist)
        graph.add_node("edit", self.edit)
        graph.add_node("qa", self.run_qa)
        graph.add_node("approval_gate", self.approval_gate)
        graph.add_edge(START, "classify")
        graph.add_edge("classify", "select_template")
        graph.add_edge("select_template", "select_theme")
        graph.add_edge("select_theme", "select_specialist")
        graph.add_edge("select_specialist", "edit")
        graph.add_edge("edit", "qa")
        graph.add_edge("qa", "approval_gate")
        graph.add_edge("approval_gate", END)
        self.graph = graph.compile()

    def classify(self, state):
        item = classify_request(state["request"])
        return {"document_type": item.document_type, "history": state.get("history", []) + ["classify"]}

    def select_template(self, state):
        template = self.templates.select(state.get("document_type"))
        if not template:
            return {"status": "needs_clarification", "history": state["history"] + ["template_missing"]}
        return {"template_id": template.template_id, "history": state["history"] + ["template_selected"]}

    def select_theme(self, state):
        theme = self.themes.get(state.get("theme_id", "corporate"))
        return {"theme_id": theme.theme_id, "history": state["history"] + ["theme_selected"]}

    def select_specialist(self, state):
        specialist = select_specialist(state.get("document_type"))
        if not specialist:
            return {"status": "needs_clarification", "history": state["history"] + ["specialist_missing"]}
        return {"specialist": specialist, "history": state["history"] + ["specialist_selected"]}

    def edit(self, state):
        content = state.get("content") or state["request"]
        result = self.editor.edit(content, state.get("operation", "rewrite"))
        return {"content": result.content, "status": result.status, "history": state["history"] + ["edited"]}

    def run_qa(self, state):
        from .document_models import DocumentArtifact
        artifact = DocumentArtifact(
            "CFS-DOC-GRAPH", state.get("document_type") or "",
            state.get("template_id") or "", state.get("theme_id") or "corporate",
            state.get("specialist") or "",
        )
        qa = self.qa.validate(artifact)
        return {"qa": qa, "history": state["history"] + ["qa"]}

    def approval_gate(self, state):
        if not state.get("qa", {}).get("passed"):
            return {"status": "needs_revision", "approval_required": True,
                    "credentials_exposed": False, "history": state["history"] + ["approval_blocked"]}
        if not state.get("approved", False):
            return {"status": "awaiting_founder_approval", "approval_required": True,
                    "credentials_exposed": False, "history": state["history"] + ["approval_wait"]}
        return {"status": "approved_for_export", "approval_required": True,
                "credentials_exposed": False, "history": state["history"] + ["approved"]}

    def run(self, request: str, theme: str = "corporate", operation: str = "rewrite",
            content: str = "", approved: bool = False) -> dict:
        reference_id = self.references.next(category="DOC")
        result = self.graph.invoke({
            "reference_id": reference_id,
            "request": request,
            "theme_id": theme,
            "operation": operation,
            "content": content,
            "approved": approved,
            "history": [],
            "credentials_exposed": False,
        })
        trace = DocumentTrace(reference_id)
        for stage in result.get("history", []):
            status = "completed"
            if stage in {"template_missing", "specialist_missing", "approval_blocked"}:
                status = "blocked"
            elif stage == "approval_wait":
                status = "awaiting_approval"
            trace.stage(stage, status)
        trace.stage("document_workflow", result.get("status", "unknown"),
                    document_type=result.get("document_type"), specialist=result.get("specialist"),
                    credentials_exposed=False)
        result["reference_id"] = reference_id
        result["trace"] = trace.summary()
        result["trace_events"] = trace.events()
        return result
