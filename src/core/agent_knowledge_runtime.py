from __future__ import annotations
from typing import Any
from .unified_agent_brain import UnifiedAgentBrain
from .hybrid_context_engine import HybridContextEngine
from .lms_training import LMSTraining
from .lms_intelligence import LMSIntelligence
from .customer_360 import Customer360
from .opportunity_revenue import OpportunityRevenue

class AgentKnowledgeRuntime:
    """Unified governed runtime for agent skills, memory and enterprise RAG."""
    def __init__(self)->None:
        self.unified=UnifiedAgentBrain(); self.brain=self.unified.brain; self.rag=self.unified.rag; self.memory=self.unified.memory
        self.lms=LMSTraining(); self.lms_intelligence=LMSIntelligence(lms=self.lms)
        self.customer_360=Customer360(); self.opportunities=OpportunityRevenue()
        self.hybrid=HybridContextEngine(memory=self.memory, rag=self.rag, graph=self.unified.graph, customer_360=self.customer_360, lms=self.lms, lms_intelligence=self.lms_intelligence, opportunities=self.opportunities)
    def context(self,agent_id:str,request:str,*,tenant_id:str='default',workspace_id:str='default',entity_id:str|None=None,learner_id:str|None=None)->dict[str,Any]:
        context=self.hybrid.build(agent_id,request,tenant_id=tenant_id,workspace_id=workspace_id,entity_id=entity_id)
        context['agent']=self.brain.profile(agent_id); context['working_memory']=self.brain.recall(agent_id,request,limit=5); context['persistent_memory']=context['memory']
        if entity_id:
            try: self.hybrid.enrich_customer(context,entity_id=entity_id)
            except ValueError as exc: context['enrichment_error']=str(exc)
        if learner_id:
            try: self.hybrid.enrich_learner(context,learner_id=learner_id)
            except ValueError as exc: context['enrichment_error']=str(exc)
        context['credentials_exposed']=False; return context
    def learn_experience(self,agent_id:str,request:str,outcome:str,reference_id:str,*,tenant_id:str='default',workspace_id:str='default')->dict[str,Any]:return self.unified.capture_experience(agent_id,request,outcome,reference_id,tenant_id=tenant_id,workspace_id=workspace_id)
    def health(self)->dict[str,Any]:return self.unified.health()
