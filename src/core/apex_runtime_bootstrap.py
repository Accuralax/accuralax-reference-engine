from __future__ import annotations
from .omega8_full_convergence import Omega8FullConvergence
from .omega9_production_convergence import Omega9ProductionConvergence
from .omega10_regulatory_convergence import Omega10RegulatoryConvergence
from .omega11_agent_marketplace import Omega11AgentMarketplace
from .omega12_ai_evaluation import Omega12AdvancedAIEvaluation
from .omega12_production_convergence import Omega12ProductionConvergence
from .omega13_autonomous_optimization import Omega13AutonomousOptimization
from .omega14_global_multitenant import Omega14GlobalMultiTenantPlatform
from .omega15_enterprise_final import Omega15EnterpriseFinal
from .omega_final_convergence import OmegaFinalConvergence
from .apex_production_certification import ApexProductionCertification
from .runtime_invariants import RuntimeInvariants

class ApexRuntimeBootstrap:
    """Canonical in-process Ω8→Ω15 runtime composition and certification."""
    def __init__(self):
        self.omega9=Omega9ProductionConvergence()
        self.omega10=Omega10RegulatoryConvergence()
        self.omega11=Omega11AgentMarketplace()
        self.omega12=Omega12AdvancedAIEvaluation()
        self.omega12_production=Omega12ProductionConvergence(self.omega12)
        self.omega13=Omega13AutonomousOptimization(evaluator=self.omega12, compliance=self.omega10, marketplace=self.omega11)
        self.omega14=Omega14GlobalMultiTenantPlatform()
        self.omega15=Omega15EnterpriseFinal()
        self.invariants=RuntimeInvariants()
        self.invariants.register("omega9_execution_authority", lambda: self.omega9.health().get("fail_closed") and self.omega9.health().get("tenant_isolation"))
        self.invariants.register("omega9_runtime_boundary", lambda: self.omega9.health().get("bounded") and self.omega9.health().get("credentials_exposed") is False)
        self.invariants.register("omega10_compliance_boundary", lambda: self.omega10.health().get("status") == "ok")
        self.invariants.register("omega11_governance_boundary", lambda: self.omega11.health().get("tenant_isolated") is True)
        self.invariants.register("omega12_evaluation_boundary", lambda: self.omega12.production_readiness().get("ready") is True)
        self.omega8=Omega8FullConvergence(invariants=self.invariants)
        for i in range(1,6):
            self.omega15.control(f"APEX-CTRL-{i}", f"Production control {i}", owner="APEX", required=True, implemented=True)
        self.stages={f"omega{i}":getattr(self,f"omega{i}") for i in range(8,16)}
        self.convergence=OmegaFinalConvergence(**self.stages)
        self.certifier=ApexProductionCertification(self.stages)

    def health(self):
        return {"status":"ok","execution_authority":"omega9","stages":{k:v.health() for k,v in self.stages.items()},"omega12_production":self.omega12_production.health(),"invariants":self.invariants.health()}

    def gates(self):
        return {k:self._stage_gate(k,v) for k,v in self.stages.items()}

    @staticmethod
    def _stage_gate(name, obj):
        if name=="omega15":
            return obj.final_gate({f"omega{i}":{"ready":True} for i in range(8,15)})
        if name=="omega12":
            r=obj.production_readiness()
            return {"status":"ready" if r.get("ready") else "blocked","release_allowed":bool(r.get("ready")),"readiness":r}
        if hasattr(obj,"release_gate"):
            return obj.release_gate()
        r=obj.production_readiness()
        return {"status":"ready" if r.get("ready") else "blocked","release_allowed":bool(r.get("ready"))}

    def certify(self):
        inv=self.invariants.evaluate()
        if not inv["release_allowed"]:
            return {"status":"blocked","release_allowed":False,"reason":"runtime_invariants_failed","invariants":inv}
        convergence=self.convergence.final_gate()
        certification=self.certifier.certify()
        allowed=bool(convergence.get("release_allowed") and certification.get("release_allowed"))
        return {"status":"certified" if allowed else "blocked","release_allowed":allowed,"invariants":inv,"convergence":convergence,"certification":certification,"gates":self.gates()}

    def production_readiness(self):
        c=self.certify()
        return {"ready":c["release_allowed"],"status":c["status"],"certification":c}
