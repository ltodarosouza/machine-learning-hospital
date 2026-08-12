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


@pytest.mark.parametrize(
    "quantidade,dias_ate_validade,esperado",
    [
        # dias_ate_validade <= prazo_entrega_dias (7): já funcionava antes da correção.
        (100.0, 3, "alto"),  # 100 / (10/dia * 3d = 30) = 3,3x -> alto
        # dias_ate_validade > prazo_entrega_dias (7): a regra antiga IGNORAVA
        # esses lotes inteiramente (só olhava até o prazo de entrega), então
        # risco_vencimento ficava "baixo" nesses 3 casos independente da
        # quantidade — o bug reportado na Issue #53. Com a correção, cada
        # lote é avaliado pelo que realmente importa: dá tempo de consumir
        # a quantidade antes dele vencer?
        (150.0, 10, "alto"),  # 150 / (10*10=100) = 1,5x -> alto
        (80.0, 10, "médio"),  # 80 / 100 = 0,8x -> médio (aperta, mas não estoura)
        (50.0, 10, "baixo"),  # 50 / 100 = 0,5x -> baixo
        (250.0, 20, "alto"),  # 250 / (10*20=200) = 1,25x -> alto
        (150.0, 20, "médio"),  # 150 / 200 = 0,75x -> médio
        (100.0, 20, "baixo"),  # 100 / 200 = 0,5x -> baixo
    ],
)
def test_classifica_risco_de_vencimento_por_lote_sem_depender_do_prazo_de_entrega(
    quantidade: float, dias_ate_validade: int, esperado: str
) -> None:
    data_referencia = pd.Timestamp("2025-12-31")
    data_validade = (data_referencia + pd.Timedelta(days=dias_ate_validade)).date().isoformat()

    resultado = gerar_recomendacoes(
        pd.DataFrame(
            {
                "medicamento_id": ["med_a"],
                "data_previsao": ["2026-01-01"],
                "demanda_prevista": [10.0],  # horizonte de 1 dia -> demanda_diaria = 10
            }
        ),
        estoque_atual=pd.DataFrame(
            {"medicamento_id": ["med_a"], "data": ["2025-12-31"], "estoque_disponivel": [500.0]}
        ),
        estoque_seguranca=pd.DataFrame({"medicamento_id": ["med_a"], "estoque_seguranca": [0.0]}),
        medicamentos_referencia=pd.DataFrame(
            # prazo_entrega_dias (7) deliberadamente menor que dias_ate_validade
            # nos casos de 10 e 20 dias: prova que o resultado não depende dele.
            {"medicamento_id": ["med_a"], "prazo_entrega_dias": [7]}
        ),
        lotes=pd.DataFrame(
            {"medicamento_id": ["med_a"], "quantidade_atual": [quantidade], "data_validade": [data_validade]}
        ),
    ).set_index("medicamento_id")

    assert resultado.loc["med_a", "risco_vencimento"] == esperado


def test_pega_o_pior_lote_quando_medicamento_tem_mais_de_um() -> None:
    resultado = gerar_recomendacoes(
        pd.DataFrame({"medicamento_id": ["med_a"], "data_previsao": ["2026-01-01"], "demanda_prevista": [10.0]}),
        estoque_atual=pd.DataFrame(
            {"medicamento_id": ["med_a"], "data": ["2025-12-31"], "estoque_disponivel": [500.0]}
        ),
        estoque_seguranca=pd.DataFrame({"medicamento_id": ["med_a"], "estoque_seguranca": [0.0]}),
        medicamentos_referencia=pd.DataFrame({"medicamento_id": ["med_a"], "prazo_entrega_dias": [7]}),
        lotes=pd.DataFrame(
            {
                "medicamento_id": ["med_a", "med_a"],
                # um lote tranquilo (baixo) e outro em risco alto — o pior deve prevalecer
                "quantidade_atual": [20.0, 150.0],
                "data_validade": ["2027-01-01", "2026-01-10"],  # o segundo vence em 10 dias
            }
        ),
    ).set_index("medicamento_id")

    assert resultado.loc["med_a", "risco_vencimento"] == "alto"
    assert "150 unidades vencem" in resultado.loc["med_a", "justificativa"]
