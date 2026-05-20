"""Singleton Azure AI Foundry client with lazy credential initialization."""

from functools import lru_cache

from azure.ai.agents import AgentsClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

from .config import FoundrySettings


class FoundryClient:
    """Wrapper around AgentsClient with mode-based credential selection."""
    def __init__(self, settings: FoundrySettings | None = None) -> None:
        self.settings = settings or FoundrySettings()
        self._agents_client: AgentsClient | None = None

    def _build_credential(self) -> DefaultAzureCredential | ManagedIdentityCredential:
        """Return credential based on configured mode."""
        if self.settings.foundry_credential_mode == "managed_identity":
            return ManagedIdentityCredential(client_id=self.settings.azure_client_id)
        return DefaultAzureCredential()

    @property
    def agents_client(self) -> AgentsClient:
        if self._agents_client is None:
            self._agents_client = AgentsClient(
                endpoint=self.settings.foundry_project_endpoint,
                credential=self._build_credential(),
            )
        return self._agents_client


@lru_cache(maxsize=1)
def get_foundry_client() -> FoundryClient:
    return FoundryClient()
