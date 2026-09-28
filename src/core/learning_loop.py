from __future__ import annotations

from typing import Any
from .langgraph_checkpoint import LangGraphCheckpointStore
from .persistent_memory import PersistentMemory


class GovernedLearningLoop:
    """Bounded reflection/learning loop; policy remains higher priority than memory."""

    def __init__(self, max_iterations: int = 3) -> None:
        self.max_iterations = max(1, min(max_iterations, 5))
        self.checkpoints = LangGraphCheckpointStore()
        self.memory = PersistentMemory()

    def run(self, reference_id: str, agent_id: str, state: dict[str, Any],
            outcome: str, *, verified: bool = False) -> dict[str, Any]:
        iterations = 0
        checkpoints = []
        current = dict(state)
        while iterations < self.max_iterations:
            node = f"reflection_{iterations + 1}"
            cp = self.checkpoints.save(reference_id, node, current)
            checkpoints.append(cp.checkpoint_id)
            iterations += 1
            if verified:
                break
            current["learning_status"] = "awaiting_verification"
            break

        consolidated = False
        if verified:
            result = self.memory.consolidate(agent_id)
            consolidated = result["allowed"]

        return {
            "reference_id": reference_id,
            "agent_id": agent_id,
            "iterations": iterations,
            "max_iterations": self.max_iterations,
            "checkpoint_ids": checkpoints,
            "learning_status": "consolidated" if consolidated else "awaiting_verification",
            "policy_precedence": True,
            "credentials_exposed": False,
            "outcome": outcome,
        }

    def resume(self, reference_id: str) -> dict[str, Any]:
        checkpoint = self.checkpoints.latest(reference_id)
        if not checkpoint:
            return {"resumable": False, "reason": "checkpoint_not_found"}
        return {"resumable": True, "checkpoint": checkpoint.state,
                "node": checkpoint.node, "credentials_exposed": False}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "max_iterations": self.max_iterations,
                "checkpoints": self.checkpoints.health(),
                "memory": self.memory.health(),
                "credentials_exposed": False}
