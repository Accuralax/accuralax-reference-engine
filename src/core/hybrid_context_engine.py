from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import hashlib
import json
import uuid

from .evidence_verifier import EvidenceVerifier
from .persistent_memory import PersistentMemory
from .knowledge_rag import KnowledgeRAG
from .context_graph import TemporalContextGraph
from .customer_360 import Customer360
from .opportunity_revenue import OpportunityRevenue


class HybridContextEngine:
    """Governed context assembly across memory, RAG and temporal graph."""
    def __init__(self, *, memory=None, rag=None, graph=None, customer_360=None, lms=None, lms_intelligence=None, opportunities=None) -> None:
        self.memory = memory or PersistentMemory()
        self.rag = rag or KnowledgeRAG()
        self.graph = graph or TemporalContextGraph()
        self.customer_360 = customer_360 or Customer360()
        self.opportunities = opportunities or OpportunityRevenue()
        self.lms = lms
        self.lms_intelligence = lms_intelligence
        self.verifier = EvidenceVerifier()

    @staticmethod
    def _trace_id(agent_id: str, request: str) -> str:
        raw = f"{agent_id}:{request}:{datetime.now(timezone.utc).isoformat()}".encode()
        return f"CTX-{hashlib.sha256(raw).hexdigest()[:12].upper()}"

    @staticmethod
    def _memory_item(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_type": "persistent_memory",
            "source_id": item.get("memory_id"),
            "content": item.get("content", ""),
            "score": float(item.get("memory_score", 0)),
            "freshness": float(item.get("freshness", 0)),
            "confidence": float(item.get("confidence", 0)),
            "provenance": item.get("provenance"),
            "state": item.get("state"),
        }
    @staticmethod
    def _graph_item(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_type": "temporal_graph",
            "source_id": item.get("fact_id"),
            "content": f"{item.get('subject_id')} {item.get('predicate')} {item.get('object_id')}",
            "score": float(item.get("confidence", 0)),
            "freshness": 1.0 if not item.get("valid_until") else 0.0,
            "confidence": float(item.get("confidence", 0)),
            "provenance": item.get("reference_id") or item.get("source"),
            "state": "current" if not item.get("valid_until") else "historical",
            "valid_from": item.get("valid_from"),
            "valid_until": item.get("valid_until"),
        }

    @staticmethod
    def _rag_item(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_type": "knowledge_rag",
            "source_id": item.get("knowledge_id"),
            "content": item.get("content", ""),
            "score": float(item.get("score", 0)),
            "freshness": float(item.get("freshness", 0)),
            "confidence": float(item.get("source_authority", 0)),
            "provenance": item.get("source"),
            "state": item.get("state"),
            "trust": item.get("trust"),
            "content_hash": item.get("content_hash"),
        }

    def build(self, agent_id: str, request: str, *, tenant_id: str = "default",
              workspace_id: str = "default", entity_id: str | None = None,
              memory_limit: int = 5, knowledge_limit: int = 8,
              graph_limit: int = 8) -> dict[str, Any]:
        if not agent_id or not request.strip() or not tenant_id or not workspace_id:
            return {"allowed": False, "reason": "identity_scope_request_required"}
        return self._build_with_scope(agent_id, request, tenant_id, workspace_id,
                                      entity_id, memory_limit, knowledge_limit, graph_limit)
    def _build_with_scope(self, agent_id: str, request: str, tenant_id: str,
                          workspace_id: str, entity_id: str | None,
                          memory_limit: int, knowledge_limit: int,
                          graph_limit: int) -> dict[str, Any]:
        # Persistent memory remains agent/scope governed; RAG and graph are tenant/workspace isolated.
        try:
            from .agent_brain import AgentBrain
            profile = AgentBrain().profile(agent_id)
            domains = profile.get("domains", [])
            skills = profile.get("skills", [])
        except Exception:
            domains, skills = [], []

        memories = self.memory.retrieve_ranked(agent_id, request, scope=domains, limit=memory_limit)
        knowledge = self.rag.retrieve(request, minimum_trust="medium",
                                      tenant_id=tenant_id, workspace_id=workspace_id)[:knowledge_limit]
        graph_subject = entity_id or agent_id
        facts = self.graph.current(tenant_id, workspace_id, graph_subject)[:graph_limit]

        # Entity-aware graph context: an explicit client/entity gets priority.
        # When no entity is supplied, keep the graph scoped to the active agent.
        items = ([self._memory_item(x) for x in memories] +
                 [self._rag_item(x) for x in knowledge] +
                 [self._graph_item(self.graph.as_dict(x)) for x in facts])
        items.sort(key=lambda x: (x["score"], x["confidence"], x["freshness"]), reverse=True)

        evidence = self.verifier.verify(request, knowledge, memories)
        trace_id = self._trace_id(agent_id, request)
        return {
            "allowed": True, "trace_id": trace_id, "agent_id": agent_id,
            "tenant_id": tenant_id, "workspace_id": workspace_id,
            "entity_id": entity_id, "domains": domains, "skills": skills,
            "items": items, "memory": memories, "knowledge": knowledge,
            "graph": [self.graph.as_dict(f) for f in facts],
            "evidence": evidence,
            "governance": {
                "tenant_isolation": True, "workspace_isolation": True,
                "policy_precedence": True, "provenance_required": True,
                "credentials_exposed": False, "conflicts_require_review": True,
            },
            "credentials_exposed": False,
        }

    def _crm_item(self, item: dict[str, Any], kind: str) -> dict[str, Any]:
        return {
            "source_type": f"crm_{kind}",
            "source_id": item.get("event_id") or item.get("opportunity_id") or item.get("relationship_id"),
            "content": item.get("summary") or item.get("name") or item.get("subject") or "",
            "score": 1.0,
            "freshness": 1.0,
            "confidence": 1.0,
            "provenance": "customer_360",
            "state": item.get("status", "current"),
        }

    def enrich_customer(self, context: dict[str, Any], *, entity_id: str) -> dict[str, Any]:
        tenant_id = context["tenant_id"]
        workspace_id = context["workspace_id"]
        customer = Customer360().customer_360(tenant_id, workspace_id, entity_id)
        opportunities = OpportunityRevenue().revenue(tenant_id, workspace_id)
        context["customer_360"] = customer
        context["revenue_snapshot"] = opportunities
        additions = []
        additions.extend(self._crm_item(x, "timeline") for x in customer["timeline"][:5])
        additions.extend(self._crm_item(x, "opportunity") for x in customer["opportunities"][:5])
        context["items"] = sorted(context.get("items", []) + additions,
                                   key=lambda x: (x["score"], x["confidence"], x["freshness"]),
                                   reverse=True)
        context["enrichment"] = {
            "customer_360": True,
            "sales_revenue": True,
            "entity_id": entity_id,
            "credentials_exposed": False,
        }
        return context

    def enrich_learner(self, context: dict[str, Any], *, learner_id: str) -> dict[str, Any]:
        if not self.lms_intelligence:
            from .lms_intelligence import LMSIntelligence
            self.lms_intelligence = LMSIntelligence(lms=self.lms)
        tenant_id, workspace_id = context["tenant_id"], context["workspace_id"]
        profile = self.lms_intelligence.learner_profile(tenant_id, workspace_id, learner_id)
        performance = self.lms_intelligence.performance_summary(tenant_id, workspace_id, learner_id)
        gaps = self.lms_intelligence.skill_gaps(tenant_id, workspace_id, learner_id)
        context["lms"] = {"learner_profile": profile, "performance": performance, "skill_gaps": gaps}
        additions = []
        for item in profile["progress"][:5]:
            additions.append({"source_type":"lms_progress", "source_id":item.get("course_id"),
                              "content":str(item.get("title", "course")) + " progress " + str(item.get("completion_pct", 0)) + "%",
                              "score":1.0,"freshness":1.0,"confidence":1.0,"provenance":"lms", "state":"current"})
        for gap in gaps["gaps"][:5]:
            additions.append({"source_type":"lms_skill_gap", "source_id":gap.get("competency_id"),
                              "content":str(gap.get("name", "competency")) + " requires development",
                              "score":1.0,"freshness":1.0,"confidence":1.0,"provenance":"lms_intelligence", "state":"review"})
        context["items"] = sorted(context.get("items", []) + additions,
                                   key=lambda x:(x["score"],x["confidence"],x["freshness"]), reverse=True)
        context.setdefault("enrichment", {})["lms"] = True
        context["enrichment"]["learner_id"] = learner_id
        return context

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "hybrid": True,
            "sources": ["persistent_memory", "knowledge_rag", "temporal_graph", "customer_360", "sales_revenue"],
            "tenant_isolation": True,
            "workspace_isolation": True,
            "provenance_required": True,
            "credentials_exposed": False,
        }
