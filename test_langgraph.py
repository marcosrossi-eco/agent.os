import pytest

pytest.importorskip("langgraph")

from agent_os import AgentGraph  # noqa: E402
from agent_os.langgraph_graph import LangGraphAgent  # noqa: E402
from agent_os.state import ActionStatus, AgentState, GraphNode, Status  # noqa: E402

EXAMPLE = (
    "Precisamos lançar o novo plano Pro em 30 de novembro, com landing page, e-mail de lançamento e suporte treinado."
)


def test_langgraph_pauses_and_resumes_like_native(ctx, jira):
    agent = LangGraphAgent(ctx)
    state = agent.run(AgentState.new(EXAMPLE))
    assert state.status == Status.AWAITING_APPROVAL
    assert [p.action_id for p in state.hitl.pending] == ["commit-date"]

    state = agent.resume(state, {"commit-date": True}, by="gerente")
    assert state.status == Status.DONE
    assert state.action("commit-date").status == ActionStatus.EXECUTED
    assert jira.issues[state.issue_keys["E1"]]["duedate"] == "2026-11-30"


def test_langgraph_rejection_replans(ctx):
    agent = LangGraphAgent(ctx)
    state = agent.run(AgentState.new(EXAMPLE))
    state = agent.resume(state, {"commit-date": False})
    assert state.status == Status.DONE
    assert state.request.committed_date is None


def test_langgraph_clarifies_on_low_confidence(ctx, jira):
    state = LangGraphAgent(ctx).run(AgentState.new("faça aquilo que combinamos"))
    assert state.graph_node == GraphNode.CLARIFY
    assert jira.issues == {}


def test_both_engines_produce_same_issues(ctx, jira):
    from agent_os import Settings, build_context
    from agent_os.tools.base import BoardSnapshot
    from agent_os.tools.mock_jira import MockJiraClient

    other = MockJiraClient(board=BoardSnapshot())
    other_ctx = build_context(Settings(), jira=other, clock=ctx.clock)
    AgentGraph(ctx).run(AgentState.new("Implementar o endpoint de busca da API"))
    LangGraphAgent(other_ctx).run(AgentState.new("Implementar o endpoint de busca da API"))
    assert jira.issues == other.issues
