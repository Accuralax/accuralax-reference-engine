from src.core.knowledge_rag import KnowledgeRAG

def test_rag_persists_and_isolates(tmp_path):
    db=tmp_path/'rag.sqlite3'
    a=KnowledgeRAG(db_path=str(db))
    x=a.ingest('cybersecurity policy incident response',source='policy.pdf',trust='verified',tenant_id='A',workspace_id='W1',metadata={'owner':'team','api_key':'hidden'})
    assert x['knowledge_id'].startswith('KNO-')
    assert 'api_key' not in x['metadata']
    b=KnowledgeRAG(db_path=str(db))
    assert b.retrieve('cybersecurity incident',tenant_id='A',workspace_id='W1')
    assert b.retrieve('cybersecurity',tenant_id='B',workspace_id='W1')==[]
    assert b.retrieve('cybersecurity',tenant_id='A',workspace_id='W2')==[]

def test_rag_health_is_durable(tmp_path):
    db=tmp_path/'rag.sqlite3'; KnowledgeRAG(db_path=str(db)).ingest('hello',source='x',tenant_id='t',workspace_id='w')
    assert KnowledgeRAG(db_path=str(db)).health()['item_count']==1
