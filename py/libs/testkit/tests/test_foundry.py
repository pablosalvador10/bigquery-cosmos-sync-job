"""Tests for FakeFoundryClient and FakeAgentManager."""

from testkit import FakeFoundryClient, FakeAgentManager


class TestFakeFoundryClient:
    def test_create_agent(self):
        client = FakeFoundryClient()
        agent = client.agents_client.create_agent(name="test", model="gpt-4")
        assert agent.name == "test"
        assert agent.model == "gpt-4"
        assert len(client.agents_client.created) == 1

    def test_delete_agent(self):
        client = FakeFoundryClient()
        agent = client.agents_client.create_agent(name="test")
        client.agents_client.delete_agent(agent.id)
        assert agent.id in client.agents_client.deleted


class TestFakeAgentManager:
    def test_temporary_agent_lifecycle(self):
        manager = FakeAgentManager()
        with manager.temporary_agent(name="ephemeral", model="gpt-4") as agent:
            assert agent.name == "ephemeral"
        assert len(manager.created_agents) == 1
        assert len(manager.deleted_agents) == 1

    def test_run_agent(self):
        manager = FakeAgentManager()
        manager.set_run_response("custom response")
        result = manager.run_agent("agent-1", "thread-1")
        assert result.content == "custom response"

    def test_run_agent_stream(self):
        manager = FakeAgentManager()
        results = list(manager.run_agent_stream("agent-1", "thread-1"))
        assert len(results) == 1
        assert results[0].content == "fake agent response"
