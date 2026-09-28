import pytest
from src.core.lms_training import LMSTraining


def test_course_generator_builds_aligned_learning_assets(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    result = lms.generate_course_blueprint("t1", "w1", "AI Fundamentals", "adult learners", "beginner", ["Explain AI", "Apply safe AI"], "10 hours", ["UNESCO"])
    assert result["requires_human_review"] is True
    assert "assessment_alignment" in result["quality_gates"]
    assert len(result["modules"]) == 2
    assert all(x["assessment"]["course_id"] == result["course"]["course_id"] for x in result["modules"])
    assert result["generation"]["human_reviewed"] == 0


def test_course_generator_validates_outcomes(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    with pytest.raises(ValueError, match="learning_outcomes_required"):
        lms.generate_course_blueprint("t1", "w1", "AI", "learners", "beginner", [], "1 hour")
