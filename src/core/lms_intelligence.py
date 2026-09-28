import json

from .lms_training import LMSTraining, now, new_id


class LMSIntelligence:
    """Governed learner and training intelligence built on the LMS persistence layer."""

    def __init__(self, lms=None):
        self.lms = lms or LMSTraining()

    def learner_profile(self, tenant_id, workspace_id, learner_id):
        self.lms._validate_scope(tenant_id, workspace_id)
        with self.lms._db() as c:
            learner = c.execute(
                "SELECT * FROM learners WHERE learner_id=? AND tenant_id=? AND workspace_id=?",
                (learner_id, tenant_id, workspace_id)).fetchone()
            if not learner:
                raise ValueError("learner_not_found")
            progress = c.execute("""SELECT p.*, c.title FROM progress p JOIN courses c ON c.course_id=p.course_id
                WHERE p.learner_id=? ORDER BY p.updated_at DESC""", (learner_id,)).fetchall()
            attempts = c.execute("""SELECT a.*, s.title, s.course_id FROM attempts a JOIN assessments s ON s.assessment_id=a.assessment_id
                WHERE a.learner_id=? ORDER BY a.submitted_at DESC""", (learner_id,)).fetchall()
            attendance = c.execute("SELECT * FROM attendance WHERE learner_id=? ORDER BY session_date DESC", (learner_id,)).fetchall()
            competencies = c.execute("""SELECT cc.course_id, cc.competency_id, cc.target_level, co.name, co.level
                FROM course_competencies cc JOIN competencies co ON co.competency_id=cc.competency_id
                JOIN enrolments e ON e.course_id=cc.course_id WHERE e.learner_id=?""", (learner_id,)).fetchall()
        return {"learner":dict(learner),"progress":[dict(x) for x in progress],"attempts":[dict(x) for x in attempts],
                "attendance":[dict(x) for x in attendance],"competencies":[dict(x) for x in competencies]}

    def skill_gaps(self, tenant_id, workspace_id, learner_id):
        profile = self.learner_profile(tenant_id, workspace_id, learner_id)
        attempts = [x for x in profile["attempts"] if x["score"] is not None]
        avg = sum(float(x["score"]) for x in attempts)/len(attempts) if attempts else None
        gaps = []
        for c in profile["competencies"]:
            scores = [float(x["score"]) for x in attempts if x["course_id"] == c["course_id"]]
            score = sum(scores)/len(scores) if scores else None
            if score is None or score < 70:
                gaps.append({"competency_id":c["competency_id"],"name":c["name"],"target_level":c["target_level"],
                    "evidence":"assessment_score" if score is not None else "missing_assessment_evidence",
                    "score":score,"priority":"high" if score is None or score < 50 else "medium"})
        return {"learner_id":learner_id,"average_score":avg,"gaps":gaps,"requires_review":bool(gaps)}

    def performance_summary(self, tenant_id, workspace_id, learner_id):
        profile = self.learner_profile(tenant_id, workspace_id, learner_id)
        scored = [float(x["score"]) for x in profile["attempts"] if x["score"] is not None]
        completed = [x for x in profile["progress"] if float(x.get("completion_pct") or 0) >= 100]
        total_progress = [float(x.get("completion_pct") or 0) for x in profile["progress"]]
        attendance = profile["attendance"]
        present = sum(1 for x in attendance if str(x.get("status","")).lower() in ("present","attended","late"))
        attendance_rate = (present/len(attendance)*100) if attendance else None
        avg = sum(scored)/len(scored) if scored else None
        gaps = self.skill_gaps(tenant_id, workspace_id, learner_id)["gaps"]
        risk_flags = []
        if avg is not None and avg < 50: risk_flags.append("low_assessment_performance")
        if attendance_rate is not None and attendance_rate < 75: risk_flags.append("low_attendance")
        if gaps: risk_flags.append("skill_gaps")
        if profile["progress"] and sum(total_progress)/len(total_progress) < 50: risk_flags.append("low_progress")
        return {
            "learner_id": learner_id,
            "completion_rate": (len(completed)/len(profile["progress"])*100) if profile["progress"] else 0,
            "average_progress": (sum(total_progress)/len(total_progress)) if total_progress else 0,
            "assessment_average": avg,
            "attendance_rate": attendance_rate,
            "assessment_count": len(scored),
            "course_count": len(profile["progress"]),
            "competency_count": len(profile["competencies"]),
            "skill_gap_count": len(gaps),
            "risk_flags": risk_flags,
            "risk_level": "high" if len(risk_flags) >= 2 else ("medium" if risk_flags else "low"),
            "strengths": [{"type":"assessment","value":avg}] if avg is not None and avg >= 70 else [],
            "requires_human_review": True,
        }

    def instructor_dashboard(self, tenant_id, workspace_id, instructor_id=None):
        self.lms._validate_scope(tenant_id, workspace_id)
        with self.lms._db() as c:
            if instructor_id:
                assigned = c.execute('''SELECT DISTINCT a.cohort_id,h.course_id FROM instructor_assignments a
                                        JOIN cohorts h ON h.cohort_id=a.cohort_id
                                        WHERE a.tenant_id=? AND a.workspace_id=? AND a.instructor_id=? AND a.status='active' ''',
                                     (tenant_id,workspace_id,instructor_id)).fetchall()
                cohort_ids=[x['cohort_id'] for x in assigned]
                course_ids=list({x['course_id'] for x in assigned})
            else:
                assigned = c.execute('SELECT cohort_id,course_id FROM cohorts h JOIN courses co ON co.course_id=h.course_id WHERE co.tenant_id=? AND co.workspace_id=?',
                                     (tenant_id,workspace_id)).fetchall()
                cohort_ids=[x['cohort_id'] for x in assigned]
                course_ids=list({x['course_id'] for x in assigned})
            cohorts=len(cohort_ids)
            courses=len(course_ids)
            learners_query='''SELECT DISTINCT l.learner_id FROM learners l JOIN enrolments e ON e.learner_id=l.learner_id
                              WHERE l.tenant_id=? AND l.workspace_id=?'''
            params=[tenant_id,workspace_id]
            if instructor_id:
                learners_query += ' AND e.cohort_id IN (' + ','.join('?' for _ in cohort_ids) + ')' if cohort_ids else ' AND 1=0'
                params.extend(cohort_ids)
            rows=c.execute(learners_query,tuple(params)).fetchall()
        learner_summaries=[self.performance_summary(tenant_id,workspace_id,x['learner_id']) for x in rows]
        scored=[x['assessment_average'] for x in learner_summaries if x['assessment_average'] is not None]
        return {
            'instructor_id': instructor_id, 'cohort_count': cohorts, 'learner_count': len(learner_summaries), 'course_count': courses,
            'at_risk_learners': [x for x in learner_summaries if x['risk_level'] in ('high','medium')],
            'high_risk_count': sum(1 for x in learner_summaries if x['risk_level']=='high'),
            'average_assessment': (sum(scored)/len(scored)) if scored else None,
            'requires_human_review': True,
        }

    def recommend_learning_path(self, tenant_id, workspace_id, learner_id, goal):
        gaps = self.skill_gaps(tenant_id, workspace_id, learner_id)
        path_id = new_id("PATH")
        evidence = {"goal":goal,"skill_gaps":gaps,"generated_at":now(),"human_review_required":True}
        with self.lms._db() as c:
            c.execute("INSERT INTO learning_paths VALUES (?,?,?,?,?,?,?,?,?,?)",
                (path_id,tenant_id,workspace_id,learner_id,f"Adaptive path — {goal}",goal,"adaptive","draft",json.dumps(evidence),now()))
        return {"path_id":path_id,"learner_id":learner_id,"goal":goal,"status":"draft",
                "recommendations":[{"type":"remediation","competency_id":g["competency_id"],"reason":g["evidence"],"priority":g["priority"]} for g in gaps["gaps"]],
                "requires_human_review":True,"evidence":evidence}

    def record_learning_event(self, tenant_id, workspace_id, learner_id, event_type, entity_type="", entity_id="", payload=None):
        self.lms._validate_scope(tenant_id, workspace_id)
        eid=new_id("LEARN-EVENT")
        with self.lms._db() as c:
            c.execute("INSERT INTO learning_events VALUES (?,?,?,?,?,?,?,?,?)",
                (eid,tenant_id,workspace_id,learner_id,event_type,entity_type,entity_id,json.dumps(payload or {},sort_keys=True),now()))
        return {"event_id":eid,"status":"recorded","tenant_id":tenant_id,"workspace_id":workspace_id}

    def health(self):
        return {"status":"ok","engine":"personalised-learning-intelligence","adaptive_paths":True,
            "skill_gap_analysis":True,"performance_intelligence":True,"instructor_dashboard":True,
            "human_review_required_for_generated_paths":True,"credentials_exposed":False}
