from src.core.omega10_regulatory_convergence import Omega10RegulatoryConvergence

def test_all_40_capabilities():
    x=Omega10RegulatoryConvergence(); assert len(x.CAPABILITIES)==40; assert set(x.CAPABILITIES)==set(range(1,41))

def test_source_ingestion_and_normalization():
    x=Omega10RegulatoryConvergence(); x.register_source('S1','Official','Authority','ZA'); r=x.ingest('t','w','S1','Reg','text'); assert r['status']=='accepted'; assert x.normalize(' a  b ')['content']=='a b'

def test_regulatory_lifecycle_and_assessment():
    x=Omega10RegulatoryConvergence(); rid=x.regulatory.register_regulation('t','w','Reg','ZA',version='1')['regulation_id']; x.regulatory.add_applicability_rule('t','w',rid,'sector','eq','finance'); x.extract_obligations('t','w',rid,[{'title':'Control','priority':'high'}]); a=x.assess('t','w',rid,{'sector':'finance'},{'c1':True,'c2':False}); assert a['applicable'] and a['score']==50.0

def test_controls_cases_alerts_and_approval():
    x=Omega10RegulatoryConvergence(); rid=x.regulatory.register_regulation('t','w','Reg','ZA')['regulation_id']; o=x.extract_obligations('t','w',rid,[{'title':'Control'}])['created'][0]['obligation_id']; assert x.map_control('t','w',o,'C1')['control_id']=='C1'; case=x.case('t','w','finding'); assert x.sla(case['case_id'],'2099-01-01')['status']=='active'; assert x.approval('t','w','D',True,'A')['status']=='approved'; assert x.alert('t','w','CH')['status']=='pending'

def test_provenance_conflict_confidence_and_freshness():
    x=Omega10RegulatoryConvergence(); assert x.provenance('s','1','h','d')['traceable']; assert x.contradictions([{'topic':'a','position':'x'},{'topic':'a','position':'y'}])['status']=='conflicting'; assert x.confidence(1,1,1)['status']=='high'; assert x.freshness('2099-01-01T00:00:00+00:00')['status']=='fresh'

def test_security_multijurisdiction_and_simulation():
    x=Omega10RegulatoryConvergence(); assert x.multi_jurisdiction(['ZA','BW'],{'jurisdiction':'ZA'})['status']=='applicable'; assert x.simulate('t','w','c',{'a':False})['projected_gaps']==['a']

def test_ai_and_release_gate():
    x=Omega10RegulatoryConvergence(); assert x.evaluate_ai([{'id':'1','source':'official','evidence':['e']}])['status']=='pass'; assert x.release_gate()['release_allowed']; assert x.production_readiness()['status']=='ready'
