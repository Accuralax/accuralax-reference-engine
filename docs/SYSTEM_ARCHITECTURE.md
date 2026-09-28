# CyberFusion Solutions AI Agent — System Architecture

## Vision
A local-first, self-checking and controlled self-healing agentic system. Reliability comes from deterministic application rules around the LLM, bounded agent loops, auditable knowledge, explicit permissions, validation, and rollback.

## Runtime layers
User channels → Transport Gateway → Session / Identity / Consent → LangGraph Orchestrator → Agentic Runtime (Supervisor, specialist agents, bounded sub-agents, Skills, MCP/tool gateway) → Knowledge / RAG → Safety & Policy → Audit / Reference / Observability → Self-Check & Repair → Validation Sandbox → Tests → Apply / Rollback / Human Review.

## Agent hierarchy
- Supervisor / Orchestrator
- Specialist agents: Intake, Service Triage, Knowledge/RAG, Business Operations, Digital, AI & Automation, Cybersecurity Triage, Compliance, Funding, Support, QA/Verifier, Repair/DevOps.
- Sub-agents are bounded by task, tool permissions, budget, timeout, and escalation rules.

## Skills
Skills are reusable bounded capabilities. Every skill declares purpose, triggers, permitted tools, inputs, outputs, safety constraints, verification, and escalation behavior. Skills never override application policy.

## LangChain + LangGraph
LangChain is the component/integration layer for models, tools, retrievers, embeddings, and RAG. LangGraph is the stateful orchestration backbone for checkpoints, retries, bounded loops, sub-agents, approvals, and repair workflows.

## Core graph
START → safety_guard → intake → service_router → knowledge_retrieval → specialist_agent → verifier → response → consent_gate → handoff → audit → END.

Failure/repair branch: any node → health_check → diagnose → repair_plan → sandbox_patch → regression_tests → pass/apply/continue OR fail/rollback/human_review.

Every loop has max iterations, timeout, token/tool budget, cycle detection, terminal failure state, and audit trace.

## RAG
ingest → normalize → chunk → metadata → embed → index → retrieve → rerank → context limit → answer → provenance/citations → evaluation.

Knowledge records should carry source, owner, version, effective date, review date, classification, service/domain, and verification status. Evaluation covers retrieval relevance, groundedness, stale/missing-source behavior, provenance coverage, prompt-injection resistance, and duplicate/conflict detection.

## MCP
Planned capability-scoped MCP domains include GitHub, Claude Code, Obsidian, Remote Desktop Commander, Supabase, Vercel, and approved business systems. Read-only is the default. Write, deploy, delete, credential, and external-side-effect actions require stronger policy gates and appropriate approval.

Obsidian is a human-readable knowledge/architecture workspace, not automatically authoritative customer-facing truth. Structured application knowledge/database remains the operational source of truth; audit records are immutable.

Claude Code operates under the same repository safety, testing, secret, approval, and rollback controls.

Hermes remains a pluggable integration until the exact Hermes product/framework/model is identified; do not add an unverified dependency merely for naming alignment.

## Self-check / self-healing
OBSERVE → DETECT → CLASSIFY → DIAGNOSE → PLAN → SANDBOX → TEST → APPROVE/POLICY GATE → APPLY → VERIFY → AUDIT → CONTINUE or ROLLBACK.

The repair system must not silently modify production, credentials, safety policy, approval policy, audit mechanisms, or its own repair authority. Changes to those control planes require human approval.

## UI Verse
Use shadcn/ui + Tailwind for accessible application UI, Anime.js for interaction/motion, and WebGL/Three.js as progressive enhancement. The multi-window 3D scene represents the real runtime rather than being decorative: center Supervisor/Orchestrator; orbit specialist agents; second orbit sub-agents; outer ring Skills/Tools/MCP; background knowledge/RAG nodes and telemetry. Support idle, thinking, retrieving, tool-call, verifying, waiting-consent, handoff, complete, and error states. The interface must remain usable without WebGL.

## Completion rule
A feature is complete only when implementation, deterministic tests, failure behavior, security boundaries, observability/audit, self-check coverage, and rollback/approval behavior are defined and verified.
