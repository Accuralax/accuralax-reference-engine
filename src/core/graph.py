from __future__ import annotations

from .bounded_graph import BoundedGraph, GraphPolicy, GraphState


def build_foundation_graph() -> BoundedGraph:
    """Build the deterministic foundation graph; LangGraph becomes the adapter later."""
    graph = BoundedGraph(GraphPolicy(max_iterations=12, max_retries_per_node=2))

    def safety(state: GraphState) -> GraphState:
        forbidden = ("password", "api key", "apikey", "authentication token", "card number")
        if any(item in state.request.lower() for item in forbidden):
            state.data["safety_status"] = "blocked_sensitive_request"
            state.terminal = True
        else:
            state.data["safety_status"] = "pass"
        return state

    def intake(state: GraphState) -> GraphState:
        state.data["intake_status"] = "ready"
        return state

    def route(state: GraphState) -> GraphState:
        from .service_router import ServiceRouter
        match = ServiceRouter().route(state.request)
        state.data["service_id"] = match.service_id if match else None
        state.data["routing_status"] = "matched" if match and match.service_id else "clarification_required"
        if not match or not match.service_id:
            state.terminal = True
        return state

    graph.add_node("safety_guard", safety)
    graph.add_node("intake", intake)
    graph.add_node("service_router", route)
    graph.add_edge("safety_guard", "intake")
    graph.add_edge("intake", "service_router")
    return graph


def run_foundation_graph(request: str) -> GraphState:
    return build_foundation_graph().run(GraphState(request=request), "safety_guard")
