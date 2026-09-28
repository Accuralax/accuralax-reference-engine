# Ω-8.3 Agent Planning + Replanning Convergence
# Canonical flow: signal -> decision -> agent selection -> plan -> evaluate -> replan -> governance -> approval -> execution

from datetime import datetime, timezone

class AgentPlanningConvergence:
    """Bounded convergence coordinator; execution remains behind approval/governance."""
    def __init__(self, signal_fabric, decision_engine, planner, replanner, governance=None, approval_gate=None, executor=None, max_agents=3, max_cycles=3):
        self.signals = signal_fabric
        self.decisions = decision_engine
        self.planner = planner
        self.replanner = replanner
        self.governance = governance
        self.approval_gate = approval_gate
        self.executor = executor
        self.max_agents = max(1, min(int(max_agents), 10))
        self.max_cycles = max(1, min(int(max_cycles), 10))

    def select_agent(self, candidates):
        candidates = list(candidates or [])[:self.max_agents]
        usable = [c for c in candidates if c.get("enabled", True) and c.get("status", "active") == "active"]
        if not usable:
            return {"status": "blocked", "reason": "no_active_agent"}
        chosen = sorted(usable, key=lambda c: (-float(c.get("confidence", 0)), str(c.get("agent_id", ""))))[0]
        return {"status": "selected", "agent_id": str(chosen["agent_id"]), "candidates_considered": len(candidates)}

    def evaluate(self, plan, decision):
        actions = plan.get("actions", [])
        if not actions:
            return {"status": "blocked", "reason": "empty_plan"}
        if decision.get("status") not in {"approved", "approval_required"}:
            return {"status": "blocked", "reason": "decision_not_ready"}
        return {"status": "ready", "action_count": len(actions), "bounded": True}

    def replan(self, tenant_id, workspace_id, source_plan_id, lead=None, opportunity=None, consent_granted=False, open_tasks=0):
        return self.replanner.propose(tenant_id, workspace_id, source_plan_id, lead, opportunity, consent_granted, open_tasks)

    def health(self):
        return {"status": "ok", "engine": "agent-planning-convergence", "bounded": True, "max_agents": self.max_agents, "max_cycles": self.max_cycles, "execution_separate": True, "approval_boundary": True}

    def run(self, event, candidates, lead=None, opportunity=None, consent_granted=False, open_tasks=0, action="review", risk="read", steps=0, cost=0, approved=False):
        """Converge a signal into a governed plan proposal; never bypass approval."""
        signal = self.signals.ingest(event)
        selection = self.select_agent(candidates)
        if selection["status"] != "selected":
            return {"status": "blocked", "stage": "agent_selection", "signal": signal, "selection": selection}
        agent_id = selection["agent_id"]
        decision = self.decisions.decide(str(event.tenant_id), str(event.workspace_id), agent_id, signal, action=action, risk=risk, steps=steps, cost=cost, approved=approved)
        if decision["status"] == "blocked":
            return {"status": "blocked", "stage": "decision", "signal": signal, "selection": selection, "decision": decision}
        client_id = str((event.payload or {}).get("client_id") or event.entity_id)
        plan = self.planner.plan(str(event.tenant_id), str(event.workspace_id), client_id, lead, opportunity, consent_granted, open_tasks, trigger="omega8.3:" + str(event.event_type), agent_id=agent_id)
        evaluation = self.evaluate(plan, decision)
        if evaluation["status"] != "ready":
            return {"status": "blocked", "stage": "evaluation", "signal": signal, "selection": selection, "decision": decision, "plan": plan, "evaluation": evaluation}
        if self.governance:
            first = plan["actions"][0]
            gate = self.governance.check(str(event.tenant_id), str(event.workspace_id), agent_id, first.get("action", "review"), risk=first.get("risk", risk), steps=1, cost=first.get("cost", 0), tool=first.get("tool"), approved=approved)
            if not gate["allowed"]:
                return {"status": "approval_required" if gate["approval_required"] else "blocked", "stage": "governance", "signal": signal, "selection": selection, "decision": decision, "plan": plan, "evaluation": evaluation, "governance": gate}
        return {"status": "approved" if approved else "approval_required", "stage": "approval", "signal": signal, "selection": selection, "decision": decision, "plan": plan, "evaluation": evaluation}
