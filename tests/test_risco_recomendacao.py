"""Cenários de risco explicável da Issue #16."""

import pandas as pd

from src.recommendation.motor_recomendacao import gerar_recomendacoes


def _previsoes() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "medicamento_id": ["falta", "vencimento", "normal"],
            "data_previsao": ["2026-01-01"] * 3,
            "demanda_prevista": [10.0, 10.0, 10.0],
        }
    )


def test_classifica_risco_de_falta_vencimento_e_situacao_normal() -> None:
    resultado = gerar_recomendacoes(
        _previsoes(),
        pd.DataFrame(
            {"medicamento_id": ["falta", "vencimento", "normal"], "data": ["2025-12-31"] * 3,
             "estoque_disponivel": [20.0, 100.0, 110.0]}
        ),
        pd.DataFrame(
            {"medicamento_id": ["falta", "vencimento", "normal"], "estoque_seguranca": [0.0] * 3}
        ),
        medicamentos_referencia=pd.DataFrame(
            {"medicamento_id": ["falta", "vencimento", "normal"], "prazo_entrega_dias": [3, 7, 7]}
        ),
        lotes=pd.DataFrame(
            {"medicamento_id": ["vencimento", "normal"], "quantidade_atual": [100.0, 10.0],
             "data_validade": ["2026-01-03", "2027-01-01"]}
        ),
    ).set_index("medicamento_id")

    assert resultado.loc["falta", "risco_falta"] == "alto"
    assert resultado.loc["vencimento", "risco_vencimento"] == "alto"
    assert resultado.loc["normal", "risco_falta"] == "baixo"
    assert resultado.loc["normal", "risco_vencimento"] == "baixo"
    assert "estoque cobre 2.0 dias" in resultado.loc["falta", "justificativa"]
    assert "100 unidades vencem" in resultado.loc["vencimento", "justificativa"]
