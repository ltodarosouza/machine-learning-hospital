"""Testes do modelo de previsão da Issue #12."""

import pandas as pd

from src.features.pipeline import gerar_features
from src.models.modelo_demanda import (
    avaliar_validacao_temporal,
    prever_demanda,
    treinar_modelo,
    validar_saida_modelo,
)


def _dados_brutos() -> pd.DataFrame:
    linhas = []
    for medicamento, base in (("med_a", 10), ("med_b", 30)):
        for indice, data in enumerate(pd.date_range("2025-01-01", periods=75, freq="D")):
            linhas.append(
                {
                    "data": data,
                    "medicamento_id": medicamento,
                    "consumo_unidades": base + indice % 7,
                    "feriado": False,
                    "temperatura_media": 27.0 + indice % 3,
                    "chuva_mm": float(indice % 5),
                    "casos_dengue_regiao": 8.0 + indice % 4,
                }
            )
    return pd.DataFrame(linhas)


def test_treino_e_previsao_respeitam_contrato() -> None:
    bruto = _dados_brutos()
    corte = pd.Timestamp("2025-03-08")
    features = gerar_features(bruto[bruto["data"] <= corte])

    modelo = treinar_modelo(features, n_estimators=10)
    previsao = prever_demanda(modelo, features, corte)

    validar_saida_modelo(previsao, {"med_a", "med_b"})
    assert len(previsao) == 14


def test_validacao_temporal_usa_apenas_historico_antes_do_corte() -> None:
    comparacao = avaliar_validacao_temporal(
        _dados_brutos(), data_corte="2025-03-08", n_estimators=10
    )

    assert len(comparacao) == 14
    assert comparacao.attrs["mae"] >= 0
    assert (pd.to_datetime(comparacao["data_previsao"]) > pd.Timestamp("2025-03-08")).all()
