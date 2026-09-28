from __future__ import annotations


class IntegrationControlPlane:
    """Canonical adapter dispatch facade with health and bounded execution."""

    def __init__(self, integration_layer):
        self.integration = integration_layer

    def health(self):
        return self.integration.health()

    def dispatch(self, tenant_id, workspace_id, connector, action, payload=None, **kwargs):
        return self.integration.dispatch(
            tenant_id, workspace_id, connector, action, payload=payload, **kwargs
        )

    def retry(self, tenant_id, workspace_id, job_id, actor_id="system"):
        return self.integration.retry(tenant_id, workspace_id, job_id, actor_id)

    def jobs(self, tenant_id, workspace_id, limit=100):
        return self.integration.jobs(tenant_id, workspace_id, limit)
