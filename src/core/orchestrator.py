from __future__ import annotations

from dataclasses import dataclass

from .agent_context import build_context_for_state
from .conversation import ConversationEngine, ConversationState
from .session_store import ConversationStore, InMemoryConversationStore


@dataclass(frozen=True)
class OrchestrationResult:
    state: ConversationState
    agent_context: str


class ConversationOrchestrator:
    """Single application boundary for session-aware deterministic orchestration."""

    def __init__(self, store: ConversationStore | None = None) -> None:
        self.store = store or InMemoryConversationStore()
        self.engine = ConversationEngine()

    def start(self, request: str) -> OrchestrationResult:
        state = self.engine.start(request)
        self.store.save(state)
        return OrchestrationResult(state, build_context_for_state(state))

    def continue_with_information(
        self,
        reference_id: str,
        field: str,
        value: str,
    ) -> OrchestrationResult:
        state = self._require(reference_id)
        self.engine.record_information(state, field, value)
        self.store.save(state)
        return OrchestrationResult(state, build_context_for_state(state))

    def continue_with_consent(
        self,
        reference_id: str,
        consent: bool,
    ) -> OrchestrationResult:
        state = self._require(reference_id)
        self.engine.record_consent(state, consent)
        self.store.save(state)
        return OrchestrationResult(state, build_context_for_state(state))

    def assign_owner(self, reference_id: str) -> OrchestrationResult:
        state = self._require(reference_id)
        self.engine.assign_owner(state)
        self.store.save(state)
        return OrchestrationResult(state, build_context_for_state(state))

    def get(self, reference_id: str) -> OrchestrationResult:
        state = self._require(reference_id)
        return OrchestrationResult(state, build_context_for_state(state))

    def _require(self, reference_id: str) -> ConversationState:
        state = self.store.load(reference_id)
        if state is None:
            raise KeyError(f"Unknown reference_id: {reference_id}")
        return state
