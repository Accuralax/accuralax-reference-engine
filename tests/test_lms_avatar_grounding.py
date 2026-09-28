import json

from src.core.lms_avatar import LMSAvatar
from src.core.lms_training import LMSTraining


def test_avatar_responds_from_learner_context(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    learner = lms.create_learner("t1", "w1", "Learner One", "one@example.com")
    avatar = LMSAvatar(lms=lms)
    session = avatar.start_session("t1", "w1", learner["learner_id"])
    result = avatar.tutor_message(session["session"]["session_id"], "How is my progress?")
    assert result["status"] == "responded"
    assert "LMS record" in result["generated_response"]
    assert result["generation_requires_review"] is True


def test_avatar_rejects_empty_message(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    learner = lms.create_learner("t1", "w1", "Learner One", "one@example.com")
    avatar = LMSAvatar(lms=lms)
    session = avatar.start_session("t1", "w1", learner["learner_id"])
    try:
        avatar.tutor_message(session["session"]["session_id"], " ")
        assert False
    except ValueError as exc:
        assert str(exc) == "message_required"


def test_avatar_does_not_claim_mastery(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    learner = lms.create_learner("t1", "w1", "Learner One", "one@example.com")
    avatar = LMSAvatar(lms=lms)
    session = avatar.start_session("t1", "w1", learner["learner_id"])
    result = avatar.tutor_message(session["session"]["session_id"], "What are my skill gaps?")
    assert "Mastery should be confirmed" in result["generated_response"] or "knowledge check" in result["generated_response"]
