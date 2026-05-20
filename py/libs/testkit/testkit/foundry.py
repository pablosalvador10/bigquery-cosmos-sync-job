"""Fake Foundry client and agent manager for testing agent workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4


@dataclass
class FakeAgent:
    """A fake agent created by the FakeFoundryClient."""

    id: str
    name: str
    model: str
    instructions: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FakeRunResult:
    """A fake agent run result."""

    status: str = "completed"
    content: str = "fake agent response"


class FakeAgentsClient:
    """In-memory agents client matching the Azure AI Agents SDK interface."""

    def __init__(self) -> None:
        self._agents: dict[str, FakeAgent] = {}
        self.created: list[FakeAgent] = []
        self.deleted: list[str] = []

    def create_agent(
        self,
        *,
        name: str = "test-agent",
        model: str = "gpt-4.1-mini",
        instructions: str = "",
        **kwargs: Any,
    ) -> FakeAgent:
        agent = FakeAgent(
            id=f"agent-{uuid4().hex[:8]}",
            name=name,
            model=model,
            instructions=instructions,
            metadata=kwargs,
        )
        self._agents[agent.id] = agent
        self.created.append(agent)
        return agent

    def delete_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)
        self.deleted.append(agent_id)


class FakeFoundryClient:
    """Fake FoundryClient matching foundrykit's FoundryClient interface.

    Usage::

        client = FakeFoundryClient()
        agent = client.agents_client.create_agent(name="test")
        assert len(client.agents_client.created) == 1
    """

    def __init__(self) -> None:
        self._agents_client = FakeAgentsClient()

    @property
    def agents_client(self) -> FakeAgentsClient:
        return self._agents_client


class FakeAgentManager:
    """Fake AgentManager matching foundrykit's AgentManager interface.

    Usage::

        manager = FakeAgentManager()
        with manager.temporary_agent(name="test") as agent:
            assert agent.name == "test"
        assert len(manager.created_agents) == 1
        assert len(manager.deleted_agents) == 1
    """

    def __init__(self, client: FakeFoundryClient | None = None) -> None:
        self.client = client or FakeFoundryClient()
        self.created_agents: list[FakeAgent] = []
        self.deleted_agents: list[str] = []
        self._run_response = "fake agent response"

    def set_run_response(self, content: str) -> "FakeAgentManager":
        """Set the response returned by ``run_agent``."""
        self._run_response = content
        return self

    @contextmanager
    def temporary_agent(self, **create_kwargs: Any) -> Iterator[FakeAgent]:
        agent = self.client.agents_client.create_agent(**create_kwargs)
        self.created_agents.append(agent)
        try:
            yield agent
        finally:
            self.client.agents_client.delete_agent(agent.id)
            self.deleted_agents.append(agent.id)

    def run_agent(self, agent_id: str, thread_id: str) -> FakeRunResult:
        return FakeRunResult(content=self._run_response)

    def run_agent_stream(self, agent_id: str, thread_id: str):
        yield FakeRunResult(content=self._run_response)
