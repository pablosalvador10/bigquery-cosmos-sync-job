"""YAML-driven agent specification loader."""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class AgentSpec(BaseModel):
    """Defines an agent's name, model, instructions, and tools."""
    name: str
    model: str
    instructions: str
    tools: list[str] = Field(default_factory=list)


def load_agent_spec(file_path: str | Path) -> AgentSpec:
    """Load and validate an agent spec from a YAML file."""
    path = Path(file_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return AgentSpec.model_validate(data)
