from agent_os.nodes import action_executor
from agent_os.policy import high_impact_reason
from agent_os.state import (
    Action,
    ActionStatus,
    AgentState,
    Domain,
    GraphNode,
    RiskLevel,
    Status,
)

EXAMPLE = (
    "Precisamos lançar o novo plano Pro em 30 de novembro, com landing page, e-mail de lançamento e suporte treinado."
)


def test_flow_without_date_runs_to_done(graph, jira):
    state = graph.run(AgentState.new("Implementar o endpoint de busca da API e escrever testes automatizados"))
    assert state.status == Status.DONE
    assert state.graph_node == GraphNode.DONE
    epics = [i for i in jira.issues.values() if i["type"] == "Epic"]
    stories = [i for i in jira.issues.values() if i["type"] == "Story"]
    subtasks = [i for i in jira.issues.values() if i["type"] == "Sub-task"]
    assert len(epics) == 1 and len(stories) == 4 and len(subtasks) == 8
    assert all("agent-os" in i["labels"] for i in jira.issues.values())
    assert len(jira.links) == 3  # dependências encadeadas entre as 4 Stories
    assert state.risk.level == RiskLevel.LOW
    assert state.hitl.pending == []


def test_committed_date_pauses_for_human_approval(graph, jira):
    state = graph.run(AgentState.new(EXAMPLE))
    assert state.status == Status.AWAITING_APPROVAL
    assert [p.action_id for p in state.hitl.pending] == ["commit-date"]
    assert "Previsão atual" in state.hitl.pending[0].reason
    assert all("duedate" not in issue for issue in jira.issues.values())  # nada comprometido ainda
    assert len(jira.issues) == 1 + 3 + 6  # Epic + 3 entregáveis + 2 sub-tasks cada


def test_approval_commits_date_and_finishes(graph, jira):
    state = graph.run(AgentState.new(EXAMPLE))
    state = graph.resume(state, {"commit-date": True}, by="gerente")
    assert state.status == Status.DONE
    epic_key = state.issue_keys["E1"]
    assert jira.issues[epic_key]["duedate"] == "2026-11-30"
    assert state.action("commit-date").status == ActionStatus.EXECUTED
    assert state.hitl.decisions[0].by == "gerente"


def test_rejection_drops_commitment_and_replans(graph, jira):
    state = graph.run(AgentState.new(EXAMPLE))
    state = graph.resume(state, {"commit-date": False})
    assert state.status == Status.DONE
    assert state.request.committed_date is None
    assert state.action("commit-date").status == ActionStatus.REJECTED
    assert all("duedate" not in issue for issue in jira.issues.values())
    assert any("não aprovada" in note for note in state.notes)


def test_late_forecast_raises_risk(graph):
    state = graph.run(AgentState.new("Implementar o endpoint da API de pagamentos até 2026-11-02"))
    state = graph.resume(state, {"commit-date": True})
    assert state.risk.level.rank >= RiskLevel.MEDIUM.rank
    assert state.risk.forecast.predicted_date > state.risk.forecast.committed_date


def test_executor_is_idempotent(graph, ctx, jira):
    state = graph.run(AgentState.new("Implementar o endpoint de busca da API"))
    before = len(jira.issues)
    action_executor.run(state, ctx)
    assert len(jira.issues) == before


def test_delete_is_forbidden(ctx, jira):
    state = AgentState.new("x", domain=Domain.ENGINEERING)
    state.actions = [Action(id="del", tool="jira.issues", operation="delete", target="AGT-1")]
    state = action_executor.run(state, ctx)
    assert state.actions[0].status == ActionStatus.FAILED
    assert "proibida" in state.actions[0].error


def test_batch_edit_over_limit_requires_approval(ctx):
    state = AgentState.new("x", domain=Domain.ENGINEERING)
    state.actions = [Action(id=f"u{i}", tool="jira.issues", operation="update", target=f"AGT-{i}") for i in range(11)]
    reason = high_impact_reason(state.actions[0], state, ctx.settings)
    assert reason is not None and "lote" in reason[0]
    assert high_impact_reason(Action(id="c", tool="jira.issues", operation="create"), state, ctx.settings) is None


def test_pending_approval_expires_into_reminder_not_approval(graph, ctx):
    from datetime import datetime, timedelta

    state = graph.run(AgentState.new(EXAMPLE))
    later = state.hitl.pending[0].expires_at + timedelta(hours=1)
    ctx.clock = lambda: later  # type: ignore[assignment]
    state = graph.resume(state, {})  # nenhuma decisão
    assert state.status == Status.AWAITING_APPROVAL
    assert state.hitl.pending[0].reminders == 1
    assert isinstance(state.hitl.pending[0].expires_at, datetime)


def test_report_intent_skips_creation(graph, jira):
    state = graph.run(AgentState.new("Gerar relatório de burn-down da sprint de engenharia", domain=Domain.ENGINEERING))
    assert state.status == Status.DONE
    assert jira.issues == {}
