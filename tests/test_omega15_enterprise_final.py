from src.core.omega15_enterprise_final import Omega15EnterpriseFinal
def test_omega15():
 o=Omega15EnterpriseFinal(); assert not o.final_gate({})["release_allowed"]; o.control("c","architecture"); layers={x:{"ready":True} for x in o.required_stages}; assert o.final_gate(layers)["release_allowed"]; assert len(o.layer_status())==40
