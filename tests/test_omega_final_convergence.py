from src.core.omega_final_convergence import OmegaFinalConvergence
from src.core.omega13_autonomous_optimization import Omega13AutonomousOptimization
from src.core.omega14_global_multitenant import Omega14GlobalMultiTenantPlatform
from src.core.omega15_enterprise_final import Omega15EnterpriseFinal

class Gate:
    def release_gate(self): return {"release_allowed":True,"status":"ready"}

def test_final_convergence_blocks_missing_stages():
    c=OmegaFinalConvergence(omega13=Omega13AutonomousOptimization())
    assert c.final_gate()["release_allowed"] is False

def test_final_convergence_all_stages():
    c=OmegaFinalConvergence(omega8=Gate(),omega9=Gate(),omega10=Gate(),omega11=Gate(),
        omega12=Gate(),omega13=Omega13AutonomousOptimization(),
        omega14=Omega14GlobalMultiTenantPlatform(),omega15=Omega15EnterpriseFinal())
    g=c.final_gate()
    assert g["release_allowed"] is True
    assert c.production_readiness()["ready"] is True
    assert len(c.layer_status())==8
