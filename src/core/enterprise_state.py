from pathlib import Path
from datetime import datetime, timezone
import sqlite3, json, uuid

class EnterpriseState:
    def __init__(self, db_path=None):
        root=Path(__file__).resolve().parents[2]
        self.db_path=Path(db_path) if db_path else root/'data'/'enterprise_state.sqlite3'
        self.db_path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.db_path, timeout=15.0) as db:
            db.execute('PRAGMA busy_timeout=15000')
            db.execute('CREATE TABLE IF NOT EXISTS executions (reference_id TEXT PRIMARY KEY, request_id TEXT, trace_id TEXT, correlation_id TEXT, tenant_id TEXT, workspace_id TEXT, actor_id TEXT, channel TEXT, request TEXT, status TEXT, risk_level TEXT, approval_state TEXT, safety_status TEXT, verification_status TEXT, agent TEXT, domain TEXT, created_at TEXT, updated_at TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS audit_events (event_id TEXT PRIMARY KEY, reference_id TEXT, node TEXT, status TEXT, details TEXT, request_id TEXT, trace_id TEXT, correlation_id TEXT, created_at TEXT)')
            for table, col in (("executions","correlation_id"),("audit_events","request_id"),("audit_events","trace_id"),("audit_events","correlation_id")):
                cols={r[1] for r in db.execute(f'PRAGMA table_info({table})')}
                if col not in cols: db.execute(f'ALTER TABLE {table} ADD COLUMN {col} TEXT')
            db.commit()

    def save_execution(self,c):
        now=datetime.now(timezone.utc).isoformat()
        vals=(c['reference_id'],c['request_id'],c['trace_id'],c.get('correlation_id'),c.get('tenant_id','default'),c.get('workspace_id','default'),c.get('actor_id','system'),c.get('channel','internal'),c.get('request',''),c.get('status','received'),c.get('risk_level','low'),c.get('approval_state','not_required'),c.get('safety_status'),c.get('verification_status'),c.get('agent'),c.get('domain'),c.get('created_at',now),now)
        with sqlite3.connect(self.db_path, timeout=15.0) as db:
            db.execute('PRAGMA busy_timeout=15000')
            db.execute('INSERT OR REPLACE INTO executions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',vals); db.commit()

    def append_audit(self,reference_id,node,status,details=None,request_id=None,trace_id=None,correlation_id=None):
        event_id='TRC-'+uuid.uuid4().hex[:12].upper()
        safe={k:v for k,v in (details or {}).items() if str(k).lower() not in {'password','api_key','apikey','token','secret','credential','credentials'}}
        with sqlite3.connect(self.db_path, timeout=15.0) as db:
            db.execute('PRAGMA busy_timeout=15000')
            db.execute('INSERT INTO audit_events VALUES (?,?,?,?,?,?,?,?,?)',(event_id,reference_id,node,status,json.dumps(safe),request_id,trace_id,correlation_id,datetime.now(timezone.utc).isoformat())); db.commit()
        return event_id

    def recent_executions(self,limit=20):
        with sqlite3.connect(self.db_path, timeout=15.0) as db:
            db.execute('PRAGMA busy_timeout=15000')
            rows=db.execute('SELECT reference_id,request_id,trace_id,correlation_id,status,approval_state,agent,domain,created_at,updated_at FROM executions ORDER BY updated_at DESC LIMIT ?',(max(1,min(limit,100)),)).fetchall()
        keys=['reference_id','request_id','trace_id','correlation_id','status','approval_state','agent','domain','created_at','updated_at']
        return [dict(zip(keys,r)) for r in rows]

    def audit(self,reference_id):
        with sqlite3.connect(self.db_path, timeout=15.0) as db:
            db.execute('PRAGMA busy_timeout=15000')
            rows=db.execute('SELECT event_id,node,status,details,request_id,trace_id,correlation_id,created_at FROM audit_events WHERE reference_id=? ORDER BY created_at',(reference_id,)).fetchall()
        return [{'event_id':r[0],'node':r[1],'status':r[2],'details':json.loads(r[3]),'request_id':r[4],'trace_id':r[5],'correlation_id':r[6],'created_at':r[7]} for r in rows]

    def health(self):
        with sqlite3.connect(self.db_path, timeout=15.0) as db:
            db.execute('PRAGMA busy_timeout=15000')
            e=db.execute('SELECT COUNT(*) FROM executions').fetchone()[0]; a=db.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0]
        return {'status':'ok','executions':e,'audit_events':a,'sensitive_data_stored':False,'traceable':True}
