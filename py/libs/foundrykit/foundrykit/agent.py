"""Agent lifecycle management: create, run, stream, and cleanup."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from .client import FoundryClient, get_foundry_client


@dataclass
class AgentStreamEvent:
    """Typed event emitted during an agent streaming run."""
    event_type: str
    data: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentManager:
    """Creates, runs, and cleans up Foundry prompt agents."""

    def __init__(self, client: FoundryClient | None = None) -> None:
        self.client = client or get_foundry_client()

    @contextmanager
    def temporary_agent(self, **create_kwargs: Any) -> Iterator[Any]:
        agent = self.client.agents_client.create_agent(**create_kwargs)
        try:
            yield agent
        finally:
            self.client.agents_client.delete_agent(agent.id)

    def run_agent(self, agent_id: str, thread_id: str) -> Any:
        return self.client.agents_client.runs.create_and_process(
            thread_id=thread_id,
            agent_id=agent_id,
        )

    def run_agent_stream(self, agent_id: str, thread_id: str):
        with self.client.agents_client.runs.stream(thread_id=thread_id, agent_id=agent_id) as stream:
            for event in stream:
                yield AgentStreamEvent(event_type="raw", data=str(event))
