from datetime import datetime

import pytest

from agent_os import AgentGraph, Settings, build_context
from agent_os.tools.base import BoardSnapshot
from agent_os.tools.mock_jira import MockJiraClient

NOW = datetime(2026, 10, 31, 12, 0)


@pytest.fixture
def jira() -> MockJiraClient:
    return MockJiraClient(board=BoardSnapshot())  # quadro vazio: sem gargalos


@pytest.fixture
def ctx(jira):
    return build_context(Settings(), jira=jira, clock=lambda: NOW)


@pytest.fixture
def graph(ctx) -> AgentGraph:
    return AgentGraph(ctx)
