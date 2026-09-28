from src.core.lms_training import LMSTraining
from src.core.lms_time import localize


def test_session_is_stored_as_utc_and_localized(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    course = lms.create_course("t1", "w1", "Course")
    cohort = lms.create_cohort(course["course_id"], "Cohort")
    session = lms.schedule_session(
        "t1", "w1", cohort["cohort_id"], "Session",
        "2026-10-01T09:00:00+02:00", "2026-10-01T10:30:00+02:00"
    )
    assert session["scheduled_start"] == "2026-10-01T07:00:00+00:00"
    view = lms.session_view("t1", "w1", session["session_id"], "Europe/Berlin")
    assert view["scheduled_start_local"] == "2026-10-01T09:00:00+02:00"
    assert view["scheduled_end_local"] == "2026-10-01T10:30:00+02:00"
    assert view["scheduled_start_utc"] == "2026-10-01T07:00:00+00:00"


def test_dst_conversion_uses_iana_timezone():
    before = localize("2026-03-29T00:30:00+00:00", "Europe/Berlin")
    after = localize("2026-03-29T01:30:00+00:00", "Europe/Berlin")
    assert before.strftime("%z") == "+0100"
    assert after.strftime("%z") == "+0200"


def test_update_session_normalizes_to_utc(tmp_path):
    lms = LMSTraining(str(tmp_path / "lms.sqlite3"))
    course = lms.create_course("t1", "w1", "Course")
    cohort = lms.create_cohort(course["course_id"], "Cohort")
    session = lms.schedule_session(
        "t1", "w1", cohort["cohort_id"], "Session",
        "2026-10-01T09:00:00+02:00", "2026-10-01T10:00:00+02:00"
    )
    updated = lms.update_session(
        "t1", "w1", session["session_id"],
        scheduled_start="2026-10-01T11:00:00+02:00",
        scheduled_end="2026-10-01T12:00:00+02:00"
    )
    assert updated["scheduled_start"] == "2026-10-01T09:00:00+00:00"
    assert updated["scheduled_end"] == "2026-10-01T10:00:00+00:00"
