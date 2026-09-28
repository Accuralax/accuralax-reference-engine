import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

from .lms_time import session_time_view, to_utc
from .event_bus import EventBus

DB_PATH = os.getenv("LMS_DB_PATH", os.path.join("data", "lms_training.sqlite3"))

COURSE_STATES = {"draft", "review", "approved", "published", "archived"}
ENROLMENT_STATES = {"pending", "active", "completed", "withdrawn", "suspended"}
ASSESSMENT_STATES = {"draft", "review", "published", "closed"}
CERTIFICATE_STATES = {"draft", "issued", "revoked"}
CONTENT_STATES = {"draft", "generated", "reviewed", "approved", "published", "superseded"}


def now():
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix):
    return f"CFS-{prefix}-{uuid.uuid4().hex[:12]}"


class LMSTraining:
    """Governed LMS + Training Management persistence layer.

    AI-generated content is never published automatically and certificates
    cannot be issued without verified completion.
    """

    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = db_path
        self.events = EventBus(os.path.join(os.path.dirname(db_path) or ".", "event_bus.sqlite3"))
        self._init()

    def _db(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _init(self):
        with self._db() as c:
            c.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS programmes(
              programme_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              name TEXT NOT NULL, description TEXT, status TEXT NOT NULL DEFAULT 'draft',
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS courses(
              course_id TEXT PRIMARY KEY, programme_id TEXT, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              title TEXT NOT NULL, description TEXT, status TEXT NOT NULL DEFAULT 'draft',
              version INTEGER NOT NULL DEFAULT 1, generated_content INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              FOREIGN KEY(programme_id) REFERENCES programmes(programme_id));
            CREATE TABLE IF NOT EXISTS modules(
              module_id TEXT PRIMARY KEY, course_id TEXT NOT NULL, title TEXT NOT NULL,
              description TEXT, position INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
              FOREIGN KEY(course_id) REFERENCES courses(course_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS lessons(
              lesson_id TEXT PRIMARY KEY, module_id TEXT NOT NULL, title TEXT NOT NULL,
              content TEXT, position INTEGER NOT NULL, content_state TEXT NOT NULL DEFAULT 'draft',
              ai_generated INTEGER NOT NULL DEFAULT 0,
              FOREIGN KEY(module_id) REFERENCES modules(module_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS learners(
              learner_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              name TEXT NOT NULL, email TEXT, external_ref TEXT, status TEXT NOT NULL DEFAULT 'active',
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS instructors(
              instructor_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              name TEXT NOT NULL, email TEXT, authorised INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cohorts(
              cohort_id TEXT PRIMARY KEY, course_id TEXT NOT NULL, name TEXT NOT NULL,
              start_date TEXT, end_date TEXT, capacity INTEGER, status TEXT NOT NULL DEFAULT 'planned',
              FOREIGN KEY(course_id) REFERENCES courses(course_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS instructor_assignments(
              assignment_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              cohort_id TEXT NOT NULL, instructor_id TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'lead',
              status TEXT NOT NULL DEFAULT 'active', assigned_at TEXT NOT NULL, released_at TEXT,
              UNIQUE(cohort_id, instructor_id, role),
              FOREIGN KEY(cohort_id) REFERENCES cohorts(cohort_id) ON DELETE CASCADE,
              FOREIGN KEY(instructor_id) REFERENCES instructors(instructor_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS training_sessions(
              session_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              cohort_id TEXT NOT NULL, instructor_id TEXT, title TEXT NOT NULL,
              scheduled_start TEXT NOT NULL, scheduled_end TEXT NOT NULL, mode TEXT NOT NULL DEFAULT 'classroom',
              location TEXT, status TEXT NOT NULL DEFAULT 'scheduled', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              FOREIGN KEY(cohort_id) REFERENCES cohorts(cohort_id) ON DELETE CASCADE,
              FOREIGN KEY(instructor_id) REFERENCES instructors(instructor_id) ON DELETE SET NULL);
            CREATE TABLE IF NOT EXISTS enrolments(
              enrolment_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, course_id TEXT NOT NULL,
              cohort_id TEXT, status TEXT NOT NULL DEFAULT 'pending', enrolled_at TEXT NOT NULL,
              completed_at TEXT, UNIQUE(learner_id, course_id),
              FOREIGN KEY(learner_id) REFERENCES learners(learner_id),
              FOREIGN KEY(course_id) REFERENCES courses(course_id),
              FOREIGN KEY(cohort_id) REFERENCES cohorts(cohort_id));
            CREATE TABLE IF NOT EXISTS assessments(
              assessment_id TEXT PRIMARY KEY, course_id TEXT NOT NULL, module_id TEXT,
              title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft', pass_mark REAL NOT NULL DEFAULT 50,
              high_impact INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
              FOREIGN KEY(course_id) REFERENCES courses(course_id) ON DELETE CASCADE,
              FOREIGN KEY(module_id) REFERENCES modules(module_id));
            CREATE TABLE IF NOT EXISTS questions(
              question_id TEXT PRIMARY KEY, assessment_id TEXT NOT NULL, prompt TEXT NOT NULL,
              options_json TEXT, answer_json TEXT, points REAL NOT NULL DEFAULT 1,
              FOREIGN KEY(assessment_id) REFERENCES assessments(assessment_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS attempts(
              attempt_id TEXT PRIMARY KEY, assessment_id TEXT NOT NULL, learner_id TEXT NOT NULL,
              answers_json TEXT NOT NULL, score REAL, passed INTEGER, graded_by TEXT,
              grading_provenance TEXT, submitted_at TEXT, graded_at TEXT,
              FOREIGN KEY(assessment_id) REFERENCES assessments(assessment_id),
              FOREIGN KEY(learner_id) REFERENCES learners(learner_id));
            CREATE TABLE IF NOT EXISTS attendance(
              attendance_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, cohort_id TEXT NOT NULL,
              session_date TEXT NOT NULL, status TEXT NOT NULL, recorded_by TEXT, recorded_at TEXT NOT NULL,
              UNIQUE(learner_id, cohort_id, session_date));
            CREATE TABLE IF NOT EXISTS progress(
              progress_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, course_id TEXT NOT NULL,
              lesson_id TEXT, completion_pct REAL NOT NULL DEFAULT 0, competency_json TEXT,
              updated_at TEXT NOT NULL, UNIQUE(learner_id, course_id, lesson_id));
            CREATE TABLE IF NOT EXISTS certificates(
              certificate_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, course_id TEXT NOT NULL,
              certificate_no TEXT UNIQUE, status TEXT NOT NULL DEFAULT 'draft',
              issued_at TEXT, revoked_at TEXT, completion_verified INTEGER NOT NULL DEFAULT 0,
              evidence_json TEXT, FOREIGN KEY(learner_id) REFERENCES learners(learner_id),
              FOREIGN KEY(course_id) REFERENCES courses(course_id));
            CREATE TABLE IF NOT EXISTS ai_generations(
              generation_id TEXT PRIMARY KEY, course_id TEXT NOT NULL, module_id TEXT,
              request TEXT NOT NULL, output TEXT NOT NULL, content_state TEXT NOT NULL DEFAULT 'generated',
              model TEXT, human_reviewed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
              FOREIGN KEY(course_id) REFERENCES courses(course_id));
            CREATE TABLE IF NOT EXISTS competencies(
              competency_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              name TEXT NOT NULL, description TEXT, level TEXT NOT NULL DEFAULT 'novice',
              evidence_required INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS course_competencies(
              course_id TEXT NOT NULL, competency_id TEXT NOT NULL, target_level TEXT NOT NULL,
              PRIMARY KEY(course_id, competency_id),
              FOREIGN KEY(course_id) REFERENCES courses(course_id) ON DELETE CASCADE,
              FOREIGN KEY(competency_id) REFERENCES competencies(competency_id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS learning_paths(
              path_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              learner_id TEXT, name TEXT NOT NULL, goal TEXT, method TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'draft', evidence_json TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS avatar_sessions(
              session_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              learner_id TEXT NOT NULL, course_id TEXT, mode TEXT NOT NULL,
              context_json TEXT, messages_json TEXT, memory_scope TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS content_versions(
              version_id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
              version INTEGER NOT NULL, content TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'draft',
              generated_by TEXT, reviewed_by TEXT, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS learning_events(
              event_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
              learner_id TEXT, event_type TEXT NOT NULL, entity_type TEXT, entity_id TEXT,
              payload_json TEXT, created_at TEXT NOT NULL);
            """)

    def _row(self, row):
        return dict(row) if row else None

    def _validate_scope(self, tenant_id, workspace_id):
        if not tenant_id or not workspace_id:
            raise ValueError("tenant_id and workspace_id are required")

    def _learner_scope(self, learner_id):
        with self._db() as c:
            row = c.execute("SELECT tenant_id, workspace_id FROM learners WHERE learner_id=?", (learner_id,)).fetchone()
        if not row:
            raise ValueError("learner_not_found")
        return row["tenant_id"], row["workspace_id"]

    def create_programme(self, tenant_id, workspace_id, name, description=""):
        self._validate_scope(tenant_id, workspace_id)
        pid, ts = new_id("PROGRAMME"), now()
        with self._db() as c:
            c.execute("INSERT INTO programmes VALUES (?,?,?,?,?,?,?,?)",
                      (pid, tenant_id, workspace_id, name, description, "draft", ts, ts))
        return self.get_programme(pid)

    def create_course(self, tenant_id, workspace_id, title, description="", programme_id=None):
        self._validate_scope(tenant_id, workspace_id)
        cid, ts = new_id("COURSE"), now()
        with self._db() as c:
            if programme_id:
                p = c.execute("SELECT programme_id FROM programmes WHERE programme_id=? AND tenant_id=? AND workspace_id=?",
                              (programme_id, tenant_id, workspace_id)).fetchone()
                if not p: raise ValueError("programme_not_found")
            c.execute("INSERT INTO courses VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (cid, programme_id, tenant_id, workspace_id, title, description, "draft", 1, 0, ts, ts))
        return self.get_course(cid)

    def add_module(self, course_id, title, description="", position=1):
        mid = new_id("MODULE")
        with self._db() as c:
            c.execute("INSERT INTO modules VALUES (?,?,?,?,?,?)", (mid, course_id, title, description, position, "draft"))
        return self._row(c.execute("SELECT * FROM modules WHERE module_id=?", (mid,)).fetchone())

    def add_lesson(self, module_id, title, content="", position=1, ai_generated=False):
        lid = new_id("LESSON")
        state = "generated" if ai_generated else "draft"
        with self._db() as c:
            c.execute("INSERT INTO lessons VALUES (?,?,?,?,?,?,?)",
                      (lid, module_id, title, content, position, state, int(ai_generated)))
        return self._row(c.execute("SELECT * FROM lessons WHERE lesson_id=?", (lid,)).fetchone())

    def create_learner(self, tenant_id, workspace_id, name, email="", external_ref=""):
        self._validate_scope(tenant_id, workspace_id)
        lid, ts = new_id("LEARNER"), now()
        with self._db() as c:
            c.execute("INSERT INTO learners VALUES (?,?,?,?,?,?,?,?,?)",
                      (lid, tenant_id, workspace_id, name, email, external_ref, "active", ts, ts))
        return self._row(c.execute("SELECT * FROM learners WHERE learner_id=?", (lid,)).fetchone())

    def create_instructor(self, tenant_id, workspace_id, name, email="", authorised=False):
        self._validate_scope(tenant_id, workspace_id)
        iid, ts = new_id("INSTRUCTOR"), now()
        with self._db() as c:
            c.execute("INSERT INTO instructors VALUES (?,?,?,?,?,?,?,?)",
                      (iid, tenant_id, workspace_id, name, email, int(authorised), ts, ts))
        return self._row(c.execute("SELECT * FROM instructors WHERE instructor_id=?", (iid,)).fetchone())

    def create_cohort(self, course_id, name, start_date=None, end_date=None, capacity=None):
        cid = new_id("COHORT")
        with self._db() as c:
            c.execute("INSERT INTO cohorts VALUES (?,?,?,?,?,?,?)",
                      (cid, course_id, name, start_date, end_date, capacity, "planned"))
        return self._row(c.execute("SELECT * FROM cohorts WHERE cohort_id=?", (cid,)).fetchone())

    def enrol(self, learner_id, course_id, cohort_id=None):
        eid, ts = new_id("ENROL"), now()
        with self._db() as c:
            c.execute("INSERT INTO enrolments VALUES (?,?,?,?,?,?,?)",
                      (eid, learner_id, course_id, cohort_id, "active", ts, None))
        result = self._row(c.execute("SELECT * FROM enrolments WHERE enrolment_id=?", (eid,)).fetchone())
        tenant_id, workspace_id = self._learner_scope(learner_id)
        self.events.publish("lms.enrolment.created", tenant_id, workspace_id, "system", "learner", learner_id, eid, {"course_id": course_id, "cohort_id": cohort_id, "status": "active"}, idempotency_key=f"enrolment-created:{eid}")
        return result

    def record_progress(self, learner_id, course_id, completion_pct, lesson_id=None, competency=None):
        pct = max(0.0, min(100.0, float(completion_pct)))
        pid, ts = new_id("PROGRESS"), now()
        payload = json.dumps(competency or {}, sort_keys=True)
        with self._db() as c:
            c.execute("""INSERT INTO progress VALUES (?,?,?,?,?,?,?)
                         ON CONFLICT(learner_id,course_id,lesson_id) DO UPDATE SET completion_pct=excluded.completion_pct, competency_json=excluded.competency_json, updated_at=excluded.updated_at""",
                      (pid, learner_id, course_id, lesson_id, pct, payload, ts))
            if pct >= 100:
                c.execute("UPDATE enrolments SET status='completed', completed_at=? WHERE learner_id=? AND course_id=?",
                          (ts, learner_id, course_id))
        result = self._row(c.execute("SELECT * FROM progress WHERE progress_id=?", (pid,)).fetchone())
        tenant_id, workspace_id = self._learner_scope(learner_id)
        self.events.publish("lms.progress.recorded", tenant_id, workspace_id, "system", "learner", learner_id, pid, {"course_id": course_id, "completion_pct": pct, "lesson_id": lesson_id})
        return result

    def record_attendance(self, learner_id, cohort_id, session_date, status, recorded_by="system"):
        aid, ts = new_id("ATTEND"), now()
        with self._db() as c:
            c.execute("""INSERT INTO attendance VALUES (?,?,?,?,?,?,?)
                         ON CONFLICT(learner_id,cohort_id,session_date) DO UPDATE SET status=excluded.status,recorded_by=excluded.recorded_by,recorded_at=excluded.recorded_at""",
                      (aid, learner_id, cohort_id, session_date, status, recorded_by, ts))
        result = self._row(c.execute("SELECT * FROM attendance WHERE attendance_id=?", (aid,)).fetchone())
        tenant_id, workspace_id = self._learner_scope(learner_id)
        self.events.publish("lms.attendance.recorded", tenant_id, workspace_id, str(recorded_by), "learner", learner_id, aid, {"cohort_id": cohort_id, "session_date": session_date, "status": status})
        return result

    def assign_instructor(self, tenant_id, workspace_id, cohort_id, instructor_id, role='lead'):
        self._validate_scope(tenant_id, workspace_id)
        aid, ts = new_id('ASSIGN'), now()
        with self._db() as c:
            cohort = c.execute('''SELECT h.cohort_id FROM cohorts h JOIN courses co ON co.course_id=h.course_id
                                  WHERE h.cohort_id=? AND co.tenant_id=? AND co.workspace_id=?''',
                               (cohort_id, tenant_id, workspace_id)).fetchone()
            instructor = c.execute('SELECT instructor_id FROM instructors WHERE instructor_id=? AND tenant_id=? AND workspace_id=?',
                                   (instructor_id, tenant_id, workspace_id)).fetchone()
            if not cohort: raise ValueError('cohort_not_found')
            if not instructor: raise ValueError('instructor_not_found')
            c.execute('''INSERT INTO instructor_assignments
                         (assignment_id,tenant_id,workspace_id,cohort_id,instructor_id,role,status,assigned_at,released_at)
                         VALUES (?,?,?,?,?,?,?,?,?)
                         ON CONFLICT(cohort_id,instructor_id,role) DO UPDATE SET status='active',released_at=NULL,assigned_at=excluded.assigned_at''',
                      (aid,tenant_id,workspace_id,cohort_id,instructor_id,role,'active',ts,None))
            row = c.execute('SELECT * FROM instructor_assignments WHERE cohort_id=? AND instructor_id=? AND role=?',
                            (cohort_id,instructor_id,role)).fetchone()
        result = self._row(row)
        self.events.publish("lms.instructor.assigned", tenant_id, workspace_id, "system", "cohort", cohort_id, aid, {"instructor_id": instructor_id, "role": role})
        return result

    def schedule_session(self, tenant_id, workspace_id, cohort_id, title, scheduled_start, scheduled_end,
                         instructor_id=None, mode='classroom', location=None):
        self._validate_scope(tenant_id, workspace_id)
        sid, ts = new_id('SESSION'), now()
        with self._db() as c:
            cohort = c.execute('''SELECT h.cohort_id FROM cohorts h JOIN courses co ON co.course_id=h.course_id
                                  WHERE h.cohort_id=? AND co.tenant_id=? AND co.workspace_id=?''',
                               (cohort_id,tenant_id,workspace_id)).fetchone()
            if not cohort: raise ValueError('cohort_not_found')
            if instructor_id:
                ok = c.execute('SELECT instructor_id FROM instructors WHERE instructor_id=? AND tenant_id=? AND workspace_id=?',
                               (instructor_id,tenant_id,workspace_id)).fetchone()
                if not ok: raise ValueError('instructor_not_found')
            start_utc = to_utc(scheduled_start)
            end_utc = to_utc(scheduled_end)
            if end_utc <= start_utc: raise ValueError('session_end_must_follow_start')
            scheduled_start = start_utc.isoformat()
            scheduled_end = end_utc.isoformat()
            c.execute('''INSERT INTO training_sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                      (sid,tenant_id,workspace_id,cohort_id,instructor_id,title,scheduled_start,scheduled_end,mode,location,'scheduled',ts,ts))
        result = self._row(c.execute('SELECT * FROM training_sessions WHERE session_id=?',(sid,)).fetchone())
        self.events.publish("lms.session.scheduled", tenant_id, workspace_id, "system", "session", sid, sid, {"cohort_id": cohort_id, "instructor_id": instructor_id, "scheduled_start": scheduled_start, "scheduled_end": scheduled_end})
        return result

    def update_session(self, tenant_id, workspace_id, session_id, **changes):
        self._validate_scope(tenant_id, workspace_id)
        allowed = {'title','scheduled_start','scheduled_end','instructor_id','mode','location','status'}
        patch = {k:v for k,v in changes.items() if k in allowed and v is not None}
        if not patch: raise ValueError('no_session_changes')
        with self._db() as c:
            row = c.execute('SELECT * FROM training_sessions WHERE session_id=? AND tenant_id=? AND workspace_id=?',
                            (session_id,tenant_id,workspace_id)).fetchone()
            if not row: raise ValueError('session_not_found')
            start = patch.get('scheduled_start', row['scheduled_start'])
            end = patch.get('scheduled_end', row['scheduled_end'])
            start_utc = to_utc(start)
            end_utc = to_utc(end)
            if end_utc <= start_utc: raise ValueError('session_end_must_follow_start')
            if 'scheduled_start' in patch: patch['scheduled_start'] = start_utc.isoformat()
            if 'scheduled_end' in patch: patch['scheduled_end'] = end_utc.isoformat()
            if 'instructor_id' in patch and patch['instructor_id']:
                ok = c.execute('SELECT instructor_id FROM instructors WHERE instructor_id=? AND tenant_id=? AND workspace_id=?',
                               (patch['instructor_id'],tenant_id,workspace_id)).fetchone()
                if not ok: raise ValueError('instructor_not_found')
            sets = ', '.join(f'{k}=?' for k in patch)
            c.execute(f'UPDATE training_sessions SET {sets},updated_at=? WHERE session_id=?',
                      (*patch.values(),now(),session_id))
            return self._row(c.execute('SELECT * FROM training_sessions WHERE session_id=?',(session_id,)).fetchone())

    def session_view(self, tenant_id, workspace_id, session_id, timezone_name):
        self._validate_scope(tenant_id, workspace_id)
        with self._db() as c:
            row = c.execute('SELECT * FROM training_sessions WHERE session_id=? AND tenant_id=? AND workspace_id=?',
                            (session_id, tenant_id, workspace_id)).fetchone()
        if not row: raise ValueError('session_not_found')
        return session_time_view(dict(row), timezone_name)

    def cohort_roster(self, tenant_id, workspace_id, cohort_id, timezone_name=None):
        self._validate_scope(tenant_id, workspace_id)
        with self._db() as c:
            cohort = c.execute('''SELECT h.*,co.title course_title FROM cohorts h JOIN courses co ON co.course_id=h.course_id
                                  WHERE h.cohort_id=? AND co.tenant_id=? AND co.workspace_id=?''',
                               (cohort_id,tenant_id,workspace_id)).fetchone()
            if not cohort: raise ValueError('cohort_not_found')
            learners = c.execute('''SELECT e.enrolment_id,e.status,e.enrolled_at,l.learner_id,l.name,l.email,l.external_ref
                                    FROM enrolments e JOIN learners l ON l.learner_id=e.learner_id
                                    WHERE e.cohort_id=? AND l.tenant_id=? AND l.workspace_id=? ORDER BY l.name''',
                                 (cohort_id,tenant_id,workspace_id)).fetchall()
            instructors = c.execute('''SELECT a.*,i.name instructor_name,i.email instructor_email
                                       FROM instructor_assignments a JOIN instructors i ON i.instructor_id=a.instructor_id
                                       WHERE a.cohort_id=? AND a.tenant_id=? AND a.workspace_id=? AND a.status='active' ''',
                                    (cohort_id,tenant_id,workspace_id)).fetchall()
            sessions = c.execute('SELECT * FROM training_sessions WHERE cohort_id=? AND tenant_id=? AND workspace_id=? ORDER BY scheduled_start',
                                 (cohort_id,tenant_id,workspace_id)).fetchall()
        session_rows = [dict(x) for x in sessions]
        if timezone_name:
            session_rows = [session_time_view(x, timezone_name) for x in session_rows]
        return {'cohort':self._row(cohort),'learners':[dict(x) for x in learners],
                'instructors':[dict(x) for x in instructors],'sessions':session_rows}

    def set_assessment_status(self, tenant_id, workspace_id, assessment_id, status):
        self._validate_scope(tenant_id, workspace_id)
        if status not in ASSESSMENT_STATES: raise ValueError('invalid_assessment_status')
        with self._db() as c:
            row = c.execute('''SELECT a.assessment_id FROM assessments a JOIN courses co ON co.course_id=a.course_id
                               WHERE a.assessment_id=? AND co.tenant_id=? AND co.workspace_id=?''',
                            (assessment_id,tenant_id,workspace_id)).fetchone()
            if not row: raise ValueError('assessment_not_found')
            c.execute('UPDATE assessments SET status=? WHERE assessment_id=?',(status,assessment_id))
            result = self._row(c.execute('SELECT * FROM assessments WHERE assessment_id=?',(assessment_id,)).fetchone())
        self.events.publish("lms.assessment.status_changed", tenant_id, workspace_id, "system", "assessment", assessment_id, assessment_id, {"status": status})
        return result

    def revoke_certificate(self, tenant_id, workspace_id, certificate_id, reason=''):
        self._validate_scope(tenant_id, workspace_id)
        with self._db() as c:
            row = c.execute('''SELECT ce.* FROM certificates ce JOIN learners l ON l.learner_id=ce.learner_id
                               WHERE ce.certificate_id=? AND l.tenant_id=? AND l.workspace_id=?''',
                            (certificate_id,tenant_id,workspace_id)).fetchone()
            if not row: raise ValueError('certificate_not_found')
            evidence = json.loads(row['evidence_json'] or '{}'); evidence['revocation_reason'] = reason
            c.execute('UPDATE certificates SET status=\'revoked\',revoked_at=?,evidence_json=? WHERE certificate_id=?',
                      (now(),json.dumps(evidence,sort_keys=True),certificate_id))
            return self._row(c.execute('SELECT * FROM certificates WHERE certificate_id=?',(certificate_id,)).fetchone())

    def create_assessment(self, course_id, title, pass_mark=50, module_id=None, high_impact=False):
        aid, ts = new_id("ASSESS"), now()
        with self._db() as c:
            c.execute("INSERT INTO assessments VALUES (?,?,?,?,?,?,?,?)",
                      (aid, course_id, module_id, title, "draft", float(pass_mark), int(high_impact), ts))
        return self._row(c.execute("SELECT * FROM assessments WHERE assessment_id=?", (aid,)).fetchone())

    def add_question(self, assessment_id, prompt, options=None, answer=None, points=1):
        qid = new_id("QUESTION")
        with self._db() as c:
            c.execute("INSERT INTO questions VALUES (?,?,?,?,?,?)",
                      (qid, assessment_id, prompt, json.dumps(options or []), json.dumps(answer), points))
        return self._row(c.execute("SELECT * FROM questions WHERE question_id=?", (qid,)).fetchone())

    def submit_attempt(self, assessment_id, learner_id, answers):
        aid = new_id("ATTEMPT")
        with self._db() as c:
            c.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (aid, assessment_id, learner_id, json.dumps(answers), None, None, None, None, now(), None))
        return self._row(c.execute("SELECT * FROM attempts WHERE attempt_id=?", (aid,)).fetchone())

    def grade_attempt(self, attempt_id, score, passed, graded_by, provenance="human_review"):
        if not graded_by or not provenance: raise ValueError("grading_provenance_required")
        with self._db() as c:
            c.execute("UPDATE attempts SET score=?,passed=?,graded_by=?,grading_provenance=?,graded_at=? WHERE attempt_id=?",
                      (float(score), int(bool(passed)), graded_by, provenance, now(), attempt_id))
        return self._row(c.execute("SELECT * FROM attempts WHERE attempt_id=?", (attempt_id,)).fetchone())

    def generate_content(self, course_id, request, output, model="governed-generator", module_id=None):
        gid, ts = new_id("AIGEN"), now()
        with self._db() as c:
            c.execute("INSERT INTO ai_generations VALUES (?,?,?,?,?,?,?,?,?)",
                      (gid, course_id, module_id, request, output, "generated", model, 0, ts))
        return self._row(c.execute("SELECT * FROM ai_generations WHERE generation_id=?", (gid,)).fetchone())

    def review_content(self, generation_id, approved, reviewer):
        if not reviewer: raise ValueError("reviewer_required")
        state = "approved" if approved else "reviewed"
        with self._db() as c:
            generation = c.execute("SELECT * FROM ai_generations WHERE generation_id=?", (generation_id,)).fetchone()
            if not generation: raise ValueError("generation_not_found")
            c.execute("UPDATE ai_generations SET content_state=?,human_reviewed=1 WHERE generation_id=?",
                      (state, generation_id))
            if approved:
                c.execute("""UPDATE lessons SET content_state='approved'
                             WHERE module_id IN (SELECT m.module_id FROM modules m
                                                 WHERE m.course_id=?)
                               AND ai_generated=1""", (generation["course_id"],))
        result = self._row(c.execute("SELECT * FROM ai_generations WHERE generation_id=?", (generation_id,)).fetchone())
        return result

    def issue_certificate(self, learner_id, course_id, certificate_no=None):
        with self._db() as c:
            enrollment = c.execute("SELECT * FROM enrolments WHERE learner_id=? AND course_id=?", (learner_id, course_id)).fetchone()
            if not enrollment or enrollment["status"] != "completed":
                raise ValueError("certificate_requires_verified_completion")
            attempts = c.execute("""SELECT a.* FROM attempts a JOIN assessments s ON s.assessment_id=a.assessment_id
                                    WHERE a.learner_id=? AND s.course_id=? AND s.status='published'""", (learner_id, course_id)).fetchall()
            if any(a["passed"] != 1 for a in attempts) if attempts else True:
                raise ValueError("certificate_requires_passing_assessments")
            cert_id = new_id("CERT")
            number = certificate_no or cert_id
            c.execute("INSERT INTO certificates VALUES (?,?,?,?,?,?,?,?,?)",
                      (cert_id, learner_id, course_id, number, "issued", now(), None, 1,
                       json.dumps({"completion":"verified","assessments":"passed"})))
        result = self._row(c.execute("SELECT * FROM certificates WHERE certificate_id=?", (cert_id,)).fetchone())
        tenant_id, workspace_id = self._learner_scope(learner_id)
        self.events.publish("lms.certificate.issued", tenant_id, workspace_id, "system", "learner", learner_id, cert_id, {"course_id": course_id, "certificate_no": number})
        return result

    def publish_course(self, course_id, approver):
        if not approver: raise ValueError("approver_required")
        with self._db() as c:
            pending = c.execute("SELECT COUNT(*) n FROM lessons l JOIN modules m ON m.module_id=l.module_id WHERE m.course_id=? AND l.content_state NOT IN ('approved','published')", (course_id,)).fetchone()["n"]
            if pending:
                raise ValueError("all_lesson_content_requires_approval")
            c.execute("UPDATE courses SET status='published',updated_at=? WHERE course_id=?", (now(), course_id))
        return self.get_course(course_id)

    def get_programme(self, pid):
        with self._db() as c: return self._row(c.execute("SELECT * FROM programmes WHERE programme_id=?", (pid,)).fetchone())

    def get_course(self, cid):
        with self._db() as c:
            course = self._row(c.execute("SELECT * FROM courses WHERE course_id=?", (cid,)).fetchone())
            if course:
                course["modules"] = [self._row(x) for x in c.execute("SELECT * FROM modules WHERE course_id=? ORDER BY position", (cid,)).fetchall()]
        return course

    def dashboard(self, tenant_id, workspace_id):
        self._validate_scope(tenant_id, workspace_id)
        with self._db() as c:
            def n(sql, args=()): return c.execute(sql, args).fetchone()["n"]
            return {"programmes":n("SELECT COUNT(*) n FROM programmes WHERE tenant_id=? AND workspace_id=?",(tenant_id,workspace_id)),
                    "courses":n("SELECT COUNT(*) n FROM courses WHERE tenant_id=? AND workspace_id=?",(tenant_id,workspace_id)),
                    "learners":n("SELECT COUNT(*) n FROM learners WHERE tenant_id=? AND workspace_id=?",(tenant_id,workspace_id)),
                    "instructors":n("SELECT COUNT(*) n FROM instructors WHERE tenant_id=? AND workspace_id=?",(tenant_id,workspace_id)),
                    "enrolments":n("""SELECT COUNT(*) n FROM enrolments e JOIN learners l ON l.learner_id=e.learner_id
                                      WHERE l.tenant_id=? AND l.workspace_id=?""",(tenant_id,workspace_id)),
                    "completed":n("""SELECT COUNT(*) n FROM enrolments e JOIN learners l ON l.learner_id=e.learner_id
                                     WHERE l.tenant_id=? AND l.workspace_id=? AND e.status='completed'""",(tenant_id,workspace_id)),
                    "certificates":n("""SELECT COUNT(*) n FROM certificates c JOIN learners l ON l.learner_id=c.learner_id
                                       WHERE l.tenant_id=? AND l.workspace_id=? AND c.status='issued'""",(tenant_id,workspace_id)),
                    "ai_pending_review":n("""SELECT COUNT(*) n FROM ai_generations g JOIN courses c ON c.course_id=g.course_id
                                             WHERE c.tenant_id=? AND c.workspace_id=? AND g.human_reviewed=0""",(tenant_id,workspace_id))}

    def create_competency(self, tenant_id, workspace_id, name, description="", level="novice"):
        self._validate_scope(tenant_id, workspace_id)
        cid, ts = new_id("COMPETENCY"), now()
        with self._db() as c:
            c.execute("INSERT INTO competencies VALUES (?,?,?,?,?,?,?,?)", (cid, tenant_id, workspace_id, name, description, level, 1, ts))
        return self._row(c.execute("SELECT * FROM competencies WHERE competency_id=?", (cid,)).fetchone())

    def map_competency(self, course_id, competency_id, target_level="competent"):
        with self._db() as c:
            c.execute("INSERT OR REPLACE INTO course_competencies VALUES (?,?,?)", (course_id, competency_id, target_level))
        return {"course_id": course_id, "competency_id": competency_id, "target_level": target_level}

    def generate_course_blueprint(self, tenant_id, workspace_id, topic, audience, level, outcomes, duration, standards=None):
        self._validate_scope(tenant_id, workspace_id)
        if not str(topic).strip() or not str(audience).strip() or not str(level).strip():
            raise ValueError("topic_audience_level_required")
        outcomes = outcomes if isinstance(outcomes, list) else [outcomes]
        outcomes = [str(x).strip() for x in outcomes if str(x).strip()]
        if not outcomes:
            raise ValueError("learning_outcomes_required")
        course = self.create_course(tenant_id, workspace_id, f"{topic} — {level}", f"AI-generated draft for {audience}.")
        modules = []
        for i, outcome in enumerate(outcomes, 1):
            m = self.add_module(course["course_id"], f"Module {i}: {outcome}", f"Learning outcome: {outcome}", i)
            lesson_content = {"objective": outcome, "audience": audience, "level": level, "duration": duration,
                              "activities": ["guided practice", "real-world application"],
                              "assessment_alignment": outcome}
            lesson = self.add_lesson(m["module_id"], f"Lesson {i}.1: {outcome}", json.dumps(lesson_content, sort_keys=True), 1, True)
            assessment = self.create_assessment(course["course_id"], f"Module {i} Knowledge Check", 50, m["module_id"])
            question = self.add_question(assessment["assessment_id"], f"Explain or demonstrate: {outcome}", points=10)
            modules.append({"module": m, "lesson": lesson, "assessment": assessment, "question": question,
                            "activities": lesson_content["activities"],
                            "rubric": {"criteria": [outcome], "levels": ["developing","competent","proficient"]}})
        request = {"topic": topic, "audience": audience, "level": level, "outcomes": outcomes, "duration": duration, "standards": standards or []}
        blueprint = {"course_outline": course["title"], "modules": modules,
                     "quality_gates": ["learning_outcomes_present", "lesson_alignment", "assessment_alignment", "source_review", "human_review"],
                     "facilitator_guide": "Draft facilitator guide; human review required."}
        generation = self.generate_content(course["course_id"], json.dumps(request, sort_keys=True), json.dumps(blueprint, sort_keys=True), "governed-course-generator")
        return {"course": self.get_course(course["course_id"]), "modules": modules, "generation": generation,
                "workflow": ["draft","validate","human_review","approve","publish"], "requires_human_review": True,
                "quality_gates": blueprint["quality_gates"]}

    def create_avatar_session(self, tenant_id, workspace_id, learner_id, course_id=None, mode="tutor", context=None):
        self._validate_scope(tenant_id, workspace_id)
        sid, ts = new_id("AVATAR"), now()
        with self._db() as c:
            c.execute("INSERT INTO avatar_sessions VALUES (?,?,?,?,?,?,?,?,?,?,?)", (sid, tenant_id, workspace_id, learner_id, course_id, mode, json.dumps(context or {}), "[]", f"learner:{learner_id}", ts, ts))
        return self._row(c.execute("SELECT * FROM avatar_sessions WHERE session_id=?", (sid,)).fetchone())

    def append_avatar_message(self, session_id, role, message):
        with self._db() as c:
            row = c.execute("SELECT * FROM avatar_sessions WHERE session_id=?", (session_id,)).fetchone()
            if not row: raise ValueError("avatar_session_not_found")
            messages = json.loads(row["messages_json"])
            messages.append({"role": role, "message": message, "at": now()})
            c.execute("UPDATE avatar_sessions SET messages_json=?,updated_at=? WHERE session_id=?", (json.dumps(messages), now(), session_id))
        return self._row(c.execute("SELECT * FROM avatar_sessions WHERE session_id=?", (session_id,)).fetchone())

    def health(self):
        with self._db() as c:
            tables = [r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        return {"status":"ok","engine":"lms-training-management","database":self.db_path,
                "tables":len(tables),"ai_content_requires_review":True,
                "certificate_requires_completion":True,"grading_provenance_required":True,
                "credentials_exposed":False}
