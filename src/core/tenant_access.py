from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class AccessContext:
    tenant_id: str = 'default'
    workspace_id: str = 'default'
    actor_id: str = 'system'
    role: str = 'viewer'
    trust: str = 'verified'

class TenantAccess:
    ROLES={'owner':{'read','analyse','execute_bounded','execute_scoped','request_approval','admin'},'admin':{'read','analyse','execute_bounded','execute_scoped','request_approval','admin'},'manager':{'read','analyse','execute_bounded','execute_scoped','request_approval'},'member':{'read','analyse','execute_bounded'},'viewer':{'read','analyse'},'agent':{'read','analyse','execute_bounded','execute_scoped','request_approval'},'sub_agent':{'read','analyse','execute_bounded'}}
    def authorize(self, ctx: AccessContext, permission: str, tenant_id: str, workspace_id: str) -> dict[str,Any]:
        same_scope=ctx.tenant_id==tenant_id and ctx.workspace_id==workspace_id
        allowed=same_scope and permission in self.ROLES.get(ctx.role,set()) and ctx.trust!='untrusted'
        return {'allowed':allowed,'tenant_id':tenant_id,'workspace_id':workspace_id,'actor_id':ctx.actor_id,'role':ctx.role,'permission':permission,'scope_match':same_scope,'credentials_exposed':False}
    def health(self): return {'status':'ok','role_count':len(self.ROLES),'cross_tenant_access':'denied_by_default','credentials_exposed':False}
