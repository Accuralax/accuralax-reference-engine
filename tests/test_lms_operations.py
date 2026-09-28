from src.core.lms_training import LMSTraining
from src.core.lms_operations import LMSOperations


def test_tms_operations_lifecycle(tmp_path):
    lms = LMSTraining(str(tmp_path / 'tms.sqlite3'))
    p = lms.create_programme('t1', 'w1', 'Programme')
    course = lms.create_course('t1', 'w1', 'Course', programme_id=p['programme_id'])
    cohort = lms.create_cohort(course['course_id'], 'Cohort A')
    instructor = lms.create_instructor('t1', 'w1', 'Instructor', authorised=True)
    learner = lms.create_learner('t1', 'w1', 'Learner')
    lms.enrol(learner['learner_id'], course['course_id'], cohort['cohort_id'])

    assignment = lms.assign_instructor('t1', 'w1', cohort['cohort_id'], instructor['instructor_id'])
    assert assignment['status'] == 'active'

    session = lms.schedule_session('t1', 'w1', cohort['cohort_id'], 'Session 1', '2026-10-01T09:00:00+02:00', '2026-10-01T10:00:00+02:00', instructor['instructor_id'])
    assert session['status'] == 'scheduled'

    roster = lms.cohort_roster('t1', 'w1', cohort['cohort_id'])
    assert len(roster['learners']) == 1
    assert len(roster['instructors']) == 1
    assert len(roster['sessions']) == 1

    assessment = lms.create_assessment(course['course_id'], 'Assessment')
    updated = lms.set_assessment_status('t1', 'w1', assessment['assessment_id'], 'published')
    assert updated['status'] == 'published'

    dashboard = LMSOperations(lms).operations_dashboard('t1', 'w1')
    assert dashboard['active_assignments'] == 1
    assert dashboard['scheduled_sessions'] == 1
    assert dashboard['unassigned_cohorts'] == 0
