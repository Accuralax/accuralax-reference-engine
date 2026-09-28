class OmegaOrchestrationBoundary:
    def __init__(self, legacy_plane, omega_runtime=None):
        self.legacy = legacy_plane
        self.omega = omega_runtime

    def create(self, tenant_id, workspace_id, run_type, payload=None, requested_by="system", correlation_id=None, trace_id=None, omega_request_id=None):
        data = dict(payload or {})
        if omega_request_id:
            data["omega_request_id"] = str(omega_request_id)
            data["execution_authority"] = "OMEGA"
        return self.legacy.create(tenant_id, workspace_id, run_type, data, requested_by, correlation_id, trace_id)

    def execute(self, tenant_id, workspace_id, run_id):
        return self.legacy.execute(tenant_id, workspace_id, run_id)

    def health(self):
        result = self.legacy.health()
        result["omega_configured"] = bool(self.omega and self.omega.enabled)
        result["migration_boundary"] = True
        return result
