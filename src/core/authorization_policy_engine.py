from __future__ import annotations
import os,sqlite3,uuid
from datetime import datetime,timezone

class AuthorizationPolicyEngine:
    ROLES={'OWNER','ADMIN','MEMBER','VIEWER'}
    PERMS={'OWNER':{'*'},'ADMIN':{'read','write','execute','manage_members','manage_policies','manage_agents','manage_skills','approve'},'MEMBER':{'read','write','execute'},'VIEWER':{'read'}}
    def __init__(self,db_path=None):
        self.db_path=db_path or os.path.join('data','authorization_policy.sqlite3'); os.makedirs(os.path.dirname(self.db_path) or '.',exist_ok=True)
        with self.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS memberships(tenant_id TEXT,workspace_id TEXT,principal_id TEXT,role TEXT,active INTEGER,PRIMARY KEY(tenant_id,workspace_id,principal_id))')
            c.execute('CREATE TABLE IF NOT EXISTS policies(tenant_id TEXT,workspace_id TEXT,action TEXT,role TEXT,allow INTEGER,approval INTEGER)')
            c.execute('CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,principal_id TEXT,action TEXT,allowed INTEGER,reason TEXT,created_at TEXT)')
    def db(self):
        c=sqlite3.connect(self.db_path); c.row_factory=sqlite3.Row
        class C:
            def __enter__(s): return c
            def __exit__(s,*a): c.commit(); c.close()
        return C()
    def set_membership(self,t,w,p,role):
        role=str(role).upper()
        if role not in self.ROLES: raise ValueError('invalid_role')
        with self.db() as c: c.execute('INSERT OR REPLACE INTO memberships VALUES(?,?,?,?,1)',(str(t),str(w),str(p),role))
        return self.get_membership(t,w,p)
    def get_membership(self,t,w,p):
        with self.db() as c:r=c.execute('SELECT * FROM memberships WHERE tenant_id=? AND workspace_id=? AND principal_id=?',(str(t),str(w),str(p))).fetchone()
        return dict(r) if r else None
    def add_policy(self,t,w,action,role=None,allow=True,approval=False):
        with self.db() as c:c.execute('INSERT INTO policies VALUES(?,?,?,?,?,?)',(str(t),str(w),str(action),role,int(allow),int(approval)))
        return {'tenant_id':str(t),'workspace_id':str(w),'action':str(action),'role':role,'allow':bool(allow),'approval':bool(approval)}
    def authorize(self,t,w,p,action,approved=False):
        m=self.get_membership(t,w,p); allowed=False; reason='deny_no_membership'; approval=False
        if m and m['active']:
            perms=self.PERMS[m['role']]; allowed='*' in perms or action in perms or str(action).split(':',1)[0] in perms; reason='allowed_role_permission' if allowed else 'deny_role_permission'
            with self.db() as c: rows=c.execute('SELECT * FROM policies WHERE tenant_id=? AND workspace_id=? AND action=? AND (role IS NULL OR role=?)',(str(t),str(w),str(action),m['role'])).fetchall()
            # Deterministic precedence: explicit deny always wins; otherwise any
            # applicable approval requirement blocks execution until approved.
            deny = any(not bool(x['allow']) for x in rows)
            approval = any(bool(x['approval']) for x in rows)
            if deny:
                allowed=False; reason='deny_explicit_policy'
            elif approval and not approved:
                allowed=False; reason='approval_required'
        d={'id':'DEC-'+uuid.uuid4().hex[:12].upper(),'tenant_id':str(t),'workspace_id':str(w),'principal_id':str(p),'action':str(action),'allowed':bool(allowed),'reason':reason,'approval_required':approval,'created_at':datetime.now(timezone.utc).isoformat()}
        with self.db() as c:c.execute('INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?)',(d['id'],d['tenant_id'],d['workspace_id'],d['principal_id'],d['action'],int(d['allowed']),d['reason'],d['created_at']))
        return d
    def health(self):
        with self.db() as c:m=c.execute('SELECT COUNT(*) FROM memberships').fetchone()[0]; p=c.execute('SELECT COUNT(*) FROM policies').fetchone()[0]; d=c.execute('SELECT COUNT(*) FROM decisions').fetchone()[0]
        return {'status':'ok','deny_by_default':True,'roles':sorted(self.ROLES),'memberships':m,'policies':p,'decisions':d,'tenant_workspace_scoped':True,'approval_aware':True}
