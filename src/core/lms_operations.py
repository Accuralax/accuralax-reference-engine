from .lms_training import LMSTraining, now, new_id

class LMSOperations:
    def __init__(self, lms=None):
        self.lms = lms or LMSTraining()

    def health(self):
        return {"status":"ok","engine":"lms-training-operations","credentials_exposed":False}

    def operations_dashboard(self, tenant_id, workspace_id):
        self.lms._validate_scope(tenant_id, workspace_id)
        with self.lms._db() as c:
            cohorts = c.execute("SELECT COUNT(*) n FROM cohorts h JOIN courses co ON co.course_id=h.course_id WHERE co.tenant_id=? AND co.workspace_id=?",(tenant_id,workspace_id)).fetchone()["n"]
            instructors = c.execute("SELECT COUNT(*) n FROM instructors WHERE tenant_id=? AND workspace_id=?",(tenant_id,workspace_id)).fetchone()["n"]
            assignments = c.execute("SELECT COUNT(*) n FROM instructor_assignments WHERE tenant_id=? AND workspace_id=? AND status='active'",(tenant_id,workspace_id)).fetchone()["n"]
            sessions = c.execute("SELECT COUNT(*) n FROM training_sessions WHERE tenant_id=? AND workspace_id=?",(tenant_id,workspace_id)).fetchone()["n"]
            scheduled_sessions = c.execute("SELECT COUNT(*) n FROM training_sessions WHERE tenant_id=? AND workspace_id=? AND status='scheduled'",(tenant_id,workspace_id)).fetchone()["n"]
            unassigned_cohorts = c.execute("""SELECT COUNT(*) n FROM cohorts h JOIN courses co ON co.course_id=h.course_id
                                               WHERE co.tenant_id=? AND co.workspace_id=?
                                               AND NOT EXISTS (SELECT 1 FROM instructor_assignments a WHERE a.cohort_id=h.cohort_id AND a.status='active')""",
                                            (tenant_id,workspace_id)).fetchone()["n"]
            learners = c.execute("""SELECT COUNT(DISTINCT l.learner_id) n FROM learners l
                                    JOIN enrolments e ON e.learner_id=l.learner_id
                                    WHERE l.tenant_id=? AND l.workspace_id=?""",(tenant_id,workspace_id)).fetchone()["n"]
        return {"cohorts":cohorts,"instructors":instructors,"active_assignments":assignments,
                "sessions":sessions,"scheduled_sessions":scheduled_sessions,"unassigned_cohorts":unassigned_cohorts,
                "active_learners":learners,"generated_at":now(),"human_oversight_required":True,"credentials_exposed":False}
