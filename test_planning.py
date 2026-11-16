from datetime import date

from agent_os.nodes.plan_assign import extract_deliverables, parse_date, summarize

TODAY = date(2026, 10, 31)


def test_parse_date_pt_br_and_iso():
    assert parse_date("lançar em 30 de novembro", TODAY) == date(2026, 11, 30)
    assert parse_date("entrega em 5 de janeiro", TODAY) == date(2027, 1, 5)  # próxima ocorrência
    assert parse_date("entrega em 5 de janeiro de 2028", TODAY) == date(2028, 1, 5)
    assert parse_date("prazo 2026-12-15", TODAY) == date(2026, 12, 15)
    assert parse_date("sem data nenhuma", TODAY) is None


def test_extract_deliverables():
    text = "Lançar o plano Pro, com landing page, e-mail de lançamento e suporte treinado."
    assert extract_deliverables(text) == ["Landing page", "E-mail de lançamento", "Suporte treinado"]
    assert extract_deliverables("Corrigir bug no login") == []


def test_summarize_cuts_at_first_clause():
    assert summarize("Lançar o plano Pro, com landing page.") == "Lançar o plano Pro"


def test_summarize_drops_filler_and_date():
    text = "Precisamos lançar o novo plano Pro em 30 de novembro, com landing page."
    assert summarize(text) == "Lançar o novo plano Pro"
    assert summarize("Refatorar o checkout até 2026-12-15") == "Refatorar o checkout"
