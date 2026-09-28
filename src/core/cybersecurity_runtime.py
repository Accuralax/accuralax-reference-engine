from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .cybersecurity_teams import CybersecurityTeamEngine, SecurityProduct
from .references import ReferenceGenerator
from .security_rag import SecurityHit, SecurityKnowledgeRAG
from .supervisor import AgentSupervisor


@dataclass
class SecurityRuntimeState:
    reference_id: str
    authorized_scope: bool
    finding: dict[str, Any] = field(default_factory=dict)
    knowledge: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    status: str = "initialized"


class CybersecurityRuntime:
    """Bounded security-team runtime; external actions remain behind gateways."""

    def __init__(self) -> None:
        self.teams = CybersecurityTeamEngine()
        self.supervisor = AgentSupervisor()
        self.rag = SecurityKnowledgeRAG()

    def start(self, *, authorized_scope: bool) -> SecurityRuntimeState:
        reference = ReferenceGenerator().next("SEC")
        state = SecurityRuntimeState(reference, authorized_scope)
        state.status = "ready" if authorized_scope else "scope_required"
        state.events.append({
            "event": "scope_authorized" if authorized_scope else "scope_blocked",
            "reference_id": reference,
        })
        return state

    def retrieve_security_knowledge(
        self, state: SecurityRuntimeState, query: str, *, domain: str | None = None
    ) -> list[SecurityHit]:
        if not state.authorized_scope:
            state.status = "scope_required"
            return []
        hits = self.rag.search(query, domain=domain)
        state.knowledge = self.rag.provenance(hits)
        state.events.append({
            "event": "knowledge_retrieved",
            "reference_id": state.reference_id,
            "count": len(hits),
            "provenance": state.knowledge,
        })
        return hits

    def run_validation(
        self,
        state: SecurityRuntimeState,
        finding: dict[str, Any],
        *,
        live_red_testing: bool = False,
        approved: bool = False,
    ) -> SecurityRuntimeState:
        if not state.authorized_scope:
            state.status = "scope_required"
            return state

        red = self.teams.authorize(
            "red_team",
            "attack_path_simulation",
            authorized_scope=True,
            live_testing=live_red_testing,
        )
        blue = self.teams.authorize(
            "blue_team",
            "detection_engineering",
            authorized_scope=True,
        )

        if live_red_testing and not approved:
            state.status = "awaiting_approval"
            state.events.append({
                "event": "red_testing_approval_required",
                "reference_id": state.reference_id,
            })
            return state

        if not red.allowed or not blue.allowed:
            state.status = "blocked"
            state.events.append({
                "event": "validation_gate",
                "red": red.reason,
                "blue": blue.reason,
            })
            return state

        state.finding = dict(finding)
        state.status = "validation_complete"
        state.events.extend([
            {"event": "red_validation_complete", "reference_id": state.reference_id},
            {"event": "blue_defense_complete", "reference_id": state.reference_id},
        ])
        return state

    def product_opportunity(self, state: SecurityRuntimeState) -> SecurityProduct | None:
        product = self.teams.product_opportunity(state.finding)
        if product:
            state.events.append({
                "event": "product_opportunity",
                "reference_id": state.reference_id,
                "product_id": product.product_id,
            })
        return product

    def snapshot(self) -> dict[str, Any]:
        return {
            "runtime": "cybersecurity",
            "teams": ["red", "blue", "purple", "security_product"],
            "bounded": True,
            "knowledge": {"provider": "local_security_rag", "provenance": True},
            "external_actions": "gateway_only",
            "credentials_exposed_to_agents": False,
        }
