from pathlib import Path

from agentkit import load_agent_spec


def test_load_agent_spec(tmp_path: Path) -> None:
    spec_file = tmp_path / "agent.yaml"
    spec_file.write_text(
        """
name: chat-agent
model: gpt-4.1-mini
instructions: Be helpful.
tools:
  - ping
""".strip(),
        encoding="utf-8",
    )

    spec = load_agent_spec(spec_file)
    assert spec.name == "chat-agent"
    assert spec.tools == ["ping"]
