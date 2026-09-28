from src.core.learning_intelligence import LearningIntelligence


def test_competency_and_assessment(tmp_path):
    li = LearningIntelligence(tmp_path / "learning.sqlite3")
    c = li.record_competency("L1", "Python", "developing", "practical task", 0.8)
    assert c["allowed"]
    a = li.submit_assessment("L1", "CRS-1", "quiz", 82, "attempt:1", reviewed=True)
    assert a["allowed"]


def test_course_generator_requires_review(tmp_path):
    li = LearningIntelligence(tmp_path / "learning.sqlite3")
    result = li.generate_course("Cybersecurity Fundamentals", "youth", "beginner",
                                ["Explain threats", "Apply safe practices"], "10 weeks")
    assert result["allowed"]
    assert result["review_required"]
    assert result["state"] == "draft"


def test_avatar_and_learning_gap(tmp_path):
    li = LearningIntelligence(tmp_path / "learning.sqlite3")
    li.record_competency("L1", "Python", "competent", "project", 0.9)
    context = li.avatar_context("L1", "CRS-1")
    assert context["approved_knowledge_only"]
    gaps = li.learning_gap("L1", ["Python", "Cybersecurity"])
    assert gaps["gaps"] == ["Cybersecurity"]
