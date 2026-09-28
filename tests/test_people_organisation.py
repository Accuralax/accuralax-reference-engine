from src.core.people_organisation import PeopleOrganisation


def test_people_health():
    p = PeopleOrganisation()
    assert p.health()["status"] == "ok"
    assert p.health()["credentials_exposed"] is False


def test_people_structure_and_leave():
    p = PeopleOrganisation()
    person = p.create_person("Team Member", "Operator")
    team = p.create_team("AI Operations", "Technology")
    role = p.define_role("Operator", ["read", "execute_bounded"])
    assignment = p.assign(person["person_id"], team["team_id"], "AI operations")
    leave = p.request_leave(person["person_id"], "2026-10-01", "2026-10-03")
    blocked = p.approve_leave(leave["leave_id"])
    approved = p.approve_leave(leave["leave_id"], approved=True)
    assert role["name"] == "Operator"
    assert assignment["status"] == "active"
    assert blocked["allowed"] is False
    assert approved["status"] == "approved"


def test_hr_decision_requires_human_review():
    p = PeopleOrganisation()
    person = p.create_person("Team Member", "Operator")
    blocked = p.create_hr_case(person["person_id"], "disciplinary", "Case summary")
    assert blocked["allowed"] is False
    assert blocked["policy"]["outcome"] == "awaiting_human_review"
