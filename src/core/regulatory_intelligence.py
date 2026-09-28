from __future__ import annotations
import os, sqlite3, uuid
from datetime import datetime, timezone

class RegulatoryIntelligence:
    """Tenant-scoped regulatory source, applicability, obligation and change intelligence."""
    STATUSES={"draft","active","superseded","repealed"}
    PRIORITIES={"low","medium","high","critical"}

    def __init__(self,db_path=None):
        self.db_path=db_path or os.path.join("data","regulatory_intelligence.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        with self.db() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS regulations(
                regulation_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,title TEXT,jurisdiction TEXT,
                industry TEXT,authority TEXT,version TEXT,effective_from TEXT,effective_to TEXT,status TEXT,
                source_id TEXT,checksum TEXT,created_at TEXT,updated_at TEXT)""")
            c.execute("""CREATE TABLE IF NOT EXISTS applicability(
                rule_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,regulation_id TEXT,
                field TEXT,operator TEXT,value TEXT,required INTEGER)""")
            c.execute("""CREATE TABLE IF NOT EXISTS obligations(
                obligation_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,regulation_id TEXT,
                title TEXT,description TEXT,frequency TEXT,deadline TEXT,priority TEXT,status TEXT,version TEXT,created_at TEXT)""")
            c.execute("""CREATE TABLE IF NOT EXISTS changes(
                change_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,regulation_id TEXT,
                change_type TEXT,old_version TEXT,new_version TEXT,impact TEXT,detected_at TEXT,reviewed INTEGER)""")
            c.execute("""CREATE TABLE IF NOT EXISTS obligation_controls(
                link_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,obligation_id TEXT,
                control_id TEXT,required INTEGER,created_at TEXT)""")
            c.execute("""CREATE TABLE IF NOT EXISTS evidence_requirements(
                requirement_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,obligation_id TEXT,
                evidence_type TEXT,description TEXT,frequency TEXT,required INTEGER,created_at TEXT)""")
            c.execute("""CREATE TABLE IF NOT EXISTS assessments(
                assessment_id TEXT PRIMARY KEY,tenant_id TEXT,workspace_id TEXT,regulation_id TEXT,
                applicable INTEGER,profile_json TEXT,assessed_at TEXT)""")

    def db(self):
        c = sqlite3.connect(self.db_path, timeout=15.0)
        c.execute("PRAGMA busy_timeout=15000")
        return c
    def scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)
    def _id(self,p): return p+"-"+uuid.uuid4().hex[:12].upper()
    def _now(self): return datetime.now(timezone.utc).isoformat()

    def register_regulation(self,t,w,title,jurisdiction,industry="",authority="",version="1.0",
                            effective_from=None,effective_to=None,status="active",source_id="",checksum=""):
        t,w=self.scope(t,w)
        if status not in self.STATUSES:return {"allowed":False,"reason":"invalid_status"}
        if not str(title).strip() or not str(jurisdiction).strip():return {"allowed":False,"reason":"regulation_identity_required"}
        rid=self._id("REG");n=self._now()
        with self.db() as c:
            c.execute("INSERT INTO regulations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (rid,t,w,title,jurisdiction,industry,authority,version,effective_from,effective_to,status,source_id,checksum,n,n))
        return {"regulation_id":rid,"status":status,"version":version}

    def add_applicability_rule(self,t,w,regulation_id,field,operator,value,required=True):
        t,w=self.scope(t,w);rule=self._id("RULE")
        with self.db() as c:
            if not c.execute("SELECT 1 FROM regulations WHERE regulation_id=? AND tenant_id=? AND workspace_id=?",(regulation_id,t,w)).fetchone():
                return {"allowed":False,"reason":"regulation_not_found"}
            c.execute("INSERT INTO applicability VALUES(?,?,?,?,?,?,?,?)",(rule,t,w,regulation_id,field,operator,str(value),int(bool(required))))
        return {"rule_id":rule,"regulation_id":regulation_id}

    def assess_applicability(self,t,w,regulation_id,profile):
        import json
        t,w=self.scope(t,w)
        with self.db() as c:
            rules=c.execute("SELECT field,operator,value,required FROM applicability WHERE regulation_id=? AND tenant_id=? AND workspace_id=?",(regulation_id,t,w)).fetchall()
        results=[{"field":f,"operator":op,"required":bool(req),"expected":v,"actual":profile.get(f),"matched":self._compare(profile.get(f),op,v)} for f,op,v,req in rules]
        applicable=all(x["matched"] for x in results if x["required"])
        aid=self._id("ASM")
        with self.db() as c:
            c.execute("INSERT INTO assessments VALUES(?,?,?,?,?,?,?)",(aid,t,w,regulation_id,int(applicable),json.dumps(profile,default=str),self._now()))
        return {"assessment_id":aid,"regulation_id":regulation_id,"applicable":applicable,"rules":results}

    @staticmethod
    def _compare(actual,op,expected):
        if op=="eq":return str(actual)==expected
        if op=="neq":return str(actual)!=expected
        if op=="contains":return expected in (actual or "")
        if op=="in":return str(actual) in [x.strip() for x in expected.split(",")]
        try:
            a=float(actual);e=float(expected)
            return {"gt":a>e,"gte":a>=e,"lt":a<e,"lte":a<=e}.get(op,False)
        except (TypeError,ValueError):return False

    def add_obligation(self,t,w,regulation_id,title,description="",frequency="annual",deadline="",priority="medium",status="open",version="1.0"):
        t,w=self.scope(t,w)
        if priority not in self.PRIORITIES:return {"allowed":False,"reason":"invalid_priority"}
        oid=self._id("OBL");n=self._now()
        with self.db() as c:
            if not c.execute("SELECT 1 FROM regulations WHERE regulation_id=? AND tenant_id=? AND workspace_id=?",(regulation_id,t,w)).fetchone():
                return {"allowed":False,"reason":"regulation_not_found"}
            c.execute("INSERT INTO obligations VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(oid,t,w,regulation_id,title,description,frequency,deadline,priority,status,version,n))
        return {"obligation_id":oid,"regulation_id":regulation_id,"priority":priority}

    def link_control(self,t,w,obligation_id,control_id,required=True):
        t,w=self.scope(t,w);lid=self._id("CTL")
        with self.db() as c:
            if not c.execute("SELECT 1 FROM obligations WHERE obligation_id=? AND tenant_id=? AND workspace_id=?",(obligation_id,t,w)).fetchone():
                return {"allowed":False,"reason":"obligation_not_found"}
            c.execute("INSERT INTO obligation_controls VALUES(?,?,?,?,?,?,?)",(lid,t,w,obligation_id,control_id,int(bool(required)),self._now()))
        return {"link_id":lid,"obligation_id":obligation_id,"control_id":control_id}

    def add_evidence_requirement(self,t,w,obligation_id,evidence_type,description="",frequency="annual",required=True):
        t,w=self.scope(t,w);rid=self._id("EVR")
        with self.db() as c:
            if not c.execute("SELECT 1 FROM obligations WHERE obligation_id=? AND tenant_id=? AND workspace_id=?",(obligation_id,t,w)).fetchone():
                return {"allowed":False,"reason":"obligation_not_found"}
            c.execute("INSERT INTO evidence_requirements VALUES(?,?,?,?,?,?,?,?,?)",(rid,t,w,obligation_id,evidence_type,description,frequency,int(bool(required)),self._now()))
        return {"requirement_id":rid,"obligation_id":obligation_id}

    def record_change(self,t,w,regulation_id,change_type,old_version,new_version,impact="medium"):
        t,w=self.scope(t,w);cid=self._id("CHG")
        if impact not in self.PRIORITIES:return {"allowed":False,"reason":"invalid_impact"}
        with self.db() as c:
            if not c.execute("SELECT 1 FROM regulations WHERE regulation_id=? AND tenant_id=? AND workspace_id=?",(regulation_id,t,w)).fetchone():
                return {"allowed":False,"reason":"regulation_not_found"}
            c.execute("INSERT INTO changes VALUES(?,?,?,?,?,?,?,?,?,?)",(cid,t,w,regulation_id,change_type,old_version,new_version,impact,self._now(),0))
            c.execute("UPDATE regulations SET version=?,updated_at=? WHERE regulation_id=? AND tenant_id=? AND workspace_id=?",(new_version,self._now(),regulation_id,t,w))
        return {"change_id":cid,"regulation_id":regulation_id,"impact":impact}

    def impact_assessment(self,t,w,regulation_id,profile):
        assessment=self.assess_applicability(t,w,regulation_id,profile)
        if not assessment["applicable"]:return {"applicable":False,"obligations":[],"controls":[],"evidence_requirements":[],"assessment":assessment}
        t,w=self.scope(t,w)
        with self.db() as c:
            obs=c.execute("SELECT obligation_id,title,priority,status,deadline FROM obligations WHERE regulation_id=? AND tenant_id=? AND workspace_id=?",(regulation_id,t,w)).fetchall()
            ids=[x[0] for x in obs]
            controls=[];evidence=[]
            for oid in ids:
                controls += c.execute("SELECT obligation_id,control_id,required FROM obligation_controls WHERE obligation_id=? AND tenant_id=? AND workspace_id=?",(oid,t,w)).fetchall()
                evidence += c.execute("SELECT obligation_id,evidence_type,description,frequency,required FROM evidence_requirements WHERE obligation_id=? AND tenant_id=? AND workspace_id=?",(oid,t,w)).fetchall()
        return {"applicable":True,"assessment":assessment,
                "obligations":[dict(zip(["obligation_id","title","priority","status","deadline"],x)) for x in obs],
                "controls":[dict(zip(["obligation_id","control_id","required"],x)) for x in controls],
                "evidence_requirements":[dict(zip(["obligation_id","evidence_type","description","frequency","required"],x)) for x in evidence]}

    def detect_change(self,t,w,regulation_id,new_version,change_type="version_update",impact="medium",checksum=""):
        t,w=self.scope(t,w)
        if impact not in self.PRIORITIES:return {"allowed":False,"reason":"invalid_impact"}
        with self.db() as c:
            row=c.execute("SELECT version,checksum FROM regulations WHERE regulation_id=? AND tenant_id=? AND workspace_id=?",(regulation_id,t,w)).fetchone()
        if not row:return {"allowed":False,"reason":"regulation_not_found"}
        old_version,old_checksum=row
        with self.db() as c:
            prior=c.execute("SELECT change_id FROM changes WHERE regulation_id=? AND tenant_id=? AND workspace_id=? AND new_version=? ORDER BY detected_at DESC LIMIT 1",(regulation_id,t,w,str(new_version))).fetchone()
        if prior:
            return {"changed":False,"reason":"version_already_processed","regulation_id":regulation_id,"change_id":prior[0]}
        if str(new_version)==str(old_version) and (not checksum or checksum==old_checksum):
            return {"changed":False,"reason":"no_change","regulation_id":regulation_id}
        change=self.record_change(t,w,regulation_id,change_type,old_version,new_version,impact)
        with self.db() as c:
            c.execute("UPDATE regulations SET checksum=?,updated_at=? WHERE regulation_id=? AND tenant_id=? AND workspace_id=?",(checksum or old_checksum,self._now(),regulation_id,t,w))
        return {"changed":True,"change":change,"old_version":old_version,"new_version":new_version,"impact":impact}

    def affected_obligations(self,t,w,regulation_id):
        t,w=self.scope(t,w)
        with self.db() as c:
            rows=c.execute("SELECT obligation_id,title,priority,status,version FROM obligations WHERE regulation_id=? AND tenant_id=? AND workspace_id=? ORDER BY priority DESC,title",(regulation_id,t,w)).fetchall()
        return [dict(zip(["obligation_id","title","priority","status","version"],r)) for r in rows]

    def compare_obligations(self,t,w,regulation_id,proposed):
        """Compare a supplied regulatory obligation set against the stored version by stable title."""
        current={x["title"]:x for x in self.affected_obligations(t,w,regulation_id)}
        incoming={str(x.get("title","")):x for x in (proposed or []) if str(x.get("title","")).strip()}
        added=[]; removed=[]; changed=[]
        for title,item in incoming.items():
            if title not in current:
                added.append(item)
                continue
            old=current[title]
            fields=("priority","status","version")
            delta={k:{"old":old.get(k),"new":item.get(k)} for k in fields if item.get(k) is not None and str(item.get(k))!=str(old.get(k))}
            if delta: changed.append({"title":title,"obligation_id":old["obligation_id"],"changes":delta})
        for title,old in current.items():
            if title not in incoming: removed.append(old)
        return {"added":added,"removed":removed,"changed":changed,"total_affected":len(added)+len(removed)+len(changed)}

    def compare_controls_and_evidence(self,t,w,regulation_id,proposed):
        """Detect control/evidence additions and removals carried by proposed obligations."""
        current={x["title"]:x for x in self.affected_obligations(t,w,regulation_id)}
        added_controls=[]; removed_controls=[]; added_evidence=[]; removed_evidence=[]
        with self.db() as c:
            for title,old in current.items():
                controls={r[0] for r in c.execute("SELECT control_id FROM obligation_controls WHERE obligation_id=? AND tenant_id=? AND workspace_id=?",(old["obligation_id"],t,w)).fetchall()}
                evidence={r[0] for r in c.execute("SELECT evidence_type FROM evidence_requirements WHERE obligation_id=? AND tenant_id=? AND workspace_id=?",(old["obligation_id"],t,w)).fetchall()}
                incoming=next((x for x in (proposed or []) if str(x.get("title"))==title),None)
                if not incoming: continue
                inc_controls={str(x.get("control_id")) for x in incoming.get("controls",[]) if x.get("control_id")}
                inc_evidence={str(x.get("evidence_type")) for x in incoming.get("evidence_requirements",[]) if x.get("evidence_type")}
                added_controls += [{"obligation_id":old["obligation_id"],"control_id":x} for x in inc_controls-controls]
                removed_controls += [{"obligation_id":old["obligation_id"],"control_id":x} for x in controls-inc_controls]
                added_evidence += [{"obligation_id":old["obligation_id"],"evidence_type":x} for x in inc_evidence-evidence]
                removed_evidence += [{"obligation_id":old["obligation_id"],"evidence_type":x} for x in evidence-inc_evidence]
        return {"added_controls":added_controls,"removed_controls":removed_controls,"added_evidence":added_evidence,"removed_evidence":removed_evidence}

    def apply_obligation_diff(self,t,w,regulation_id,version,diff):
        t,w=self.scope(t,w);created=[];closed=[]
        for item in diff.get("added",[]):
            result=self.add_obligation(t,w,regulation_id,item["title"],item.get("description",""),item.get("frequency","annual"),item.get("deadline",""),item.get("priority","medium"),item.get("status","open"),item.get("version",version))
            if result.get("obligation_id"): created.append(result)
        for item in diff.get("removed",[]):
            with self.db() as c:
                c.execute("UPDATE obligations SET status=?,version=? WHERE obligation_id=? AND tenant_id=? AND workspace_id=?",("superseded",version,item["obligation_id"],t,w))
            closed.append(item["obligation_id"])
        updated=[]
        for item in diff.get("changed",[]):
            values=item.get("changes",{})
            priority=values.get("priority",{}).get("new")
            status=values.get("status",{}).get("new")
            new_ver=values.get("version",{}).get("new") or version
            if priority or status or new_ver:
                with self.db() as c:
                    c.execute("UPDATE obligations SET priority=COALESCE(?,priority),status=COALESCE(?,status),version=? WHERE obligation_id=? AND tenant_id=? AND workspace_id=?",(priority,status,new_ver,item["obligation_id"],t,w))
                updated.append(item["obligation_id"])
        return {"created":created,"superseded":closed,"updated":updated}

    def apply_control_evidence_diff(self,t,w,regulation_id,diff):
        """Apply regulatory control/evidence changes idempotently while preserving requirement history."""
        t,w=self.scope(t,w); linked=[]; retired=[]; evidence_added=[]; evidence_retired=[]
        with self.db() as c:
            for item in diff.get("added_controls",[]):
                exists=c.execute("SELECT 1 FROM obligation_controls WHERE obligation_id=? AND control_id=? AND tenant_id=? AND workspace_id=?",(item["obligation_id"],item["control_id"],t,w)).fetchone()
                if not exists:
                    lid=self._id("CTL")
                    c.execute("INSERT INTO obligation_controls VALUES(?,?,?,?,?,?,?)",(lid,t,w,item["obligation_id"],item["control_id"],1,self._now()))
                    linked.append({"link_id":lid,"obligation_id":item["obligation_id"],"control_id":item["control_id"]})
            for item in diff.get("removed_controls",[]):
                cur=c.execute("UPDATE obligation_controls SET required=0 WHERE obligation_id=? AND control_id=? AND tenant_id=? AND workspace_id=?",(item["obligation_id"],item["control_id"],t,w))
                if cur.rowcount: retired.append(item)
            for item in diff.get("added_evidence",[]):
                exists=c.execute("SELECT 1 FROM evidence_requirements WHERE obligation_id=? AND evidence_type=? AND tenant_id=? AND workspace_id=? AND required=1",(item["obligation_id"],item["evidence_type"],t,w)).fetchone()
                if not exists:
                    rid=self._id("EVR")
                    c.execute("INSERT INTO evidence_requirements VALUES(?,?,?,?,?,?,?,?,?)",(rid,t,w,item["obligation_id"],item["evidence_type"],"","annual",1,self._now()))
                    evidence_added.append({"requirement_id":rid,"obligation_id":item["obligation_id"]})
            for item in diff.get("removed_evidence",[]):
                cur=c.execute("UPDATE evidence_requirements SET required=0 WHERE obligation_id=? AND evidence_type=? AND tenant_id=? AND workspace_id=? AND required=1",(item["obligation_id"],item["evidence_type"],t,w))
                if cur.rowcount: evidence_retired.append(item)
        return {"controls_linked":linked,"controls_retired":retired,"evidence_added":evidence_added,"evidence_retired":evidence_retired}

    def snapshot(self,t,w):
        t,w=self.scope(t,w)
        with self.db() as c:
            regs=c.execute("SELECT regulation_id,title,jurisdiction,industry,authority,version,effective_from,effective_to,status,source_id FROM regulations WHERE tenant_id=? AND workspace_id=? ORDER BY title",(t,w)).fetchall()
            obs=c.execute("SELECT obligation_id,regulation_id,title,frequency,deadline,priority,status,version FROM obligations WHERE tenant_id=? AND workspace_id=? ORDER BY priority DESC,title",(t,w)).fetchall()
            changes=c.execute("SELECT change_id,regulation_id,change_type,old_version,new_version,impact,detected_at,reviewed FROM changes WHERE tenant_id=? AND workspace_id=? ORDER BY detected_at DESC",(t,w)).fetchall()
            req=c.execute("SELECT requirement_id,obligation_id,evidence_type,description,frequency,required FROM evidence_requirements WHERE tenant_id=? AND workspace_id=?",(t,w)).fetchall()
        return {"tenant_id":t,"workspace_id":w,
                "regulations":[dict(zip(["regulation_id","title","jurisdiction","industry","authority","version","effective_from","effective_to","status","source_id"],r)) for r in regs],
                "obligations":[dict(zip(["obligation_id","regulation_id","title","frequency","deadline","priority","status","version"],r)) for r in obs],
                "changes":[dict(zip(["change_id","regulation_id","change_type","old_version","new_version","impact","detected_at","reviewed"],r)) for r in changes],
                "evidence_requirements":[dict(zip(["requirement_id","obligation_id","evidence_type","description","frequency","required"],r)) for r in req]}

    def health(self):
        with self.db() as c:
            regs=c.execute("SELECT COUNT(*) FROM regulations").fetchone()[0];obs=c.execute("SELECT COUNT(*) FROM obligations").fetchone()[0]
            rules=c.execute("SELECT COUNT(*) FROM applicability").fetchone()[0];changes=c.execute("SELECT COUNT(*) FROM changes").fetchone()[0]
            links=c.execute("SELECT COUNT(*) FROM obligation_controls").fetchone()[0];req=c.execute("SELECT COUNT(*) FROM evidence_requirements").fetchone()[0]
        return {"status":"ok","regulations":regs,"obligations":obs,"applicability_rules":rules,"changes":changes,"control_links":links,"evidence_requirements":req,"tenant_scoped":True,"credentials_exposed":False}
