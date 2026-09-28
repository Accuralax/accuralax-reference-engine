import json
from src.api_server import Handler

def test_rag_module_imports():
    from src.api_server import workspace
    item=workspace.knowledge.rag.ingest('finance compliance policy',source='test',tenant_id='api-t',workspace_id='api-w')
    hits=workspace.knowledge.rag.retrieve('compliance',tenant_id='api-t',workspace_id='api-w')
    assert item['knowledge_id'] and hits

def test_rag_health():
    from src.api_server import workspace
    assert workspace.knowledge.rag.health()['status']=='ok'
