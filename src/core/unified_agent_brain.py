from __future__ import annotations
from typing import Any
from .agent_brain import AgentBrain
from .knowledge_rag import KnowledgeRAG
from .persistent_memory import PersistentMemory
from .evidence_verifier import EvidenceVerifier
from .context_graph import TemporalContextGraph

class UnifiedAgentBrain:
    """Shared enterprise brain with scoped memory, knowledge retrieval and provenance."""
    def __init__(self)->None:
        self.brain=AgentBrain(); self.memory=PersistentMemory(); self.rag=KnowledgeRAG(); self.graph=TemporalContextGraph()
    def context(self,agent_id:str,request:str,*,tenant_id:str='default',workspace_id:str='default')->dict[str,Any]:
        profile=self.brain.profile(agent_id); scope=profile['domains']
        persistent=self.memory.retrieve_ranked(agent_id,request,scope=scope,limit=5)
        knowledge=self.rag.retrieve(request,minimum_trust='medium',tenant_id=tenant_id,workspace_id=workspace_id)
        verification=EvidenceVerifier().verify(request,knowledge,persistent)
        graph=self.graph.current(tenant_id,workspace_id,agent_id)
        return {'agent_id':agent_id,'tenant_id':tenant_id,'workspace_id':workspace_id,'domains':scope,'skills':profile['skills'],'working_memory':self.brain.recall(agent_id,request,limit=5),'persistent_memory':persistent,'knowledge':knowledge,'graph':[self.graph.as_dict(f) for f in graph],'evidence':{'count':len(knowledge),'minimum_trust':'medium','provenance_required':True,'conflicts_require_review':True,**verification},'governance':{'policy_precedence':True,'credentials_exposed':False}}
    def capture_experience(self,agent_id:str,request:str,outcome:str,reference_id:str,*,tenant_id:str='default',workspace_id:str='default')->dict[str,Any]:
        profile=self.brain.profile(agent_id)
        saved=self.memory.write(agent_id,'episodic',f'Request: {request}. Outcome: {outcome}.',scope=profile['domains'],provenance=f'agent_run:{reference_id}',confidence=.9,importance=.7,validated=False)
        if saved.get('allowed'):
            self.graph.add_fact(tenant_id,workspace_id,agent_id,'experienced_run',reference_id,source=f'agent_run:{reference_id}',confidence=.7,reference_id=reference_id,agent_id=agent_id)
        return saved
    def validate_experience(self,memory_id:str,confidence:float=.9)->dict[str,Any]:return self.memory.validate(memory_id,confidence)
    def health(self)->dict[str,Any]:return {'status':'ok','brain':self.brain.health(),'persistent_memory':self.memory.health(),'rag':self.rag.health(),'context_graph':self.graph.health(),'credentials_exposed':False}
