import pytest
from src.core.lms_training import LMSTraining


def test_lms_learning_lifecycle(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    p = lms.create_programme("t1", "w1", "Cybersecurity Programme")
    c = lms.create_course("t1", "w1", "Cybersecurity Fundamentals", programme_id=p["programme_id"])
    m = lms.add_module(c["course_id"], "Module 1")
    lesson = lms.add_lesson(m["module_id"], "Security Basics", "content")
    learner = lms.create_learner("t1", "w1", "Learner One")
    cohort = lms.create_cohort(c["course_id"], "Cohort A")
    enrollment = lms.enrol(learner["learner_id"], c["course_id"], cohort["cohort_id"])
    assert enrollment["status"] == "active"
    lms.record_progress(learner["learner_id"], c["course_id"], 100, lesson["lesson_id"])
    assert lms.dashboard("t1", "w1")["completed"] == 1


def test_ai_content_requires_review(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    c = lms.create_course("t1", "w1", "AI Course")
    g = lms.generate_content(c["course_id"], "create lesson", "Generated lesson")
    assert g["content_state"] == "generated"
    assert g["human_reviewed"] == 0
    reviewed = lms.review_content(g["generation_id"], True, "instructor-1")
    assert reviewed["content_state"] == "approved"
    assert reviewed["human_reviewed"] == 1


def test_certificate_requires_completion_and_passed_assessment(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    c = lms.create_course("t1", "w1", "Certification Course")
    learner = lms.create_learner("t1", "w1", "Learner")
    lms.enrol(learner["learner_id"], c["course_id"])
    with pytest.raises(ValueError, match="verified_completion"):
        lms.issue_certificate(learner["learner_id"], c["course_id"])
    lms.record_progress(learner["learner_id"], c["course_id"], 100)
    a = lms.create_assessment(c["course_id"], "Final", high_impact=True)
    with pytest.raises(ValueError, match="passing_assessments"):
        lms.issue_certificate(learner["learner_id"], c["course_id"])
    with lms._db() as db:
        db.execute("UPDATE assessments SET status='published' WHERE assessment_id=?", (a["assessment_id"],))
    attempt = lms.submit_attempt(a["assessment_id"], learner["learner_id"], {"q1": "A"})
    lms.grade_attempt(attempt["attempt_id"], 80, True, "instructor", "human_review")
    cert = lms.issue_certificate(learner["learner_id"], c["course_id"])
    assert cert["status"] == "issued"


def test_tenant_dashboard_is_scoped(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    lms.create_course("tenant-a", "workspace-a", "Private Course")
    lms.create_learner("tenant-a", "workspace-a", "A")
    lms.create_course("tenant-b", "workspace-b", "Other Course")
    assert lms.dashboard("tenant-a", "workspace-a")["courses"] == 1
    assert lms.dashboard("tenant-a", "workspace-a")["learners"] == 1
