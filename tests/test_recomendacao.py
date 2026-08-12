"""Testes de contrato do componente de recomendação disponível no MVP."""

import pandas as pd

from src.recommendation.estoque_seguranca import (
    COLUNAS_SAIDA,
    calcular_estoque_seguranca,
)


def test_saida_estoque_seguranca_respeita_contrato() -> None:
    consumo = pd.DataFrame(
        {
            "medicamento_id": ["med_a", "med_a", "med_b", "med_b"],
            "consumo_unidades": [10.0, 20.0, 4.0, 4.0],
        }
    )
    referencias = pd.DataFrame(
        {
            "medicamento_id": ["med_a", "med_b"],
            "prazo_entrega_dias": [7, 3],
        }
    )

    resultado = calcular_estoque_seguranca(consumo, referencias)

    assert list(resultado.columns) == COLUNAS_SAIDA
    assert resultado["medicamento_id"].tolist() == ["med_a", "med_b"]
    assert not resultado.isna().any().any()
    colunas_numericas = ["desvio_padrao_consumo", "prazo_entrega_dias", "estoque_seguranca"]
    assert (resultado[colunas_numericas] >= 0).all().all()


def test_historico_minimo_e_consumo_zero_geram_buffer_zero() -> None:
    consumo = pd.DataFrame(
        {
            "medicamento_id": ["sem_historico", "demanda_zero", "demanda_zero"],
            "consumo_unidades": [8.0, 0.0, 0.0],
        }
    )
    referencias = pd.DataFrame(
        {
            "medicamento_id": ["sem_historico", "demanda_zero"],
            "prazo_entrega_dias": [7, 7],
        }
    )

    resultado = calcular_estoque_seguranca(consumo, referencias).set_index("medicamento_id")

    assert resultado.loc["sem_historico", "desvio_padrao_consumo"] == 0.0
    assert resultado.loc["sem_historico", "estoque_seguranca"] == 0
    assert resultado.loc["demanda_zero", "estoque_seguranca"] == 0
