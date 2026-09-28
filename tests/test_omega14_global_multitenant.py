from src.core.omega14_global_multitenant import Omega14GlobalMultiTenantPlatform
def test_omega14():
 o=Omega14GlobalMultiTenantPlatform(); o.register_region("za","ZA",["ZA"]); assert o.register_tenant("t","T",region_id="za")["status"]=="active"; o.workspace("t","w"); assert o.route("t","w")["status"]=="routed"; assert len(o.layer_status())==40
def test_omega14_failover():
 o=Omega14GlobalMultiTenantPlatform(); o.register_region("a","A"); o.register_region("b","B"); o.register_tenant("t","T",region_id="a"); o.workspace("t","w"); assert o.failover("t","w","b")["status"]=="blocked"; assert o.failover("t","w","b",approved=True)["status"]=="failed_over"
