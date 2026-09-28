from src.core.lms_training import LMSTraining


def test_generated_course_can_publish_only_after_human_approval(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    result = lms.generate_course_blueprint("t1", "w1", "Cybersecurity", "learners", "beginner", ["Identify threats"], "2 hours")
    course_id = result["course"]["course_id"]
    try:
        lms.publish_course(course_id, "approver")
        assert False, "publication must remain blocked before review"
    except ValueError as exc:
        assert str(exc) == "all_lesson_content_requires_approval"
    lms.review_content(result["generation"]["generation_id"], True, "reviewer-1")
    published = lms.publish_course(course_id, "approver")
    assert published["status"] == "published"
