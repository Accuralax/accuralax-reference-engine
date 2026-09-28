from src.core.project_portfolio import ProjectPortfolio


def test_project_portfolio_health():
    pm = ProjectPortfolio()
    assert pm.health()["status"] == "ok"
    assert pm.health()["credentials_exposed"] is False


def test_project_activation_requires_approval():
    pm = ProjectPortfolio()
    project = pm.create_project("Platform Build", 100000)
    blocked = pm.activate_project(project["project_id"])
    assert blocked["allowed"] is False
    allowed = pm.activate_project(project["project_id"], approved=True)
    assert allowed["allowed"] is True
    assert allowed["status"] == "active"


def test_project_structure_and_risk():
    pm = ProjectPortfolio()
    project = pm.create_project("R&D")
    task = pm.add_task(project["project_id"], "Architecture")
    milestone = pm.add_milestone(project["project_id"], "Foundation")
    dependency = pm.add_dependency(project["project_id"], "Knowledge layer")
    risk = pm.add_risk(project["project_id"], "Schedule risk", "high")
    assert task["status"] == "backlog"
    assert milestone["status"] == "planned"
    assert dependency["dependency"] == "Knowledge layer"
    assert risk["status"] == "open"
    assert pm.portfolio_health()["status"] == "amber"
