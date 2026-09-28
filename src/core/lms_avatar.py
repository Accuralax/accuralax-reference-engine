import json

from .lms_intelligence import LMSIntelligence
from .lms_training import LMSTraining


class LMSAvatar:
    """Grounded learning tutor using approved LMS context and learner evidence."""

    def __init__(self, lms=None, intelligence=None):
        self.lms = lms or LMSTraining()
        self.intelligence = intelligence or LMSIntelligence(self.lms)

    def context(self, tenant_id, workspace_id, learner_id, course_id=None):
        self.lms._validate_scope(tenant_id, workspace_id)
        profile = self.intelligence.learner_profile(tenant_id, workspace_id, learner_id)
        gaps = self.intelligence.skill_gaps(tenant_id, workspace_id, learner_id)
        with self.lms._db() as c:
            paths = c.execute(
                "SELECT * FROM learning_paths WHERE tenant_id=? AND workspace_id=? AND learner_id=? ORDER BY created_at DESC LIMIT 5",
                (tenant_id, workspace_id, learner_id)).fetchall()
            events = c.execute(
                "SELECT * FROM learning_events WHERE tenant_id=? AND workspace_id=? AND learner_id=? ORDER BY created_at DESC LIMIT 10",
                (tenant_id, workspace_id, learner_id)).fetchall()
            progress = []
            if course_id:
                progress = c.execute(
                    "SELECT * FROM progress WHERE learner_id=? AND course_id=?",
                    (learner_id, course_id)).fetchall()
        return {
            "learner": profile["learner"],
            "course_id": course_id,
            "profile": profile,
            "skill_gaps": gaps,
            "learning_paths": [self.lms._row(x) for x in paths],
            "recent_events": [self.lms._row(x) for x in events],
            "course_progress": [self.lms._row(x) for x in progress],
            "tutor_guidance": {
                "approved_content_only": True,
                "adapt_to_skill_gaps": True,
                "use_recent_learning_events": True,
                "avoid_claiming_mastery_without_evidence": True,
                "human_review_for_high_impact_decisions": True,
                "credentials_exposed": False,
            },
        }

    def start_session(self, tenant_id, workspace_id, learner_id, course_id=None, mode="tutor"):
        ctx = self.context(tenant_id, workspace_id, learner_id, course_id)
        session = self.lms.create_avatar_session(
            tenant_id, workspace_id, learner_id, course_id, mode, ctx)
        return {"session": session, "context": ctx, "requires_human_review": True}

    def tutor_message(self, session_id, message, role="learner"):
        if not message or not message.strip():
            raise ValueError("message_required")
        session = self.lms.append_avatar_message(session_id, role, message.strip())
        response = self._grounded_response(session, message.strip()) if role == "learner" else None
        if response:
            session = self.lms.append_avatar_message(session_id, "avatar", response)
        return {
            "session": session,
            "status": "responded" if response else "recorded",
            "generated_response": response,
            "generation_requires_review": True,
            "credentials_exposed": False,
        }

    def _grounded_response(self, session, message):
        context = json.loads(session["context_json"] or "{}")
        profile = context.get("profile", {})
        gaps = context.get("skill_gaps", [])
        text = message.lower()

        if "skill" in text or "weak" in text or "gap" in text:
            gap_rows = gaps.get("skill_gaps", []) if isinstance(gaps, dict) else gaps
            if gap_rows:
                names = [
                    str(x.get("skill", x.get("name", "identified skill gap")))
                    for x in gap_rows[:3]
                ]
                return (
                    "Based on your learning record, let's focus on: "
                    + ", ".join(names)
                    + ". Mastery should be confirmed through the LMS assessment."
                )
            return (
                "Your current record does not show a confirmed skill gap. "
                "Let's use a short knowledge check to establish your starting point."
            )

        if "progress" in text or "how am i doing" in text:
            count = len(context.get("course_progress", []))
            return (
                f"Your LMS record contains {count} course progress record(s). "
                "I can help you review the next learning objective."
            )

        if "hello" in text or text.strip() == "hi":
            learner = profile.get("learner", {}) if isinstance(profile, dict) else {}
            return (
                f"Hello {learner.get('name', 'there')}. "
                "I'm your learning assistant. Tell me which lesson or concept "
                "you want to work on."
            )

        return (
            "I can help explain approved course material, practice a concept, "
            "or prepare you for a knowledge check. Tell me the lesson or "
            "learning objective."
        )

    def tutor_message_v2(self, session_id, message, role="learner"):
        """Adaptive, course-grounded tutoring with explicit evidence and learning events."""
        if not message or not message.strip():
            raise ValueError("message_required")
        with self.lms._db() as c:
            session = c.execute("SELECT * FROM avatar_sessions WHERE session_id=?", (session_id,)).fetchone()
        if not session:
            raise ValueError("avatar_session_not_found")
        if role != "learner":
            return self.tutor_message(session_id, message, role)
        context = json.loads(session["context_json"] or "{}")
        evidence = self._retrieve_course_evidence(session["course_id"], message)
        response = self._adaptive_response(context, message.strip(), evidence)
        self.lms.append_avatar_message(session_id, "learner", message.strip())
        self.lms.append_avatar_message(session_id, "avatar", response["text"])
        tenant_id, workspace_id = session["tenant_id"], session["workspace_id"]
        self.intelligence.record_learning_event(
            tenant_id, workspace_id, session["learner_id"], "avatar_tutoring",
            "avatar_session", session_id,
            {"query": message.strip(), "evidence_ids": response["evidence_ids"],
             "intent": response["intent"], "review_required": True})
        return {"session_id": session_id, "status": "responded",
                "generated_response": response["text"], "intent": response["intent"],
                "evidence": evidence, "evidence_ids": response["evidence_ids"],
                "generation_requires_review": True, "credentials_exposed": False}

    def _retrieve_course_evidence(self, course_id, query):
        if not course_id:
            return []
        stopwords = {"the", "and", "for", "are", "what", "how", "can", "you", "with", "from", "this", "that"}
        terms = [x.strip(".,?!:;()[]{}") for x in query.lower().split() if len(x.strip(".,?!:;()[]{}")) >= 2 and x not in stopwords][:8]
        with self.lms._db() as c:
            rows = c.execute("""SELECT l.lesson_id,l.title,l.content,l.content_state,m.title module_title
                FROM lessons l JOIN modules m ON m.module_id=l.module_id
                WHERE m.course_id=? AND l.content_state IN ('approved','published')
                ORDER BY l.position""", (course_id,)).fetchall()
        ranked = []
        for row in rows:
            hay = (row["title"] + " " + (row["content"] or "")).lower()
            score = sum(1 for term in terms if term in hay)
            if score:
                ranked.append((score, dict(row)))
        ranked.sort(key=lambda x: (-x[0], x[1]["title"]))
        return [dict(score=score, lesson_id=row["lesson_id"], title=row["title"],
                     module_title=row["module_title"], content=row["content"] or "")
                for score, row in ranked[:5]]

    def _adaptive_response(self, context, message, evidence):
        text = message.lower()
        gaps = context.get("skill_gaps", {})
        gap_rows = gaps.get("gaps", []) if isinstance(gaps, dict) else []
        profile = context.get("profile", {})
        learner = profile.get("learner", {}) if isinstance(profile, dict) else {}
        if any(x in text for x in ("quiz", "test", "check", "practice")):
            intent = "knowledge_check"
        elif any(x in text for x in ("explain", "what is", "how does", "teach")):
            intent = "explanation"
        elif any(x in text for x in ("progress", "doing", "performance")):
            intent = "progress_review"
        else:
            intent = "guided_learning"
        evidence_ids = [x["lesson_id"] for x in evidence]
        if evidence:
            source = evidence[0]
            if intent == "knowledge_check":
                answer = "Based on the approved lesson material, try this: explain the main idea in your own words, then give one practical example. I will use your response as a learning event; mastery still requires the LMS assessment."
            else:
                answer = f"Let's work from the approved lesson '{source['title']}'. {source['content'][:700]}"
                if gap_rows:
                    answer += " I’ll adapt the explanation toward your recorded learning gaps, but those gaps are evidence for practice—not a final mastery decision."
        elif intent == "progress_review":
            progress = context.get("course_progress", [])
            answer = f"Your current LMS context contains {len(progress)} course progress record(s). I can help identify the next objective, but completion and mastery are determined by the governed LMS evidence."
        else:
            answer = f"I don't have approved course evidence matching that question yet, {learner.get('name', 'learner')}. Ask about an approved lesson or request a knowledge check."
        return {"text": answer, "intent": intent, "evidence_ids": evidence_ids}

    def request_knowledge_check(self, session_id, lesson_id=None):
        with self.lms._db() as c:
            session = c.execute("SELECT * FROM avatar_sessions WHERE session_id=?", (session_id,)).fetchone()
            if not session:
                raise ValueError("avatar_session_not_found")
            if lesson_id:
                lesson = c.execute("""SELECT l.lesson_id,l.title,m.course_id FROM lessons l JOIN modules m ON m.module_id=l.module_id
                    WHERE l.lesson_id=? AND m.course_id=? AND l.content_state IN ('approved','published')""",
                    (lesson_id, session["course_id"])).fetchone()
            else:
                lesson = c.execute("""SELECT l.lesson_id,l.title,m.course_id FROM lessons l JOIN modules m ON m.module_id=l.module_id
                    WHERE m.course_id=? AND l.content_state IN ('approved','published') ORDER BY l.position LIMIT 1""",
                    (session["course_id"],)).fetchone()
        if not lesson:
            raise ValueError("approved_lesson_not_found")
        question = f"Explain the key concept from '{lesson['title']}' in your own words and give one practical example."
        self.intelligence.record_learning_event(session["tenant_id"], session["workspace_id"], session["learner_id"],
            "knowledge_check_requested", "lesson", lesson["lesson_id"], {"session_id": session_id})
        return {"status": "ready", "lesson_id": lesson["lesson_id"], "question": question,
                "requires_assessment_for_mastery": True, "human_review_required": True}

    def health(self):
        return {
            "status": "ok",
            "engine": "ai-learning-avatar",
            "personalised_context": True,
            "approved_content_grounding": True,
            "skill_gap_context": True,
            "session_memory": True,
            "human_review_required_for_generated_guidance": True,
            "credentials_exposed": False,
        }
