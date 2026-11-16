from agent_os.nodes.router import classify, detect_intent
from agent_os.state import AgentState, Domain, GraphNode, Intent, Status

EXAMPLE = (
    "Precisamos lançar o novo plano Pro em 30 de novembro, com landing page, e-mail de lançamento e suporte treinado."
)


def test_classifies_marketing_with_enough_confidence():
    domain, confidence = classify(EXAMPLE)
    assert domain == Domain.MARKETING_DESIGN
    assert confidence >= 0.85


def test_classifies_engineering_and_operations():
    assert classify("Refatorar o endpoint da API e corrigir o bug do deploy")[0] == Domain.ENGINEERING
    assert classify("Abrir chamado para liberar acesso à VPN e senha do novo colaborador")[0] == Domain.OPERATIONS_IT


def test_detects_intents():
    assert detect_intent("Planejar a sprint de novembro") == Intent.PLAN_SPRINT
    assert detect_intent("Gerar relatório de riscos") == Intent.REPORT
    assert detect_intent("Criar landing page") == Intent.CREATE_WORK


def test_low_confidence_asks_instead_of_acting(graph, jira):
    state = graph.run(AgentState.new("faça aquilo que combinamos"))
    assert state.status == Status.NEEDS_CLARIFICATION
    assert state.graph_node == GraphNode.CLARIFY
    assert state.actions == []
    assert jira.issues == {}
    assert state.clarification_question


def test_explicit_domain_skips_ambiguity(graph):
    state = graph.run(AgentState.new("faça aquilo que combinamos", domain=Domain.ENGINEERING))
    assert state.status == Status.DONE
    assert state.routing.confidence == 1.0
