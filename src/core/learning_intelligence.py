from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import sqlite3
import uuid
import yaml


class LearningIntelligence:
    """Competency, assessment, AI-avatar and governed course-generation intelligence."""

    def __init__(self, db_path: str | Path = Path("data") / "learning_intelligence.sqlite3") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        root = Path(__file__).resolve().parents[1]
        self.config = yaml.safe_load((root / "config" / "learning_intelligence.yaml").read_text(encoding="utf-8")) or {}
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS competencies (
                competency_id TEXT PRIMARY KEY, learner_id TEXT, skill TEXT,
                level TEXT, evidence TEXT, confidence REAL, updated_at TEXT
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS assessments (
                assessment_id TEXT PRIMARY KEY, learner_id TEXT, course_id TEXT,
                assessment_type TEXT, score REAL, provenance TEXT, reviewed INTEGER
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS generated_courses (
                generation_id TEXT PRIMARY KEY, topic TEXT, audience TEXT, level TEXT,
                outcomes TEXT, draft TEXT, content_hash TEXT, state TEXT, created_at TEXT
            )""")
            db.commit()

    def record_competency(self, learner_id: str, skill: str, level: str,
                          evidence: str, confidence: float = 0.5) -> dict[str, Any]:
        allowed = self.config["competency"]["levels"]
        if level not in allowed or not evidence.strip():
            return {"allowed": False, "reason": "valid_level_and_evidence_required"}
        cid = f"CMP-{uuid.uuid4().hex[:10].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO competencies VALUES(?,?,?,?,?,?,?)",
                       (cid, learner_id, skill, level, evidence,
                        max(0, min(1, confidence)), now))
            db.commit()
        return {"allowed": True, "competency_id": cid, "level": level}

    def submit_assessment(self, learner_id: str, course_id: str,
                          assessment_type: str, score: float, provenance: str,
                          reviewed: bool = False) -> dict[str, Any]:
        if assessment_type not in self.config["assessment"]["types"]:
            return {"allowed": False, "reason": "invalid_assessment_type"}
        if not provenance:
            return {"allowed": False, "reason": "provenance_required"}
        aid = f"ASM-{uuid.uuid4().hex[:10].upper()}"
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO assessments VALUES(?,?,?,?,?,?,?)",
                       (aid, learner_id, course_id, assessment_type,
                        max(0, min(100, score)), provenance, int(reviewed)))
            db.commit()
        return {"allowed": True, "assessment_id": aid, "reviewed": reviewed}

    def generate_course(self, topic: str, audience: str, level: str,
                        outcomes: list[str], duration: str) -> dict[str, Any]:
        if not topic.strip() or not audience.strip() or not outcomes:
            return {"allowed": False, "reason": "topic_audience_outcomes_required"}
        draft = {
            "title": topic,
            "audience": audience,
            "level": level,
            "duration": duration,
            "outcomes": outcomes,
            "modules": [
                {"title": f"Introduction to {topic}", "learning_outcomes": outcomes},
                {"title": f"Applied {topic}", "learning_outcomes": outcomes},
                {"title": f"{topic} Assessment", "learning_outcomes": outcomes},
            ],
            "activities": ["guided practice", "reflection", "practical activity"],
            "assessment": {"type": "quiz", "requires_human_review": True},
            "facilitator_guide_required": True,
        }
        body = json.dumps(draft, sort_keys=True)
        gid = f"GEN-{uuid.uuid4().hex[:10].upper()}"
        digest = hashlib.sha256(body.encode()).hexdigest()
        with sqlite3.connect(self.db_path) as db:
            db.execute("INSERT INTO generated_courses VALUES(?,?,?,?,?,?,?,?,?)",
                       (gid, topic, audience, level, json.dumps(outcomes), body,
                        digest, "draft", datetime.now(timezone.utc).isoformat()))
            db.commit()
        return {"allowed": True, "generation_id": gid, "state": "draft",
                "review_required": True, "content_hash": digest, "course": draft}

    def avatar_context(self, learner_id: str, course_id: str) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            competencies = db.execute(
                "SELECT skill,level,confidence FROM competencies WHERE learner_id=?",
                (learner_id,)).fetchall()
            assessments = db.execute(
                "SELECT assessment_type,score,reviewed FROM assessments WHERE learner_id=? AND course_id=?",
                (learner_id, course_id)).fetchall()
        return {
            "learner_id": learner_id,
            "course_id": course_id,
            "mode": "tutor_coach_mentor_study_companion",
            "competencies": [{"skill": x[0], "level": x[1], "confidence": x[2]} for x in competencies],
            "assessments": [{"type": x[0], "score": x[1], "reviewed": bool(x[2])} for x in assessments],
            "approved_knowledge_only": True,
            "credentials_exposed": False,
        }

    def learning_gap(self, learner_id: str, required_skills: list[str]) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            rows = db.execute("SELECT skill,level,confidence FROM competencies WHERE learner_id=?",
                              (learner_id,)).fetchall()
        mastered = {r[0] for r in rows if r[1] in {"competent", "proficient", "advanced"} and r[2] >= 0.7}
        gaps = [skill for skill in required_skills if skill not in mastered]
        return {"learner_id": learner_id, "required": required_skills,
                "gaps": gaps, "recommendation_requires_evidence": True}

    def health(self) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as db:
            counts = [db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                      for t in ("competencies", "assessments", "generated_courses")]
        return {"status": "ok", "competencies": counts[0], "assessments": counts[1],
                "generated_courses": counts[2], "ai_review_required": True,
                "credentials_exposed": False}
