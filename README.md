# CyberFusion Solutions AI Agent

Local-first AI agent foundation for CyberFusion Solutions, built with CrewAI and AgentStack.

## Current runtime

- CrewAI 0.118.0
- AgentStack 0.3.7
- Default provider: local Ollama
- Default model: qwen3:4b
- Ollama API: http://localhost:11434
- OpenAI remains optional

## Readiness check

Run from the project directory:

    .\\.venv\\Scripts\\python.exe src\\main.py --readiness

This validates project files, YAML, Python source, and provider configuration without an LLM call.

## Run

    .\\.venv\\Scripts\\python.exe src\\main.py

Local inference uses Ollama on the same computer, so OpenAI credits are not required.

## Safety

- Never expose secrets.
- Do not invent facts when information is missing.
- Separate verified facts from assumptions.
- Require human review for credentials, irreversible actions, and sensitive decisions.

## Architecture direction

User Request -> Intent -> Client/Business Type -> Service Identification -> Knowledge Retrieval -> Response -> Consent Check -> Handoff -> Reference ID -> Audit Record
