"""Testes de contrato e casos de borda do modelo de demanda."""

import numpy as np
import pandas as pd
import pytest

from src.models.modelo_demanda import (
    COLUNAS_SAIDA,
    ModeloDemanda,
    prever_demanda,
    validar_saida_modelo,
)


class _PipelineConstante:
    def __init__(self, valor: float) -> None:
        self.valor = valor

    def predict(self, entrada: pd.DataFrame) -> np.ndarray:
        return np.full(len(entrada), self.valor, dtype=float)


def _features_minimas() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data": ["2025-01-01", "2025-01-02"],
            "medicamento_id": ["med_a", "med_b"],
            "consumo_unidades": [10.0, 20.0],
            "feat_lag_1d": [9.0, 19.0],
        }
    )


def test_previsao_respeita_contrato_para_demanda_zero() -> None:
    modelo = ModeloDemanda(
        pipeline=_PipelineConstante(0.0),
        colunas_preditivas=["medicamento_id", "feat_lag_1d", "horizonte_dias"],
        desvio_residual_por_medicamento={"med_a": 0.0, "med_b": 0.0},
    )

    previsao = prever_demanda(modelo, _features_minimas(), "2025-01-02")

    assert list(previsao.columns) == COLUNAS_SAIDA
    assert len(previsao) == 14
    assert (previsao["demanda_prevista"] == 0.0).all()
    assert (previsao["intervalo_inferior"] == 0.0).all()
    assert (previsao["intervalo_superior"] == 0.0).all()
    validar_saida_modelo(previsao, {"med_a", "med_b"})


def test_previsao_limita_estimativa_negativa_em_zero() -> None:
    modelo = ModeloDemanda(
        pipeline=_PipelineConstante(-5.0),
        colunas_preditivas=["medicamento_id", "feat_lag_1d", "horizonte_dias"],
        desvio_residual_por_medicamento={},
    )

    previsao = prever_demanda(modelo, _features_minimas(), "2025-01-02", horizonte=1)

    colunas_numericas = ["demanda_prevista", "intervalo_inferior", "intervalo_superior"]
    assert (previsao[colunas_numericas] == 0).all().all()


def test_validador_rejeita_saida_fora_do_contrato() -> None:
    previsao = pd.DataFrame(
        {
            "medicamento_id": ["med_a"],
            "data_previsao": ["2025-01-03"],
            "demanda_prevista": [1.0],
        }
    )

    with pytest.raises(ValueError, match="Colunas da previsão"):
        validar_saida_modelo(previsao, {"med_a"}, horizonte=1)
