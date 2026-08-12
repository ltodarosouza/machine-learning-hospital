"""Testes de contrato e casos de borda do motor de recomendação."""

import pandas as pd
import pytest

from src.recommendation.motor_recomendacao import COLUNAS_SAIDA, gerar_recomendacoes


def _estoque_seguranca(*valores: tuple[str, float]) -> pd.DataFrame:
    return pd.DataFrame(valores, columns=["medicamento_id", "estoque_seguranca"])


def _estoque_atual(*valores: tuple[str, float]) -> pd.DataFrame:
    return pd.DataFrame(valores, columns=["medicamento_id", "estoque_disponivel"])


def test_saida_respeita_contrato_e_agrega_horizonte_e_pedidos() -> None:
    previsoes = pd.DataFrame(
        {
            "medicamento_id": ["med_a", "med_a"],
            "data_previsao": ["2025-01-01", "2025-01-02"],
            "demanda_prevista": [10.0, 15.0],
        }
    )
    pedidos = pd.DataFrame(
        {
            "medicamento_id": ["med_a", "med_a"],
            "quantidade": [2.0, 3.0],
        }
    )

    resultado = gerar_recomendacoes(
        previsoes,
        _estoque_atual(("med_a", 0.0)),
        _estoque_seguranca(("med_a", 5.0)),
        pedidos,
    )

    assert list(resultado.columns) == COLUNAS_SAIDA
    assert len(resultado) == 1
    assert resultado.loc[0, "medicamento_id"] == "med_a"
    assert resultado.loc[0, "compra_recomendada"] == 25.0
    assert resultado.loc[0, "risco_falta"] == "alto"
    assert resultado.loc[0, "risco_vencimento"] == "baixo"
    assert "Comprar 25 unidades" in resultado.loc[0, "justificativa"]


def test_estoque_zerado_recomenda_demanda_mais_seguranca() -> None:
    previsoes = pd.DataFrame({"medicamento_id": ["med_a"], "demanda_prevista": [20.0]})

    resultado = gerar_recomendacoes(
        previsoes,
        _estoque_atual(("med_a", 0.0)),
        _estoque_seguranca(("med_a", 4.0)),
    )

    assert resultado.loc[0, "compra_recomendada"] == 24.0
    assert resultado.loc[0, "risco_falta"] == "alto"


def test_demanda_zero_e_estoque_suficiente_nao_recomendam_compra() -> None:
    previsoes = pd.DataFrame(
        {
            "medicamento_id": ["demanda_zero", "estoque_suficiente"],
            "demanda_prevista": [0.0, 10.0],
        }
    )

    resultado = gerar_recomendacoes(
        previsoes,
        _estoque_atual(("demanda_zero", 0.0), ("estoque_suficiente", 20.0)),
        _estoque_seguranca(("demanda_zero", 0.0), ("estoque_suficiente", 5.0)),
    ).set_index("medicamento_id")

    assert resultado.loc["demanda_zero", "compra_recomendada"] == 0.0
    assert resultado.loc["demanda_zero", "risco_falta"] == "baixo"
    assert resultado.loc["estoque_suficiente", "compra_recomendada"] == 0.0
    assert resultado.loc["estoque_suficiente", "risco_falta"] == "baixo"


def test_rejeita_entrada_negativa_ou_sem_estoque() -> None:
    previsoes = pd.DataFrame({"medicamento_id": ["med_a"], "demanda_prevista": [-1.0]})

    with pytest.raises(ValueError, match="demanda_prevista"):
        gerar_recomendacoes(
            previsoes,
            _estoque_atual(("med_a", 0.0)),
            _estoque_seguranca(("med_a", 0.0)),
        )

    previsoes.loc[0, "demanda_prevista"] = 1.0
    with pytest.raises(ValueError, match="Estoque atual ausente"):
        gerar_recomendacoes(
            previsoes,
            _estoque_atual(("outro", 0.0)),
            _estoque_seguranca(("med_a", 0.0)),
        )
