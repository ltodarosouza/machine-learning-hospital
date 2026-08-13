"""Testes do candidato de previsão assimétrica (Issue #78)."""

import numpy as np
import pandas as pd
import pytest

from src.features.pipeline import gerar_features
from src.models.modelo_demanda import prever_demanda, preparar_dados_supervisionados, validar_saida_modelo
from src.models.modelo_demanda_assimetrico import (
    avaliar_validacao_temporal_quantilico,
    treinar_modelo_quantilico,
)


def _dados_brutos_ruidosos(seed: int = 0) -> pd.DataFrame:
    """Consumo com ruído assimétrico: picos ocasionais bem acima da média.

    Um modelo treinado para a mediana/MAE tende a ignorar esses picos (eles
    são minoria); um quantil alto deve puxar a previsão para cima e reduzir
    quantos deles ficam subestimados.
    """
    rng = np.random.default_rng(seed)
    linhas = []
    for medicamento, base in (("med_a", 20), ("med_b", 40)):
        for indice, data in enumerate(pd.date_range("2025-01-01", periods=120, freq="D")):
            pico = 25.0 if rng.random() < 0.1 else 0.0
            linhas.append(
                {
                    "data": data,
                    "medicamento_id": medicamento,
                    "consumo_unidades": base + indice % 7 + pico,
                    "feriado": False,
                    "temperatura_media": 27.0 + indice % 3,
                    "chuva_mm": float(indice % 5),
                    "casos_dengue_regiao": 8.0 + indice % 4,
                }
            )
    return pd.DataFrame(linhas)


def test_quantile_alpha_fora_do_intervalo_e_rejeitado() -> None:
    bruto = _dados_brutos_ruidosos()
    features = gerar_features(bruto[bruto["data"] <= pd.Timestamp("2025-03-08")])

    with pytest.raises(ValueError):
        treinar_modelo_quantilico(features, quantile_alpha=0.5, n_estimators=10)
    with pytest.raises(ValueError):
        treinar_modelo_quantilico(features, quantile_alpha=1.0, n_estimators=10)
    with pytest.raises(ValueError):
        treinar_modelo_quantilico(features, quantile_alpha=0.4, n_estimators=10)


def test_treino_e_previsao_respeitam_o_mesmo_contrato_do_modelo_oficial() -> None:
    bruto = _dados_brutos_ruidosos()
    corte = pd.Timestamp("2025-03-08")
    features = gerar_features(bruto[bruto["data"] <= corte])

    modelo = treinar_modelo_quantilico(features, quantile_alpha=0.7, n_estimators=20)
    previsao = prever_demanda(modelo, features, corte)

    validar_saida_modelo(previsao, {"med_a", "med_b"})


def test_quantile_alpha_maior_reduz_subestimacao_no_treino() -> None:
    bruto = _dados_brutos_ruidosos()
    corte = pd.Timestamp("2025-04-15")
    features = gerar_features(bruto[bruto["data"] <= corte])

    modelo_mediano = treinar_modelo_quantilico(features, quantile_alpha=0.55, n_estimators=30)
    modelo_alto = treinar_modelo_quantilico(features, quantile_alpha=0.9, n_estimators=30)

    supervisionado = preparar_dados_supervisionados(features)
    entrada = supervisionado[modelo_mediano.colunas_preditivas]
    previsto_mediano = modelo_mediano.pipeline.predict(entrada)
    previsto_alto = modelo_alto.pipeline.predict(entrada)

    real = supervisionado["_alvo_consumo"].to_numpy()
    subestimacao_mediano = np.maximum(real - previsto_mediano, 0).sum()
    subestimacao_alta = np.maximum(real - previsto_alto, 0).sum()

    assert subestimacao_alta < subestimacao_mediano


def test_validacao_temporal_usa_apenas_historico_antes_do_corte() -> None:
    comparacao = avaliar_validacao_temporal_quantilico(
        _dados_brutos_ruidosos(), data_corte="2025-04-15", quantile_alpha=0.7, n_estimators=20
    )

    assert len(comparacao) == 14
    assert comparacao.attrs["mae"] >= 0
    assert (pd.to_datetime(comparacao["data_previsao"]) > pd.Timestamp("2025-04-15")).all()
