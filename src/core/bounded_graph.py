from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class GraphState:
    """Small framework-neutral state object for the first orchestration graph."""
    request: str
    data: dict[str, Any] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)
    iterations: int = 0
    terminal: bool = False
    error: str | None = None


@dataclass(frozen=True)
class GraphPolicy:
    max_iterations: int = 8
    max_retries_per_node: int = 2


Node = Callable[[GraphState], GraphState]


class BoundedGraph:
    """Minimal bounded state-machine abstraction ready for a LangGraph adapter."""

    def __init__(self, policy: GraphPolicy | None = None) -> None:
        self.policy = policy or GraphPolicy()
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, str] = {}

    def add_node(self, name: str, node: Node) -> None:
        self.nodes[name] = node

    def add_edge(self, source: str, target: str) -> None:
        self.edges[source] = target

    def run(self, state: GraphState, start: str) -> GraphState:
        current = start
        retries: dict[str, int] = {}
        seen: set[tuple[str, str]] = set()
        while not state.terminal:
            if state.iterations >= self.policy.max_iterations:
                state.error = "max_iterations_exceeded"
                state.terminal = True
                break
            if current not in self.nodes:
                state.error = f"unknown_node:{current}"
                state.terminal = True
                break
            signature = (current, repr(sorted(state.data.items())))
            if signature in seen:
                state.error = "cycle_detected"
                state.terminal = True
                break
            seen.add(signature)
            try:
                state.history.append(current)
                state = self.nodes[current](state)
                state.iterations += 1
                current = self.edges.get(current, "")
                if not current:
                    state.terminal = True
            except Exception as exc:
                retries[current] = retries.get(current, 0) + 1
                if retries[current] > self.policy.max_retries_per_node:
                    state.error = f"node_failed:{current}:{type(exc).__name__}"
                    state.terminal = True
                else:
                    state.data["last_error"] = str(exc)
        return state
