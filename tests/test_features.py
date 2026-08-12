"""Testes de contrato e integração do pipeline de features."""

import pandas as pd
import pytest

from src.features.pipeline import gerar_features


FEATURES_ESPERADAS = {
    "feat_lag_1d",
    "feat_lag_7d",
    "feat_lag_14d",
    "feat_media_movel_7d",
    "feat_media_movel_14d",
    "feat_media_movel_30d",
    "feat_dia_semana",
    "feat_fim_de_semana",
    "feat_mes",
    "feat_feriado",
    "feat_casos_dengue_lag7",
    "feat_temperatura_media_norm",
    "feat_chuva_mm_norm",
    "feat_casos_dengue_regiao_norm",
}


def _dados_exemplo() -> pd.DataFrame:
    datas = pd.date_range("2025-01-01", periods=35, freq="D")
    dados = pd.DataFrame(
        {
            "data": datas,
            "medicamento_id": "med_a",
            "consumo_unidades": [10.0] * 35,
            "feriado": pd.Series([False] * 35, dtype=object),
            "temperatura_media": 28.0,
            "chuva_mm": 2.0,
            "casos_dengue_regiao": 5.0,
        }
    )
    dados.loc[1, "consumo_unidades"] = None
    dados.loc[2, "consumo_unidades"] = -10
    dados.loc[20, "consumo_unidades"] = 1_000_000
    dados.loc[3, "temperatura_media"] = None
    dados.loc[4, "feriado"] = None
    return dados


def test_pipeline_trata_lacunas_outliers_e_remove_linhas_sem_historico() -> None:
    saida = gerar_features(_dados_exemplo())

    assert len(saida) == 5  # média móvel de 30 dias exige descartar as 30 primeiras linhas
    assert not saida.filter(regex=r"^feat_").isna().any().any()
    assert (saida["consumo_unidades"] >= 0).all()
    assert saida["consumo_unidades"].max() == 10


def test_saida_respeita_contrato_de_features() -> None:
    entrada = _dados_exemplo()

    saida = gerar_features(entrada)

    assert set(entrada.columns).issubset(saida.columns)
    assert FEATURES_ESPERADAS.issubset(saida.columns)
    assert not saida[list(FEATURES_ESPERADAS)].isna().any().any()
    assert pd.api.types.is_datetime64_any_dtype(saida["data"])
    assert saida.equals(saida.sort_values(["medicamento_id", "data"]).reset_index(drop=True))


def test_rejeita_medicamento_sem_historico_suficiente() -> None:
    entrada = _dados_exemplo().iloc[:30]

    with pytest.raises(ValueError, match="histórico suficiente"):
        gerar_features(entrada)


def test_rejeita_entrada_fora_do_contrato() -> None:
    entrada = _dados_exemplo().drop(columns="casos_dengue_regiao")

    with pytest.raises(ValueError, match="casos_dengue_regiao"):
        gerar_features(entrada)


def test_normalizacao_externa_nao_usa_estatisticas_de_datas_futuras() -> None:
    dados = _dados_exemplo()
    dados_futuro_alterado = dados.copy()
    dados_futuro_alterado.loc[30:, "temperatura_media"] = 1_000.0

    base = gerar_features(dados)
    com_futuro_alterado = gerar_features(dados_futuro_alterado)

    colunas = ["data", "feat_temperatura_media_norm"]
    corte = pd.Timestamp("2025-01-30")
    esperado = base.loc[base["data"] <= corte, colunas].reset_index(drop=True)
    observado = com_futuro_alterado.loc[
        com_futuro_alterado["data"] <= corte, colunas
    ].reset_index(drop=True)
    pd.testing.assert_frame_equal(esperado, observado)
