"""Shared fixtures for testkit tests."""

import pytest

from testkit import FakeCosmosContainer, FakeLLMClient, FakeStorage, FakeMCPClient


@pytest.fixture
def cosmos():
    return FakeCosmosContainer(partition_key="/session_id")


@pytest.fixture
def llm():
    return FakeLLMClient()


@pytest.fixture
def storage():
    return FakeStorage()


@pytest.fixture
def mcp():
    return FakeMCPClient()
