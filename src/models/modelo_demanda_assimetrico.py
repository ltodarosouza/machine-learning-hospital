"""Candidato de previsão assimétrica (Issue #78).

O modelo oficial (`modelo_demanda.py`) treina para MAE, que trata subestimar
e superestimar como erros equivalentes — o diagnóstico da Issue #76 mostrou
que isso pode reduzir o erro médio e ainda piorar ruptura nos poucos picos
que mais custam. Este módulo testa regressão quantílica do XGBoost
(`reg:quantileerror`) com `quantile_alpha > 0.5`: o quantil pedido fica acima
da mediana da distribuição condicional do consumo, então o modelo aprende a
prever mais alto para reduzir a frequência de subestimação.

Reaproveita a mesma preparação de dados e o mesmo artefato (`ModeloDemanda`)
do modelo oficial — só troca a função de perda do `XGBRegressor`. Nunca
escreve em `models_output/modelo_demanda.joblib`; esse artefato continua
vindo exclusivamente de `modelo_demanda.py`. Fora do escopo da Issue #78:
isto não altera a política de estoque/compra (`impacto_simulado.py`), só a
previsão que alimenta ela.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.models.artefato import ModeloDemanda
from src.models.modelo_demanda import (
    HIPERPARAMETROS_XGBOOST,
    _codificador_medicamento,
    _colunas_preditivas,
    prever_demanda,
    preparar_dados_supervisionados,
)
from src.utils.config import HORIZONTE_PREVISAO_DIAS

__all__ = [
    "treinar_modelo_quantilico",
    "avaliar_validacao_temporal_quantilico",
]


def treinar_modelo_quantilico(
    dados_features: pd.DataFrame,
    quantile_alpha: float,
    horizonte: int = HORIZONTE_PREVISAO_DIAS,
    n_estimators: int = 500,
    random_state: int = 42,
) -> ModeloDemanda:
    """Mesma estrutura de `modelo_demanda.treinar_modelo`, trocando a função de perda.

    `quantile_alpha` deve ficar estritamente entre 0.5 e 1.0: é o mecanismo
    que faz o XGBoost penalizar mais subestimar do que superestimar (pinball
    loss assimétrica). `quantile_alpha=0.5` reproduziria aproximadamente a
    mediana condicional, não o objetivo desta issue, por isso é rejeitado
    aqui em vez de silenciosamente aceito.
    """
    if not 0.5 < quantile_alpha < 1.0:
        raise ValueError(
            "quantile_alpha deve estar estritamente entre 0.5 e 1.0 para "
            "penalizar subestimação mais que superestimação."
        )

    supervisionado = preparar_dados_supervisionados(dados_features, horizonte)
    colunas_preditivas = _colunas_preditivas(supervisionado)
    entrada = supervisionado[colunas_preditivas]
    alvo = supervisionado["_alvo_consumo"].astype(float)

    pre_processador = ColumnTransformer(
        transformers=[("medicamento", _codificador_medicamento(), ["medicamento_id"])],
        remainder="passthrough",
        verbose_feature_names_out=False,
    )
    regressor = XGBRegressor(
        n_estimators=n_estimators,
        random_state=random_state,
        objective="reg:quantileerror",
        quantile_alpha=quantile_alpha,
        **HIPERPARAMETROS_XGBOOST,
    )
    pipeline = Pipeline([("pre_processamento", pre_processador), ("regressor", regressor)])
    pipeline.fit(entrada, alvo)

    residuos = alvo - pipeline.predict(entrada)
    desvios = (
        pd.DataFrame({"medicamento_id": supervisionado["medicamento_id"], "residuo": residuos})
        .groupby("medicamento_id")["residuo"]
        .std(ddof=0)
        .fillna(0.0)
        .to_dict()
    )
    return ModeloDemanda(pipeline, colunas_preditivas, desvios)


def avaliar_validacao_temporal_quantilico(
    dados_brutos: pd.DataFrame,
    data_corte: str | pd.Timestamp,
    quantile_alpha: float,
    horizonte: int = HORIZONTE_PREVISAO_DIAS,
    n_estimators: int = 500,
) -> pd.DataFrame:
    """Mesma metodologia de `modelo_demanda.avaliar_validacao_temporal`, para o candidato.

    Treina só com `data <= data_corte` e avalia no horizonte seguinte — sem
    vazamento temporal, mesma garantia do modelo oficial.
    """
    from src.features.pipeline import gerar_features

    corte = pd.Timestamp(data_corte)
    bruto = dados_brutos.copy()
    bruto["data"] = pd.to_datetime(bruto["data"])
    historico = bruto[bruto["data"] <= corte]
    if historico.empty:
        raise ValueError("Não há histórico antes da data de corte para validação.")

    features_treino = gerar_features(historico)
    modelo = treinar_modelo_quantilico(
        features_treino, quantile_alpha, horizonte=horizonte, n_estimators=n_estimators
    )
    previsao = prever_demanda(modelo, features_treino, corte, horizonte=horizonte)
    realizado = bruto[
        (bruto["data"] > corte) & (bruto["data"] <= corte + pd.Timedelta(days=horizonte))
    ][["medicamento_id", "data", "consumo_unidades"]].copy()
    realizado["data_previsao"] = realizado.pop("data").dt.date.astype(str)

    comparacao = previsao.merge(realizado, on=["medicamento_id", "data_previsao"], how="inner")
    if comparacao.empty:
        raise ValueError("Não há consumo realizado no horizonte de validação.")
    comparacao.attrs["mae"] = float(
        mean_absolute_error(comparacao["consumo_unidades"], comparacao["demanda_prevista"])
    )
    return comparacao
