from __future__ import annotations

import os

from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task


def build_llm() -> LLM:
    """Build the configured LLM, defaulting to the local Ollama model."""
    provider = os.getenv("LLM_PROVIDER", "local").strip().lower()
    model = os.getenv("LLM_MODEL", "qwen3:4b").strip()
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()

    if provider == "local":
        return LLM(
            model=f"ollama/{model}",
            base_url=base_url,
            temperature=0.2,
        )

    if provider == "openai":
        return LLM(
            model=model or "gpt-4o-mini",
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0.2,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER={provider!r}. Use 'local' or 'openai'.")


@CrewBase
class AiagentCrew:
    """Crew for the CyberFusion Solutions AI agent foundation."""

    @agent
    def cyberfusion_solutions_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["cyberfusion_solutions_agent"],
            verbose=True,
            allow_delegation=False,
            llm=build_llm(),
        )

    @task
    def cyberfusion_solutions_task(self) -> Task:
        return Task(
            config=self.tasks_config["cyberfusion_solutions_task"],
            agent=self.cyberfusion_solutions_agent(),
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
