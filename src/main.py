#!/usr/bin/env python
"""CLI entry point for the CyberFusion Solutions AI agent."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _configure_console() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def _provider() -> str:
    return os.getenv("LLM_PROVIDER", "local").strip().lower()


def _readiness_check() -> int:
    import yaml

    required_files = (
        "agentstack.json", "pyproject.toml", "README.md", "src/main.py",
        "src/crew.py", "src/config/agents.yaml", "src/config/tasks.yaml",
        "src/config/inputs.yaml", "src/config/business_rules.yaml",
        "src/knowledge/services.yaml", "src/knowledge/service_knowledge.yaml",
        "src/knowledge/skills.yaml",
        "src/core/intake.py", "src/core/references.py", "src/core/audit.py",
        "src/core/service_router.py", "src/core/knowledge.py", "src/core/conversation.py",
        "src/core/agent_permissions.py", "src/core/supervisor.py", "src/core/business_gateway.py", "src/core/langgraph_runtime.py", "src/core/mcp_gateway.py", "src/integrations/execution.py", "src/integrations/audited_router.py", "src/config/mcp_gateway.yaml",
    )
    missing = [name for name in required_files if not (PROJECT_ROOT / name).is_file()]
    if missing:
        print("READINESS: FAIL")
        for name in missing:
            print(f"  - {name}")
        return 1

    try:
        for path in (
            PROJECT_ROOT / "src" / "config" / "agents.yaml",
            PROJECT_ROOT / "src" / "config" / "tasks.yaml",
            PROJECT_ROOT / "src" / "config" / "inputs.yaml",
            PROJECT_ROOT / "src" / "config" / "business_rules.yaml",
            PROJECT_ROOT / "src" / "knowledge" / "services.yaml",
            PROJECT_ROOT / "src" / "knowledge" / "service_knowledge.yaml",
            PROJECT_ROOT / "src" / "knowledge" / "skills.yaml",
            PROJECT_ROOT / "src" / "config" / "mcp_gateway.yaml",
        ):
            with path.open("r", encoding="utf-8") as handle:
                yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        print("READINESS: FAIL")
        print(f"Configuration error: {exc}")
        return 1

    provider = _provider()
    if provider not in {"local", "openai"}:
        print("READINESS: FAIL")
        print(f"Unsupported LLM_PROVIDER={provider!r}; use local or openai.")
        return 1

    print("READINESS: PASS")
    print("Project files: OK")
    print("YAML configuration: OK")
    print("Python source: OK")
    print(f"LLM provider: {provider}")
    if provider == "local":
        print(f"Local model: {os.getenv('LLM_MODEL', 'qwen3:4b')}")
        print(f"Ollama URL: {os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    else:
        print("OpenAI credentials: " + ("CONFIGURED (value hidden)" if os.getenv("OPENAI_API_KEY") else "NOT CONFIGURED"))
    return 0


def _require_llm_credentials() -> None:
    if _provider() == "openai" and not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not configured. Switch to LLM_PROVIDER=local or add the key locally.")


def _context_for(request: str) -> str:
    from core.agent_context import build_agent_context
    _, context = build_agent_context(request)
    return context


def run() -> None:
    _configure_console()
    if "--readiness" in sys.argv:
        raise SystemExit(_readiness_check())

    _require_llm_credentials()
    import agentstack
    from crew import AiagentCrew

    request = agentstack.get_inputs().get("request", "")
    AiagentCrew().crew().kickoff(inputs={"request": request, "agent_context": _context_for(request)})


def train() -> None:
    _configure_console()
    _require_llm_credentials()
    import agentstack
    from crew import AiagentCrew

    try:
        iterations = int(sys.argv[1])
        filename = sys.argv[2]
    except (IndexError, ValueError) as exc:
        raise SystemExit("Usage: train <iterations> <filename>") from exc

    inputs = agentstack.get_inputs()
    request = inputs.get("request", "")
    AiagentCrew().crew().train(
        n_iterations=iterations,
        filename=filename,
        inputs={**inputs, "agent_context": _context_for(request)},
    )


def replay() -> None:
    _configure_console()
    try:
        task_id = sys.argv[1]
    except IndexError as exc:
        raise SystemExit("Usage: replay <task_id>") from exc
    from crew import AiagentCrew
    AiagentCrew().crew().replay(task_id=task_id)


def test() -> None:
    _configure_console()
    _require_llm_credentials()
    import agentstack
    from crew import AiagentCrew

    try:
        iterations = int(sys.argv[1])
        model_name = sys.argv[2]
    except (IndexError, ValueError) as exc:
        raise SystemExit("Usage: test <iterations> <model_name>") from exc

    inputs = agentstack.get_inputs()
    request = inputs.get("request", "")
    AiagentCrew().crew().test(
        n_iterations=iterations,
        openai_model_name=model_name,
        inputs={**inputs, "agent_context": _context_for(request)},
    )


if __name__ == "__main__":
    run()
