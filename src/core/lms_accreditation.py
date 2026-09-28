from __future__ import annotations
import json, os, sqlite3, uuid
from datetime import datetime, timezone
from .event_bus import EventBus


def _now():
    return datetime.now(timezone.utc).isoformat()


def _id(prefix):
    return f"ACC-{prefix}-{uuid.uuid4().hex[:12].upper()}"


class LMSAccreditation:
    """Qualification/accreditation control plane for governed training delivery.

    Keeps accreditation requirements, assessor/moderator controls, learner evidence,
    moderation, transcript and certificate-verification state separate from course content.
    """
    STATES={"draft","submitted","under_review","approved","active","expired","rejected","closed"}
    REVIEW_STATES={"pending","approved","rejected"}

    def __init__(self, training=None, db_path=None):
        self.training=training
        self.db_path=db_path or os.path.join("data","lms_accreditation.sqlite3")
        os.makedirs(os.path.dirname(self.db_path) or ".",exist_ok=True)
        self.events=EventBus(os.path.join(os.path.dirname(self.db_path) or ".","event_bus.sqlite3"))
        self._init()

    def _db(self):
        c=sqlite3.connect(self.db_path); c.row_factory=sqlite3.Row; return c

    def _init(self):
        with self._db() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS qualifications(
              qualification_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              name TEXT NOT NULL, code TEXT, authority TEXT, nqf_level TEXT, credits REAL,
              status TEXT NOT NULL DEFAULT 'draft', version TEXT NOT NULL DEFAULT '1.0',
              effective_from TEXT, effective_to TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS programme_mappings(
              mapping_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              qualification_id TEXT NOT NULL, programme_id TEXT NOT NULL, coverage_pct REAL NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'draft', mapped_at TEXT NOT NULL,
              UNIQUE(qualification_id,programme_id));
            CREATE TABLE IF NOT EXISTS requirements(
              requirement_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              qualification_id TEXT NOT NULL, requirement_type TEXT NOT NULL, name TEXT NOT NULL,
              target REAL, unit TEXT, mandatory INTEGER NOT NULL DEFAULT 1, evidence_type TEXT,
              created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS accreditation_applications(
              application_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              qualification_id TEXT NOT NULL, authority TEXT, reference_no TEXT, status TEXT NOT NULL DEFAULT 'draft',
              submitted_at TEXT, decided_at TEXT, decision_notes TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS assessor_assignments(
              assignment_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              course_id TEXT, cohort_id TEXT, assessor_id TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'assessor',
              status TEXT NOT NULL DEFAULT 'active', assigned_at TEXT NOT NULL, released_at TEXT);
            CREATE TABLE IF NOT EXISTS evidence_portfolios(
              portfolio_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              learner_id TEXT NOT NULL, qualification_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
              submitted_at TEXT, reviewed_at TEXT, reviewer_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              UNIQUE(learner_id,qualification_id));
            CREATE TABLE IF NOT EXISTS evidence_items(
              evidence_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              portfolio_id TEXT NOT NULL, requirement_id TEXT, evidence_type TEXT NOT NULL, title TEXT NOT NULL,
              source_ref TEXT, verified INTEGER NOT NULL DEFAULT 0, verified_by TEXT, verified_at TEXT, metadata_json TEXT,
              created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS moderation_reviews(
              moderation_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              learner_id TEXT, course_id TEXT, assessment_id TEXT, assessor_id TEXT, moderator_id TEXT,
              status TEXT NOT NULL DEFAULT 'pending', findings TEXT, decided_at TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS certificates(
              verification_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              learner_id TEXT NOT NULL, qualification_id TEXT NOT NULL, certificate_no TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'valid', issued_at TEXT, revoked_at TEXT, verification_hash TEXT,
              created_at TEXT NOT NULL, UNIQUE(certificate_no));
            """)

    def _scope(self,t,w):
        if not t or not w: raise ValueError("tenant_id_and_workspace_id_required")
        return str(t),str(w)

    def register_qualification(self,t,w,name,code="",authority="",nqf_level="",credits=0,status="draft",version="1.0",effective_from=None,effective_to=None):
        t,w=self._scope(t,w)
        if status not in self.STATES: raise ValueError("invalid_qualification_status")
        qid=_id("QUAL"); ts=_now()
        with self._db() as c:
            c.execute("INSERT INTO qualifications VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(qid,t,w,name,code,authority,nqf_level,float(credits),status,version,effective_from,effective_to,ts,ts))
        return self.get_qualification(t,w,qid)

    def get_qualification(self,t,w,qualification_id):
        t,w=self._scope(t,w)
        with self._db() as c:
            q=c.execute("SELECT * FROM qualifications WHERE qualification_id=? AND tenant_id=? AND workspace_id=?",(qualification_id,t,w)).fetchone()
            if not q:return None
            q=dict(q)
            q["requirements"]=[dict(x) for x in c.execute("SELECT * FROM requirements WHERE qualification_id=? AND tenant_id=? AND workspace_id=? ORDER BY name",(qualification_id,t,w))]
            q["programme_mappings"]=[dict(x) for x in c.execute("SELECT * FROM programme_mappings WHERE qualification_id=? AND tenant_id=? AND workspace_id=?",(qualification_id,t,w))]
        return q

    def map_programme(self,t,w,qualification_id,programme_id,coverage_pct=0,status="draft"):
        t,w=self._scope(t,w); coverage=max(0,min(100,float(coverage_pct)))
        mid=_id("MAP"); ts=_now()
        with self._db() as c:
            c.execute("INSERT INTO programme_mappings VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(qualification_id,programme_id) DO UPDATE SET coverage_pct=excluded.coverage_pct,status=excluded.status,mapped_at=excluded.mapped_at",(mid,t,w,qualification_id,programme_id,coverage,status,ts))
            row=c.execute("SELECT * FROM programme_mappings WHERE qualification_id=? AND programme_id=?",(qualification_id,programme_id)).fetchone()
        return dict(row)

    def add_requirement(self,t,w,qualification_id,requirement_type,name,target=None,unit="",mandatory=True,evidence_type=""):
        t,w=self._scope(t,w); rid=_id("REQ")
        with self._db() as c:
            c.execute("INSERT INTO requirements VALUES(?,?,?,?,?,?,?,?,?,?,?)",(rid,t,w,qualification_id,requirement_type,name,target,unit,int(bool(mandatory)),evidence_type,_now()))
        return dict(c.execute("SELECT * FROM requirements WHERE requirement_id=?",(rid,)).fetchone())

    def submit_accreditation(self,t,w,qualification_id,authority="",reference_no=""):
        t,w=self._scope(t,w); aid=_id("APP"); ts=_now()
        with self._db() as c:
            c.execute("INSERT INTO accreditation_applications VALUES(?,?,?,?,?,?,?,?,?,?,?)",(aid,t,w,qualification_id,authority,reference_no,"submitted",ts,None,None,ts))
        self.events.publish("lms.accreditation.submitted",t,w,"system","qualification",qualification_id,aid,{"authority":authority,"reference_no":reference_no},idempotency_key=f"accreditation-submitted:{aid}")
        return self.get_application(t,w,aid)

    def get_application(self,t,w,application_id):
        t,w=self._scope(t,w)
        with self._db() as c:
            row=c.execute("SELECT * FROM accreditation_applications WHERE application_id=? AND tenant_id=? AND workspace_id=?",(application_id,t,w)).fetchone()
        return dict(row) if row else None

    def decide_accreditation(self,t,w,application_id,status,actor_id,notes=""):
        t,w=self._scope(t,w)
        if status not in {"approved","rejected","under_review"}: raise ValueError("invalid_accreditation_decision")
        with self._db() as c:
            row=c.execute("SELECT * FROM accreditation_applications WHERE application_id=? AND tenant_id=? AND workspace_id=?",(application_id,t,w)).fetchone()
            if not row: raise ValueError("application_not_found")
            decided=_now() if status in {"approved","rejected"} else None
            c.execute("UPDATE accreditation_applications SET status=?,decided_at=?,decision_notes=? WHERE application_id=?",(status,decided,notes,application_id))
            if status=="approved": c.execute("UPDATE qualifications SET status='active',updated_at=? WHERE qualification_id=? AND tenant_id=? AND workspace_id=?",(_now(),row["qualification_id"],t,w))
        self.events.publish("lms.accreditation.decided",t,w,str(actor_id),"qualification",row["qualification_id"],application_id,{"status":status,"notes":notes})
        return self.get_application(t,w,application_id)

    def assign_assessor(self,t,w,assessor_id,course_id=None,cohort_id=None,role="assessor"):
        t,w=self._scope(t,w); aid=_id("ASSESSOR"); ts=_now()
        with self._db() as c:
            c.execute("INSERT INTO assessor_assignments VALUES(?,?,?,?,?,?,?,?,?)",(aid,t,w,course_id,cohort_id,assessor_id,role,"active",ts,None))
        return dict(c.execute("SELECT * FROM assessor_assignments WHERE assignment_id=?",(aid,)).fetchone())

    def create_portfolio(self,t,w,learner_id,qualification_id):
        t,w=self._scope(t,w); pid=_id("PORT"); ts=_now()
        with self._db() as c:
            c.execute("INSERT INTO evidence_portfolios VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(learner_id,qualification_id) DO UPDATE SET updated_at=excluded.updated_at",(pid,t,w,learner_id,qualification_id,"draft",None,None,None,ts,ts))
            row=c.execute("SELECT * FROM evidence_portfolios WHERE learner_id=? AND qualification_id=? AND tenant_id=? AND workspace_id=?",(learner_id,qualification_id,t,w)).fetchone()
        return dict(row)

    def add_evidence(self,t,w,portfolio_id,evidence_type,title,source_ref="",requirement_id=None,metadata=None):
        t,w=self._scope(t,w); eid=_id("EVID"); ts=_now()
        with self._db() as c:
            c.execute("INSERT INTO evidence_items VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(eid,t,w,portfolio_id,requirement_id,evidence_type,title,source_ref,0,None,None,json.dumps(metadata or {},sort_keys=True),ts))
        return dict(c.execute("SELECT * FROM evidence_items WHERE evidence_id=?",(eid,)).fetchone())

    def verify_evidence(self,t,w,evidence_id,verified,reviewer_id):
        t,w=self._scope(t,w)
        with self._db() as c:
            row=c.execute("SELECT * FROM evidence_items WHERE evidence_id=? AND tenant_id=? AND workspace_id=?",(evidence_id,t,w)).fetchone()
            if not row: raise ValueError("evidence_not_found")
            c.execute("UPDATE evidence_items SET verified=?,verified_by=?,verified_at=? WHERE evidence_id=?",(int(bool(verified)),reviewer_id,_now() if verified else None,evidence_id))
            return dict(c.execute("SELECT * FROM evidence_items WHERE evidence_id=?",(evidence_id,)).fetchone())

    def submit_portfolio(self,t,w,portfolio_id):
        t,w=self._scope(t,w)
        with self._db() as c:
            row=c.execute("SELECT * FROM evidence_portfolios WHERE portfolio_id=? AND tenant_id=? AND workspace_id=?",(portfolio_id,t,w)).fetchone()
            if not row: raise ValueError("portfolio_not_found")
            missing=c.execute("SELECT COUNT(*) n FROM evidence_items WHERE portfolio_id=? AND tenant_id=? AND workspace_id=? AND verified=0",(portfolio_id,t,w)).fetchone()["n"]
            c.execute("UPDATE evidence_portfolios SET status='submitted',submitted_at=?,updated_at=? WHERE portfolio_id=?",(_now(),_now(),portfolio_id))
        return {"portfolio_id":portfolio_id,"status":"submitted","unverified_evidence":missing}

    def moderate_assessment(self,t,w,learner_id=None,course_id=None,assessment_id=None,assessor_id=None,moderator_id=None):
        t,w=self._scope(t,w); mid=_id("MOD")
        with self._db() as c:
            c.execute("INSERT INTO moderation_reviews VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(mid,t,w,learner_id,course_id,assessment_id,assessor_id,moderator_id,"pending",None,None,_now()))
        return dict(c.execute("SELECT * FROM moderation_reviews WHERE moderation_id=?",(mid,)).fetchone())

    def decide_moderation(self,t,w,moderation_id,status,moderator_id,findings=""):
        t,w=self._scope(t,w)
        if status not in self.REVIEW_STATES: raise ValueError("invalid_moderation_status")
        with self._db() as c:
            row=c.execute("SELECT * FROM moderation_reviews WHERE moderation_id=? AND tenant_id=? AND workspace_id=?",(moderation_id,t,w)).fetchone()
            if not row: raise ValueError("moderation_not_found")
            c.execute("UPDATE moderation_reviews SET status=?,moderator_id=?,findings=?,decided_at=? WHERE moderation_id=?",(status,moderator_id,findings,_now() if status!="pending" else None,moderation_id))
        with self._db() as c:
            return dict(c.execute("SELECT * FROM moderation_reviews WHERE moderation_id=?",(moderation_id,)).fetchone())

    def register_certificate(self,t,w,learner_id,qualification_id,certificate_no,verification_hash="",issued_at=None):
        t,w=self._scope(t,w); vid=_id("CERT"); ts=_now()
        with self._db() as c:
            c.execute("INSERT INTO certificates VALUES(?,?,?,?,?,?,?,?,?,?,?)",(vid,t,w,learner_id,qualification_id,certificate_no,"valid",issued_at or ts,None,verification_hash,ts))
        return self.verify_certificate(t,w,certificate_no)

    def verify_certificate(self,t,w,certificate_no):
        t,w=self._scope(t,w)
        with self._db() as c:
            row=c.execute("SELECT * FROM certificates WHERE certificate_no=? AND tenant_id=? AND workspace_id=?",(certificate_no,t,w)).fetchone()
        if not row:return {"valid":False,"reason":"certificate_not_found"}
        return {"valid":row["status"]=="valid","certificate":dict(row)}

    def revoke_certificate(self,t,w,certificate_no,reason=""):
        t,w=self._scope(t,w)
        with self._db() as c:
            row=c.execute("SELECT * FROM certificates WHERE certificate_no=? AND tenant_id=? AND workspace_id=?",(certificate_no,t,w)).fetchone()
            if not row: raise ValueError("certificate_not_found")
            c.execute("UPDATE certificates SET status='revoked',revoked_at=? WHERE certificate_no=?",(_now(),certificate_no))
        self.events.publish("lms.certificate.revoked",t,w,"system","certificate",certificate_no,row["verification_id"],{"reason":reason})
        return self.verify_certificate(t,w,certificate_no)

    def transcript(self,t,w,learner_id,qualification_id=None):
        t,w=self._scope(t,w)
        if not self.training: return {"learner_id":learner_id,"qualification_id":qualification_id,"courses":[],"certificates":[]}
        with self._db() as c:
            portfolios=[dict(x) for x in c.execute("SELECT * FROM evidence_portfolios WHERE learner_id=? AND tenant_id=? AND workspace_id=?",(learner_id,t,w))]
            certs=[dict(x) for x in c.execute("SELECT * FROM certificates WHERE learner_id=? AND tenant_id=? AND workspace_id=? AND status='valid'",(learner_id,t,w))]
        return {"learner_id":learner_id,"qualification_id":qualification_id,"portfolios":portfolios,"certificates":certs,"generated_at":_now()}

    def eligibility(self,t,w,learner_id,qualification_id):
        t,w=self._scope(t,w)
        with self._db() as c:
            req=[dict(x) for x in c.execute("SELECT * FROM requirements WHERE qualification_id=? AND tenant_id=? AND workspace_id=? AND mandatory=1",(qualification_id,t,w))]
            portfolio=c.execute("SELECT * FROM evidence_portfolios WHERE learner_id=? AND qualification_id=? AND tenant_id=? AND workspace_id=?",(learner_id,qualification_id,t,w)).fetchone()
            verified=0 if not portfolio else c.execute("SELECT COUNT(*) n FROM evidence_items WHERE portfolio_id=? AND verified=1",(portfolio["portfolio_id"],)).fetchone()["n"]
        required_evidence=sum(1 for r in req if r.get("evidence_type")); complete=required_evidence==0 or verified>=required_evidence
        return {"eligible":complete,"qualification_id":qualification_id,"learner_id":learner_id,"mandatory_requirements":len(req),"verified_evidence":verified,"required_evidence_types":required_evidence}

    def health(self):
        with self._db() as c:
            tables=c.execute("SELECT COUNT(*) n FROM sqlite_master WHERE type='table'").fetchone()["n"]
            q=c.execute("SELECT COUNT(*) n FROM qualifications").fetchone()["n"]
            p=c.execute("SELECT COUNT(*) n FROM evidence_portfolios").fetchone()["n"]
            m=c.execute("SELECT COUNT(*) n FROM moderation_reviews").fetchone()["n"]
        return {"status":"ok","engine":"lms-accreditation-control","tables":tables,"qualifications":q,"portfolios":p,"moderation_reviews":m,"tenant_scoped":True,"certificate_verification":True,"credentials_exposed":False}
