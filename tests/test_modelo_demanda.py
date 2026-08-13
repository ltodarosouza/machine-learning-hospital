"""Testes do modelo de previsão da Issue #12."""

import numpy as np
import pandas as pd
import pytest

from src.features.pipeline import gerar_features
from src.models.modelo_demanda import (
    QUANTILE_ALPHA_OFICIAL,
    _colunas_preditivas,
    avaliar_validacao_temporal,
    preparar_dados_supervisionados,
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


def test_treinar_modelo_usa_quantile_alpha_oficial_por_padrao() -> None:
    """Issue #86: o padrão de produção passou a ser regressão quantílica, não MAE simétrico."""
    bruto = _dados_brutos()
    corte = pd.Timestamp("2025-03-08")
    features = gerar_features(bruto[bruto["data"] <= corte])

    modelo_padrao = treinar_modelo(features, n_estimators=10)
    regressor_padrao = modelo_padrao.pipeline.named_steps["regressor"]
    assert regressor_padrao.get_params()["objective"] == "reg:quantileerror"
    assert regressor_padrao.get_params()["quantile_alpha"] == QUANTILE_ALPHA_OFICIAL


def test_treinar_modelo_aceita_quantile_alpha_none_para_objetivo_simetrico_historico() -> None:
    bruto = _dados_brutos()
    corte = pd.Timestamp("2025-03-08")
    features = gerar_features(bruto[bruto["data"] <= corte])

    modelo_simetrico = treinar_modelo(features, n_estimators=10, quantile_alpha=None)
    regressor = modelo_simetrico.pipeline.named_steps["regressor"]
    assert regressor.get_params()["objective"] != "reg:quantileerror"


def test_treinar_modelo_rejeita_quantile_alpha_fora_do_intervalo() -> None:
    bruto = _dados_brutos()
    corte = pd.Timestamp("2025-03-08")
    features = gerar_features(bruto[bruto["data"] <= corte])

    with pytest.raises(ValueError):
        treinar_modelo(features, n_estimators=10, quantile_alpha=0.5)
    with pytest.raises(ValueError):
        treinar_modelo(features, n_estimators=10, quantile_alpha=1.0)


def test_quantile_alpha_oficial_reduz_subestimacao_frente_ao_objetivo_simetrico() -> None:
    """Mesma checagem da Issue #78 (test_modelo_demanda_assimetrico.py), agora no modelo oficial."""
    bruto = _dados_brutos()
    corte = pd.Timestamp("2025-03-08")
    features = gerar_features(bruto[bruto["data"] <= corte])

    modelo_oficial = treinar_modelo(features, n_estimators=30)
    modelo_simetrico = treinar_modelo(features, n_estimators=30, quantile_alpha=None)

    supervisionado = preparar_dados_supervisionados(features)
    entrada = supervisionado[modelo_oficial.colunas_preditivas]
    real = supervisionado["_alvo_consumo"].to_numpy()

    subestimacao_oficial = np.maximum(real - modelo_oficial.pipeline.predict(entrada), 0).sum()
    subestimacao_simetrica = np.maximum(real - modelo_simetrico.pipeline.predict(entrada), 0).sum()
    assert subestimacao_oficial < subestimacao_simetrica


def test_avaliar_validacao_temporal_aceita_override_de_quantile_alpha() -> None:
    comparacao = avaliar_validacao_temporal(
        _dados_brutos(), data_corte="2025-03-08", n_estimators=10, quantile_alpha=None
    )

    assert len(comparacao) == 14
    assert comparacao.attrs["mae"] >= 0


def test_colunas_operacionais_de_ruptura_nao_entram_como_features() -> None:
    colunas = _colunas_preditivas(
        pd.DataFrame(
            columns=[
                "data",
                "medicamento_id",
                "consumo_unidades",
                "dispensacao_unidades",
                "demanda_nao_atendida",
                "feat_lag_1d",
            ]
        )
    )

    assert "feat_lag_1d" in colunas
    assert "dispensacao_unidades" not in colunas
    assert "demanda_nao_atendida" not in colunas
