from pathlib import Path
from typing import Any
from datetime import datetime, timezone
import hashlib, json, math, os, re, sqlite3, uuid, yaml
try:
 import numpy as np
except ImportError: np=None
class EmbeddingProvider:
 dimension=256
 def __init__(self):
  self.model=os.getenv('KNOWLEDGE_EMBEDDING_MODEL','text-embedding-3-small'); self._client=None
  if os.getenv('OPENAI_API_KEY'):
   try:
    from openai import OpenAI; self._client=OpenAI(api_key=os.environ['OPENAI_API_KEY'])
   except Exception: self._client=None
 @property
 def name(self): return 'openai' if self._client else 'local-hash'
 def embed(self,text):
  if self._client:return list(self._client.embeddings.create(model=self.model,input=text).data[0].embedding)
  v=[0.0]*self.dimension
  for t in re.findall(r'[a-zA-Z0-9_]{2,}',text.lower()):
   h=hashlib.sha256(t.encode()).digest(); v[int.from_bytes(h[:4],'big')%self.dimension]+=1; v[int.from_bytes(h[4:8],'big')%self.dimension]-=.35
  n=math.sqrt(sum(x*x for x in v)) or 1; return [x/n for x in v]
class KnowledgeRAG:
 def __init__(self,config_path=None,db_path=None):
  root=Path(__file__).resolve().parents[1]; path=Path(config_path or root/'config'/'knowledge_rag.yaml')
  with path.open('r',encoding='utf-8') as h:self.config=yaml.safe_load(h) or {}
  self.db_path=Path(db_path) if db_path else root.parent/'data'/'knowledge_rag.sqlite3'; self.db_path.parent.mkdir(parents=True,exist_ok=True); self.embedder=EmbeddingProvider()
  with sqlite3.connect(self.db_path) as db:
   db.execute('CREATE TABLE IF NOT EXISTS knowledge (knowledge_id TEXT PRIMARY KEY, tenant_id TEXT, workspace_id TEXT, source TEXT, source_type TEXT, trust TEXT, state TEXT, content_hash TEXT, ingested_at TEXT, content TEXT, metadata TEXT)')
   db.execute('CREATE TABLE IF NOT EXISTS knowledge_chunks (chunk_id TEXT PRIMARY KEY, knowledge_id TEXT, tenant_id TEXT, workspace_id TEXT, chunk_index INTEGER, content TEXT, embedding BLOB, embedding_dim INTEGER, embedding_model TEXT)')
   db.execute('CREATE TABLE IF NOT EXISTS knowledge_conflicts (conflict_id TEXT PRIMARY KEY, tenant_id TEXT, workspace_id TEXT, knowledge_a TEXT, knowledge_b TEXT, reason TEXT, status TEXT, detected_at TEXT)'); db.commit()
 @staticmethod
 def content_hash(content):return hashlib.sha256(content.encode()).hexdigest()
 @staticmethod
 def _tokens(text):return set(re.findall(r'[a-zA-Z0-9_]{2,}',text.lower()))
 @staticmethod
 def _chunks(content,size=900,overlap=120):
  words=content.split(); out=[]; start=0
  while start<len(words):
   end=min(start+size,len(words)); out.append(' '.join(words[start:end]))
   if end==len(words):break
   start=max(end-overlap,start+1)
  return out
 @staticmethod
 def _cosine(a,b):
  if len(a)!=len(b):return 0
  na=math.sqrt(sum(x*x for x in a)); nb=math.sqrt(sum(x*x for x in b)); return max(0,min(1,sum(x*y for x,y in zip(a,b))/(na*nb))) if na and nb else 0
 def ingest(self,content,*,source,source_type='document',trust='unverified',metadata=None,tenant_id='default',workspace_id='default'):
  if not content.strip() or not source:raise ValueError('content and source are required')
  safe=self._safe(metadata or {}); kid=f'KNO-{uuid.uuid4().hex[:10].upper()}'; now=datetime.now(timezone.utc).isoformat(); ch=self.content_hash(content); chunks=self._chunks(content)
  with sqlite3.connect(self.db_path) as db:
   db.execute('INSERT INTO knowledge VALUES (?,?,?,?,?,?,?,?,?,?,?)',(kid,tenant_id,workspace_id,source,source_type,trust,'indexed',ch,now,content,json.dumps(safe)))
   for i,c in enumerate(chunks):
    vec=self.embedder.embed(c); blob=np.asarray(vec,dtype=np.float32).tobytes() if np is not None else json.dumps(vec).encode(); db.execute('INSERT INTO knowledge_chunks VALUES (?,?,?,?,?,?,?,?,?)',(f'CHK-{uuid.uuid4().hex[:12].upper()}',kid,tenant_id,workspace_id,i,c,blob,len(vec),self.embedder.name))
   db.commit()
  conflicts=self.detect_conflicts(kid,tenant_id=tenant_id,workspace_id=workspace_id)
  return {'knowledge_id':kid,'tenant_id':tenant_id,'workspace_id':workspace_id,'source':source,'source_type':source_type,'trust':trust,'state':'indexed','chunk_count':len(chunks),'embedding_provider':self.embedder.name,'content_hash':ch,'ingested_at':now,'metadata':safe,'conflicts_detected':len(conflicts)}
 def retrieve(self,query,*,minimum_trust='unverified',tenant_id='default',workspace_id='default'):
  ranks={v:i for i,v in enumerate(self.config.get('trust_levels',['unverified','low','medium','high','authoritative']))}; qt=self._tokens(query); qv=self.embedder.embed(query); grouped={}
  with sqlite3.connect(self.db_path) as db:rows=db.execute("SELECT c.knowledge_id,c.content,c.embedding,k.source,k.source_type,k.trust,k.state,k.content_hash,k.ingested_at,k.metadata FROM knowledge_chunks c JOIN knowledge k ON k.knowledge_id=c.knowledge_id WHERE c.tenant_id=? AND c.workspace_id=? AND k.state NOT IN ('archived','disputed')",(tenant_id,workspace_id)).fetchall()
  now=datetime.now(timezone.utc)
  for kid,c,blob,source,stype,trust,state,ch,ingested,metadata in rows:
   if ranks.get(trust,0)<ranks.get(minimum_trust,0):continue
   vec=np.frombuffer(blob,dtype=np.float32).tolist() if np is not None else json.loads(blob.decode()); semantic=self._cosine(qv,vec); overlap=len(qt&self._tokens(c)); lexical=overlap/max(len(qt),1)
   if semantic<=0 and overlap==0:continue
   try:freshness=1/(1+max((now-datetime.fromisoformat(ingested)).days,0)/30)
   except Exception:freshness=.5
   authority=ranks.get(trust,0)/max(len(ranks)-1,1); score=.55*semantic+.25*lexical+.12*freshness+.08*authority
   hit={'knowledge_id':kid,'source':source,'source_type':stype,'trust':trust,'state':state,'score':round(score,6),'semantic_score':round(semantic,6),'keyword_score':round(lexical,6),'keyword_overlap':overlap,'freshness':round(freshness,4),'source_authority':round(authority,4),'content_hash':ch,'ingested_at':ingested,'content':c,'tenant_id':tenant_id,'workspace_id':workspace_id,'metadata':json.loads(metadata or '{}')}
   if kid not in grouped or hit['score']>grouped[kid]['score']:grouped[kid]=hit
  return sorted(grouped.values(),key=lambda x:(x['score'],x['semantic_score']),reverse=True)
 def detect_conflicts(self,knowledge_id,*,tenant_id='default',workspace_id='default'):
  with sqlite3.connect(self.db_path) as db:
   row=db.execute('SELECT source,content,content_hash FROM knowledge WHERE knowledge_id=? AND tenant_id=? AND workspace_id=?',(knowledge_id,tenant_id,workspace_id)).fetchone()
   if not row:return []
   source,content,ch=row; rows=db.execute("SELECT knowledge_id,source,content,content_hash FROM knowledge WHERE tenant_id=? AND workspace_id=? AND knowledge_id<>? AND state!='archived'",(tenant_id,workspace_id,knowledge_id)).fetchall()
  a=self._tokens(content); found=[]
  for other,osource,ocontent,och in rows:
   b=self._tokens(ocontent); overlap=len(a&b)/max(len(a|b),1)
   if overlap>=.45 and ch!=och:
    cid=f'CON-{uuid.uuid4().hex[:10].upper()}'
    with sqlite3.connect(self.db_path) as db:db.execute('INSERT OR IGNORE INTO knowledge_conflicts VALUES (?,?,?,?,?,?,?,?)',(cid,tenant_id,workspace_id,knowledge_id,other,'high-content-overlap-with-different-hash','review',datetime.now(timezone.utc).isoformat()));db.commit()
    found.append({'conflict_id':cid,'knowledge_id':knowledge_id,'other_knowledge_id':other,'source':source,'other_source':osource,'status':'review'})
  return found
 def health(self):
  with sqlite3.connect(self.db_path) as db:
   count=db.execute('SELECT COUNT(*) FROM knowledge').fetchone()[0]; chunks=db.execute('SELECT COUNT(*) FROM knowledge_chunks').fetchone()[0]; conflicts=db.execute("SELECT COUNT(*) FROM knowledge_conflicts WHERE status='review'").fetchone()[0]
  return {'status':'ok','knowledge_count':count,'item_count':count,'chunk_count':chunks,'conflict_count':conflicts,'storage':'SQLite','retrieval_mode':'hybrid','semantic_search':True,'keyword_search':True,'reranking':True,'conflict_detection':True,'embedding_provider':self.embedder.name,'embedding_model':getattr(self.embedder,'model',None),'provenance_required':True,'credentials_indexed':False}
 @staticmethod
 def _safe(value):
  blocked={'password','api_key','apikey','token','secret','cvv','card_number','credential','credentials'}
  if isinstance(value,dict):return {str(k):KnowledgeRAG._safe(v) for k,v in value.items() if str(k).lower() not in blocked}
  if isinstance(value,list):return [KnowledgeRAG._safe(v) for v in value]
  return value
