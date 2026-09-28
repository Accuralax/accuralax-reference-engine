from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from .business_function_team import BusinessFunctionTeam
from .business_functions import classify_business_function
from .business_function_skills import BusinessSkillRegistry
from .business_function_rag import BusinessFunctionRAG
from .business_skill_executor import BusinessSkillExecutor


class BusinessSupervisorGraphState(TypedDict, total=False):
    request: str
    function: str | None
    specialist: str | None
    action: str | None
    approved: bool
    selected_skill: str | None
    knowledge: list[dict[str, Any]]
    skill_status: str
    skill_reason: str
    delegation_count: int
    max_delegations: int
    status: str
    reason: str
    verification_status: str
    history: list[str]
    terminal: bool
    credentials_exposed: bool


def _history(state: BusinessSupervisorGraphState, node: str) -> list[str]:
    return [*state.get("history", []), node]


def build_business_supervisor_graph(*, max_delegations: int = 3):
    team = BusinessFunctionTeam()
    graph = StateGraph(BusinessSupervisorGraphState)
    skills = BusinessSkillRegistry()
    rag = BusinessFunctionRAG()
    skill_executor = BusinessSkillExecutor()

    def intake(state: BusinessSupervisorGraphState) -> dict[str, Any]:
        return {"status": "intake", "history": _history(state, "intake"), "credentials_exposed": False}

    def classify(state: BusinessSupervisorGraphState) -> dict[str, Any]:
        function = classify_business_function(state.get("request", ""))
        specialist = team.select(function) if function else None
        if not function or not specialist:
            return {
                "function": function,
                "specialist": specialist,
                "status": "clarification_required",
                "reason": "business_function_ambiguous",
                "terminal": True,
                "history": _history(state, "classify"),
                "credentials_exposed": False,
            }
        return {
            "function": function,
            "specialist": specialist,
            "status": "classified",
            "history": _history(state, "classify"),
            "credentials_exposed": False,
        }

    def delegation(state: BusinessSupervisorGraphState) -> dict[str, Any]:
        count = state.get("delegation_count", 0) + 1
        if max_delegations <= 0 or count > max_delegations:
            return {
                "delegation_count": count,
                "status": "delegation_limit",
                "reason": "max_delegations_reached",
                "terminal": True,
                "history": _history(state, "delegation"),
            }
        return {
            "delegation_count": count,
            "status": "delegation_authorized",
            "history": _history(state, "delegation"),
        }

    def approval(state: BusinessSupervisorGraphState) -> dict[str, Any]:
        action = state.get("action")
        if not action:
            return {"status": "verification", "history": _history(state, "approval")}
        decision = team.authorize(
            state.get("specialist", ""),
            action,
            approved=bool(state.get("approved", False)),
        )
        if not decision.allowed:
            return {
                "status": "awaiting_approval" if decision.requires_approval else "action_denied",
                "reason": decision.reason,
                "terminal": not decision.requires_approval,
                "verification_status": "pending",
                "history": _history(state, "approval"),
            }
        return {"status": "action_authorized", "history": _history(state, "approval")}

    def skill_prepare(state: BusinessSupervisorGraphState) -> dict[str, Any]:
        function = state.get("function")
        specialist = state.get("specialist")
        request = state.get("request", "")
        action = state.get("action")
        if not function or not specialist:
            return {"status": "skill_denied", "skill_reason": "missing_business_context", "history": _history(state, "skill_prepare")}
        candidates = skills.select(function, action)
        if not candidates:
            candidates = skills.skills_for(function)
        if not candidates:
            return {"status": "skill_denied", "skill_reason": "no_skill_available", "history": _history(state, "skill_prepare")}
        skill = candidates[0]
        selected_action = action or skills.get(skill).get("actions", ["inspect"])[0]
        plan = skill_executor.execute_plan(
            function=function,
            specialist=specialist,
            skill=skill,
            action=selected_action,
            request=request,
            approved=bool(state.get("approved", False)),
        )
        return {
            "selected_skill": skill,
            "knowledge": plan.knowledge,
            "skill_status": plan.status,
            "skill_reason": plan.reason,
            "status": "skill_ready" if plan.allowed and plan.status == "planned" else plan.status,
            "reason": plan.reason,
            "history": _history(state, "skill_prepare"),
            "credentials_exposed": False,
        }

    def verify(state: BusinessSupervisorGraphState) -> dict[str, Any]:
        if state.get("status") in {"awaiting_approval", "action_denied", "delegation_limit"}:
            return {"verification_status": "pending", "history": _history(state, "verify")}
        return {
            "verification_status": "pass",
            "status": "ready_for_specialist",
            "history": _history(state, "verify"),
        }

    def terminal(state: BusinessSupervisorGraphState) -> dict[str, Any]:
        return {"terminal": True, "history": _history(state, "terminal"), "credentials_exposed": False}

    def after_classify(state: BusinessSupervisorGraphState) -> str:
        return "terminal" if state.get("terminal") else "delegation"

    def after_delegation(state: BusinessSupervisorGraphState) -> str:
        if state.get("terminal"):
            return "terminal"
        return "approval" if state.get("action") else "skill_prepare"

    def after_skill(state: BusinessSupervisorGraphState) -> str:
        return "verify" if state.get("status") in {"skill_ready", "planned"} else "terminal"

    def after_approval(state: BusinessSupervisorGraphState) -> str:
        return "skill_prepare" if state.get("status") == "action_authorized" else END

    graph.add_node("intake", intake)
    graph.add_node("classify", classify)
    graph.add_node("delegation", delegation)
    graph.add_node("approval", approval)
    graph.add_node("skill_prepare", skill_prepare)
    graph.add_node("verify", verify)
    graph.add_node("terminal", terminal)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "classify")
    graph.add_conditional_edges("classify", after_classify, {"delegation": "delegation", "terminal": "terminal"})
    graph.add_conditional_edges("delegation", after_delegation, {"approval": "approval", "skill_prepare": "skill_prepare", "terminal": "terminal"})
    graph.add_conditional_edges("skill_prepare", after_skill, {"verify": "verify", "terminal": "terminal"})
    graph.add_conditional_edges("approval", after_approval, {"skill_prepare": "skill_prepare", END: END})
    graph.add_edge("verify", "terminal")
    graph.add_edge("terminal", END)
    return graph.compile()


def run_business_supervisor_graph(
    request: str,
    *,
    action: str | None = None,
    approved: bool = False,
    max_delegations: int = 3,
) -> BusinessSupervisorGraphState:
    return build_business_supervisor_graph(max_delegations=max_delegations).invoke({
        "request": request,
        "action": action,
        "approved": approved,
        "delegation_count": 0,
        "history": [],
        "credentials_exposed": False,
    })
