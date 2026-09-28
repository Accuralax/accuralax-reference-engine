import json

from .lms_training import LMSTraining, now


class LMSAnalytics:
    """Governed training analytics and certification evidence engine."""

    def __init__(self, lms=None):
        self.lms = lms or LMSTraining()

    def _scope(self, tenant_id, workspace_id):
        self.lms._validate_scope(tenant_id, workspace_id)

    def training_dashboard(self, tenant_id, workspace_id):
        self._scope(tenant_id, workspace_id)
        with self.lms._db() as c:
            learners = c.execute("SELECT COUNT(*) n FROM learners WHERE tenant_id=? AND workspace_id=?", (tenant_id,workspace_id)).fetchone()["n"]
            courses = c.execute("SELECT COUNT(*) n FROM courses WHERE tenant_id=? AND workspace_id=?", (tenant_id,workspace_id)).fetchone()["n"]
            enrolments = c.execute("""SELECT COUNT(*) n FROM enrolments e JOIN learners l ON l.learner_id=e.learner_id
                WHERE l.tenant_id=? AND l.workspace_id=?""",(tenant_id,workspace_id)).fetchone()["n"]
            completed = c.execute("""SELECT COUNT(*) n FROM enrolments e JOIN learners l ON l.learner_id=e.learner_id
                WHERE l.tenant_id=? AND l.workspace_id=? AND e.status='completed'""",(tenant_id,workspace_id)).fetchone()["n"]
            issued = c.execute("""SELECT COUNT(*) n FROM certificates x JOIN learners l ON l.learner_id=x.learner_id
                WHERE l.tenant_id=? AND l.workspace_id=? AND x.status='issued'""",(tenant_id,workspace_id)).fetchone()["n"]
            pending_ai = c.execute("""SELECT COUNT(*) n FROM ai_generations g JOIN courses c ON c.course_id=g.course_id
                WHERE c.tenant_id=? AND c.workspace_id=? AND g.human_reviewed=0""",(tenant_id,workspace_id)).fetchone()["n"]
            attendance = c.execute("""SELECT COUNT(*) total,
                SUM(CASE WHEN LOWER(status) IN ('present','attended','late') THEN 1 ELSE 0 END) present
                FROM attendance a JOIN cohorts h ON h.cohort_id=a.cohort_id
                JOIN courses co ON co.course_id=h.course_id
                WHERE co.tenant_id=? AND co.workspace_id=?""",(tenant_id,workspace_id)).fetchone()
            scores = c.execute("""SELECT AVG(a.score) avg_score, COUNT(a.attempt_id) attempts
                FROM attempts a JOIN learners l ON l.learner_id=a.learner_id
                WHERE l.tenant_id=? AND l.workspace_id=? AND a.score IS NOT NULL""",(tenant_id,workspace_id)).fetchone()
        return {
            "learners":learners,"courses":courses,"enrolments":enrolments,"completed":completed,"certificates_issued":issued,
            "completion_rate":(completed/enrolments*100) if enrolments else 0,
            "attendance_rate":((attendance["present"] or 0)/attendance["total"]*100) if attendance["total"] else None,
            "assessment_average":scores["avg_score"],"assessment_attempts":scores["attempts"],
            "ai_content_pending_review":pending_ai,"generated_at":now(),
            "requires_human_review":True,"credentials_exposed":False
        }

    def course_performance(self, tenant_id, workspace_id, course_id):
        self._scope(tenant_id, workspace_id)
        with self.lms._db() as c:
            course=c.execute("SELECT * FROM courses WHERE course_id=? AND tenant_id=? AND workspace_id=?",(course_id,tenant_id,workspace_id)).fetchone()
            if not course: raise ValueError("course_not_found")
            enrol=c.execute("SELECT COUNT(*) n, SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) completed FROM enrolments WHERE course_id=?",(course_id,)).fetchone()
            score=c.execute("""SELECT AVG(a.score) avg_score, MIN(a.score) min_score, MAX(a.score) max_score, COUNT(a.attempt_id) attempts
                FROM attempts a JOIN assessments s ON s.assessment_id=a.assessment_id WHERE s.course_id=? AND a.score IS NOT NULL""",(course_id,)).fetchone()
            attendance=c.execute("""SELECT COUNT(*) total, SUM(CASE WHEN LOWER(a.status) IN ('present','attended','late') THEN 1 ELSE 0 END) present
                FROM attendance a JOIN cohorts h ON h.cohort_id=a.cohort_id WHERE h.course_id=?""",(course_id,)).fetchone()
            assessments=c.execute("SELECT assessment_id,title,status,pass_mark,high_impact FROM assessments WHERE course_id=?",(course_id,)).fetchall()
        return {
            "course":dict(course),"enrolments":enrol["n"],"completed":enrol["completed"] or 0,
            "completion_rate":((enrol["completed"] or 0)/enrol["n"]*100) if enrol["n"] else 0,
            "assessment":dict(score),"attendance_rate":((attendance["present"] or 0)/attendance["total"]*100) if attendance["total"] else None,
            "assessments":[dict(x) for x in assessments],"requires_human_review":True,"credentials_exposed":False
        }

    def cohort_performance(self, tenant_id, workspace_id, cohort_id):
        self._scope(tenant_id,workspace_id)
        with self.lms._db() as c:
            cohort=c.execute("""SELECT h.*, co.title FROM cohorts h JOIN courses co ON co.course_id=h.course_id
                WHERE h.cohort_id=? AND co.tenant_id=? AND co.workspace_id=?""",(cohort_id,tenant_id,workspace_id)).fetchone()
            if not cohort: raise ValueError("cohort_not_found")
            learners=c.execute("""SELECT l.* FROM learners l JOIN enrolments e ON e.learner_id=l.learner_id
                WHERE e.cohort_id=? AND l.tenant_id=? AND l.workspace_id=?""",(cohort_id,tenant_id,workspace_id)).fetchall()
            attendance=c.execute("""SELECT COUNT(*) total, SUM(CASE WHEN LOWER(status) IN ('present','attended','late') THEN 1 ELSE 0 END) present
                FROM attendance WHERE cohort_id=?""",(cohort_id,)).fetchone()
        return {
            "cohort":dict(cohort),"learner_count":len(learners),
            "attendance_rate":((attendance["present"] or 0)/attendance["total"]*100) if attendance["total"] else None,
            "learners":[dict(x) for x in learners],
            "generated_at":now(),"requires_human_review":True,"credentials_exposed":False
        }

    def certification_evidence(self, tenant_id, workspace_id, learner_id, course_id):
        self._scope(tenant_id,workspace_id)
        with self.lms._db() as c:
            learner=c.execute("SELECT * FROM learners WHERE learner_id=? AND tenant_id=? AND workspace_id=?",(learner_id,tenant_id,workspace_id)).fetchone()
            course=c.execute("SELECT * FROM courses WHERE course_id=? AND tenant_id=? AND workspace_id=?",(course_id,tenant_id,workspace_id)).fetchone()
            enrol=c.execute("SELECT * FROM enrolments WHERE learner_id=? AND course_id=?",(learner_id,course_id)).fetchone()
            progress=c.execute("SELECT * FROM progress WHERE learner_id=? AND course_id=?",(learner_id,course_id)).fetchall()
            attempts=c.execute("""SELECT a.*, s.title, s.pass_mark, s.high_impact, s.status assessment_status
                FROM attempts a JOIN assessments s ON s.assessment_id=a.assessment_id
                WHERE a.learner_id=? AND s.course_id=?""",(learner_id,course_id)).fetchall()
            competencies=c.execute("""SELECT cc.*, co.name, co.level FROM course_competencies cc JOIN competencies co ON co.competency_id=cc.competency_id
                WHERE cc.course_id=?""",(course_id,)).fetchall()
            attendance=c.execute("""SELECT a.* FROM attendance a JOIN cohorts h ON h.cohort_id=a.cohort_id
                WHERE a.learner_id=? AND h.course_id=?""",(learner_id,course_id)).fetchall()
        if not learner or not course: raise ValueError("learner_or_course_not_found")
        passed_assessments=[a for a in attempts if a["passed"]==1 and a["grading_provenance"]]
        completion=max([float(x["completion_pct"]) for x in progress], default=0)
        evidence={
            "completion":{"verified":bool(enrol and enrol["status"]=="completed" and completion>=100),"max_progress":completion},
            "assessments":{"count":len(attempts),"passed_with_provenance":len(passed_assessments),"all_passing":bool(attempts) and len(passed_assessments)==len(attempts)},
            "competencies":{"mapped":len(competencies),"evidence_required":[dict(x) for x in competencies]},
            "attendance":{"sessions":len(attendance),"present":sum(1 for x in attendance if str(x["status"]).lower() in ("present","attended","late"))},
        }
        eligible=evidence["completion"]["verified"] and evidence["assessments"]["all_passing"]
        return {"eligible":eligible,"learner_id":learner_id,"course_id":course_id,"evidence":evidence,
                "provenance_required":True,"exception_requires_human_review":not eligible,
                "generated_at":now(),"credentials_exposed":False}

    def health(self):
        return {"status":"ok","engine":"training-analytics-certification-evidence","training_analytics":True,
                "course_cohort_analytics":True,"certification_evidence":True,"provenance_required":True,
                "human_review_for_exceptions":True,"credentials_exposed":False}
