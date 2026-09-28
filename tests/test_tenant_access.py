from src.core.tenant_access import AccessContext, TenantAccess
from src.core.agentic_workspace import AgenticWorkspace

def test_cross_tenant_denied():
    a=TenantAccess()
    ctx=AccessContext(tenant_id='tenant-a',workspace_id='workspace-a',actor_id='u',role='owner')
    assert a.authorize(ctx,'execute_bounded','tenant-b','workspace-a')['allowed'] is False

def test_cross_workspace_denied():
    a=TenantAccess()
    ctx=AccessContext(tenant_id='tenant-a',workspace_id='workspace-a',actor_id='u',role='owner')
    assert a.authorize(ctx,'execute_bounded','tenant-a','workspace-b')['allowed'] is False

def test_viewer_cannot_execute():
    a=TenantAccess()
    ctx=AccessContext(tenant_id='t',workspace_id='w',actor_id='u',role='viewer')
    assert a.authorize(ctx,'execute_bounded','t','w')['allowed'] is False

def test_workspace_enforces_access():
    result=AgenticWorkspace().run('test',tenant_id='a',workspace_id='w',actor_id='u',role='viewer')
    assert result['status']=='blocked'
    assert result['reason']=='access_denied'
