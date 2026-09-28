from src.core.apex_production_certification import ApexProductionCertification
class Stage:
    def health(self): return {"status":"ok"}
    def release_gate(self): return {"release_allowed":True}
def test_apex_certification_fail_closed():
    assert ApexProductionCertification().certify()["release_allowed"] is False
def test_apex_certification_all_stages():
    c=ApexProductionCertification({f"omega{i}":Stage() for i in range(8,16)}); assert c.certify()["release_allowed"] is True; assert c.health()["required_stages"]==8
