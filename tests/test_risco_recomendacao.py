"""Testes do contrato específico de classificação de riscos."""

import pandas as pd
import pytest

from src.recommendation.motor_recomendacao import gerar_recomendacoes


def _previsoes() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "medicamento_id": ["vencimento", "normal"],
            "data_previsao": ["2026-01-01"] * 2,
            "demanda_prevista": [10.0, 10.0],
        }
    )


@pytest.mark.parametrize(
    "demanda,estoque,prazo,esperado",
    [
        (10.0, 40.0, 4.0, "alto"),
        (10.0, 40.1, 4.0, "médio"),
        (10.0, 60.0, 4.0, "médio"),
        (10.0, 60.1, 4.0, "baixo"),
        (0.0, 0.0, 4.0, "baixo"),
    ],
)
def test_classifica_risco_de_falta_nas_fronteiras(
    demanda: float, estoque: float, prazo: float, esperado: str
) -> None:
    resultado = gerar_recomendacoes(
        pd.DataFrame(
            {
                "medicamento_id": ["med_a"],
                "data_previsao": ["2026-01-01"],
                "demanda_prevista": [demanda],
            }
        ),
        estoque_atual=pd.DataFrame(
            {
                "medicamento_id": ["med_a"],
                "data": ["2025-12-31"],
                "estoque_disponivel": [estoque],
            }
        ),
        estoque_seguranca=pd.DataFrame(
            {"medicamento_id": ["med_a"], "estoque_seguranca": [0.0]}
        ),
        medicamentos_referencia=pd.DataFrame(
            {"medicamento_id": ["med_a"], "prazo_entrega_dias": [prazo]}
        ),
    )

    assert resultado.loc[0, "risco_falta"] == esperado


@pytest.mark.parametrize(
    "estoque,esperado",
    [(3.0, "alto"), (20.0, "baixo")],
)
def test_classifica_risco_de_falta_sem_prazo_com_fallback_binario(
    estoque: float, esperado: str
) -> None:
    resultado = gerar_recomendacoes(
        pd.DataFrame(
            {
                "medicamento_id": ["med_a"],
                "data_previsao": ["2026-01-01"],
                "demanda_prevista": [10.0],
            }
        ),
        estoque_atual=pd.DataFrame(
            {
                "medicamento_id": ["med_a"],
                "data": ["2025-12-31"],
                "estoque_disponivel": [estoque],
            }
        ),
        estoque_seguranca=pd.DataFrame(
            {"medicamento_id": ["med_a"], "estoque_seguranca": [2.0]}
        ),
    )

    assert resultado.loc[0, "risco_falta"] == esperado


def test_classifica_risco_de_vencimento_e_gera_justificativa() -> None:
    resultado = gerar_recomendacoes(
        _previsoes(),
        estoque_atual=pd.DataFrame(
            {
                "medicamento_id": ["vencimento", "normal"],
                "data": ["2025-12-31"] * 2,
                "estoque_disponivel": [100.0, 110.0],
            }
        ),
        estoque_seguranca=pd.DataFrame(
            {
                "medicamento_id": ["vencimento", "normal"],
                "estoque_seguranca": [0.0] * 2,
            }
        ),
        medicamentos_referencia=pd.DataFrame(
            {
                "medicamento_id": ["vencimento", "normal"],
                "prazo_entrega_dias": [7, 7],
            }
        ),
        lotes=pd.DataFrame(
            {
                "medicamento_id": ["vencimento", "normal"],
                "quantidade_atual": [100.0, 10.0],
                "data_validade": ["2026-01-03", "2027-01-01"],
            }
        ),
    ).set_index("medicamento_id")

    assert resultado.loc["vencimento", "risco_vencimento"] == "alto"
    assert resultado.loc["normal", "risco_vencimento"] == "baixo"
    assert "100 unidades vencem" in resultado.loc["vencimento", "justificativa"]
