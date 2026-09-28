from src.core.lms_avatar import LMSAvatar
from src.core.lms_training import LMSTraining


def setup(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    course = lms.create_course("t1", "w1", "AI Fundamentals")
    module = lms.add_module(course["course_id"], "AI Basics")
    lesson = lms.add_lesson(module["module_id"], "What is AI?", "AI systems perform tasks that normally require human intelligence.", ai_generated=True)
    learner = lms.create_learner("t1", "w1", "Learner")
    avatar = LMSAvatar(lms=lms)
    session = avatar.start_session("t1", "w1", learner["learner_id"], course["course_id"])
    return lms, avatar, session, learner, course, lesson


def test_avatar_v2_requires_approved_grounding(tmp_path):
    lms, avatar, session, learner, course, lesson = setup(tmp_path)
    result = avatar.tutor_message_v2(session["session"]["session_id"], "Explain AI")
    assert result["evidence"] == []
    assert "approved course evidence" in result["generated_response"]
    with lms._db() as db:
        db.execute("UPDATE lessons SET content_state='approved' WHERE lesson_id=?", (lesson["lesson_id"],))
    result = avatar.tutor_message_v2(session["session"]["session_id"], "Explain AI")
    assert result["evidence_ids"] == [lesson["lesson_id"]]
    assert "AI systems" in result["generated_response"]


def test_avatar_v2_records_learning_event_and_knowledge_check(tmp_path):
    lms, avatar, session, learner, course, lesson = setup(tmp_path)
    with lms._db() as db:
        db.execute("UPDATE lessons SET content_state='approved' WHERE lesson_id=?", (lesson["lesson_id"],))
    sid = session["session"]["session_id"]
    result = avatar.tutor_message_v2(sid, "Give me a practice question")
    assert result["intent"] == "knowledge_check"
    check = avatar.request_knowledge_check(sid, lesson["lesson_id"])
    assert check["requires_assessment_for_mastery"] is True
    with lms._db() as db:
        count = db.execute("SELECT COUNT(*) n FROM learning_events WHERE learner_id=?", (learner["learner_id"],)).fetchone()["n"]
    assert count >= 2


def test_avatar_v2_cannot_cross_course_boundary(tmp_path):
    lms, avatar, session, learner, course, lesson = setup(tmp_path)
    other = lms.create_course("t1", "w1", "Other Course")
    module = lms.add_module(other["course_id"], "Other")
    other_lesson = lms.add_lesson(module["module_id"], "Secret", "Private material", ai_generated=False)
    with lms._db() as db:
        db.execute("UPDATE lessons SET content_state='approved' WHERE lesson_id=?", (other_lesson["lesson_id"],))
    result = avatar.tutor_message_v2(session["session"]["session_id"], "Private material")
    assert result["evidence"] == []
