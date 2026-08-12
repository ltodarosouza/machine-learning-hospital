"""Experimento que decidiu a troca de Random Forest para XGBoost em `src/models/modelo_demanda.py`.

Compara Random Forest (com e sem as features de ruído `estoque_disponivel`/
`entradas_unidades`), Gradient Boosting e XGBoost, todos sob a mesma
metodologia de validação temporal sem vazamento usada na Issue #13
(retreina do zero a cada janela de teste, só usa `data <= corte`).

Não faz parte do pipeline de produção — é um script de decisão, mantido no
repositório para reprodutibilidade. Resultado documentado em
`src/models/README.md` e `docs/arquitetura/RESULTADOS_MODELAGEM.md`.

Uso:
    python scripts/comparar_algoritmos_modelo.py
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

REPO = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO))

from src.features.pipeline import gerar_features
from src.models.modelo_demanda import _colunas_preditivas, preparar_dados_supervisionados
from src.utils.config import HORIZONTE_PREVISAO_DIAS

try:
    from xgboost import XGBRegressor

    TEM_XGBOOST = True
except ImportError:
    TEM_XGBOOST = False

COLUNAS_EXCLUIR_RUIDO = {"estoque_disponivel", "entradas_unidades"}


def _colunas_preditivas_customizadas(dados: pd.DataFrame, excluir_ruido: bool) -> list[str]:
    colunas = _colunas_preditivas(dados)
    if excluir_ruido:
        colunas = [c for c in colunas if c not in COLUNAS_EXCLUIR_RUIDO]
    return colunas


def _treinar(dados_features, horizonte, construir_regressor, excluir_ruido):
    supervisionado = preparar_dados_supervisionados(dados_features, horizonte)
    colunas_preditivas = _colunas_preditivas_customizadas(supervisionado, excluir_ruido)
    entrada = supervisionado[colunas_preditivas]
    alvo = supervisionado["_alvo_consumo"].astype(float)

    pre = ColumnTransformer(
        transformers=[("medicamento", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["medicamento_id"])],
        remainder="passthrough",
        verbose_feature_names_out=False,
    )
    pipeline = Pipeline([("pre", pre), ("reg", construir_regressor())])
    pipeline.fit(entrada, alvo)
    return pipeline, colunas_preditivas


def _prever(pipeline, colunas_preditivas, dados_features, data_corte, horizonte):
    corte = pd.Timestamp(data_corte)
    dados = dados_features.copy()
    dados["data"] = pd.to_datetime(dados["data"])
    dados = dados[dados["data"] <= corte].sort_values(["medicamento_id", "data"])
    ultimas = dados.groupby("medicamento_id", sort=False).tail(1).copy()
    colunas_base = [c for c in colunas_preditivas if c != "horizonte_dias"]

    linhas = []
    for h in range(1, horizonte + 1):
        entrada = ultimas[colunas_base].copy()
        entrada["horizonte_dias"] = h
        entrada = entrada[colunas_preditivas]
        estimativas = np.maximum(pipeline.predict(entrada), 0.0)
        for (_, item), est in zip(ultimas.iterrows(), estimativas, strict=True):
            linhas.append(
                {
                    "medicamento_id": item["medicamento_id"],
                    "data_previsao": (corte + pd.Timedelta(days=h)).date().isoformat(),
                    "demanda_prevista": float(est),
                }
            )
    return pd.DataFrame(linhas)


def avaliar_config(dados_brutos, data_inicio_teste, data_fim_teste, horizonte, construir_regressor, excluir_ruido, nome):
    inicio = pd.Timestamp(data_inicio_teste)
    fim = pd.Timestamp(data_fim_teste)
    corte = inicio - pd.Timedelta(days=1)

    todas_previsoes = []
    while corte + pd.Timedelta(days=1) <= fim:
        historico = dados_brutos[pd.to_datetime(dados_brutos["data"]) <= corte]
        features_treino = gerar_features(historico)
        pipeline, colunas = _treinar(features_treino, horizonte, construir_regressor, excluir_ruido)
        previsao = _prever(pipeline, colunas, features_treino, corte, horizonte)
        todas_previsoes.append(previsao)
        corte += pd.Timedelta(days=horizonte)

    previsoes = pd.concat(todas_previsoes, ignore_index=True)
    real = dados_brutos[["data", "medicamento_id", "consumo_unidades"]].copy()
    real["data_previsao"] = pd.to_datetime(real["data"]).dt.date.astype(str)
    comparacao = previsoes.merge(
        real[["data_previsao", "medicamento_id", "consumo_unidades"]], on=["medicamento_id", "data_previsao"], how="inner"
    )

    mae = mean_absolute_error(comparacao["consumo_unidades"], comparacao["demanda_prevista"])
    com_consumo_positivo = comparacao[comparacao["consumo_unidades"] > 0]
    mape = (
        (com_consumo_positivo["consumo_unidades"] - com_consumo_positivo["demanda_prevista"]).abs()
        / com_consumo_positivo["consumo_unidades"]
    ).mean() * 100
    print(f"{nome}: MAE={mae:.3f} MAPE={mape:.1f}%")
    return mae, mape


def main() -> None:
    dados_brutos = pd.read_csv(REPO / "data" / "processed" / "consumo_medicamentos.csv")
    ultima_data = pd.to_datetime(dados_brutos["data"]).max()
    data_fim_teste = ultima_data.date().isoformat()
    data_inicio_teste = (ultima_data - pd.Timedelta(days=4 * HORIZONTE_PREVISAO_DIAS - 1)).date().isoformat()

    print(f"Período de teste: {data_inicio_teste} a {data_fim_teste}")
    print(f"XGBoost disponível: {TEM_XGBOOST}\n")

    configs = [
        ("Random Forest (original da Issue #12)", lambda: RandomForestRegressor(n_estimators=100, min_samples_leaf=3, random_state=42, n_jobs=-1), False),
        ("Random Forest sem features de ruído", lambda: RandomForestRegressor(n_estimators=100, min_samples_leaf=3, random_state=42, n_jobs=-1), True),
        ("Random Forest tunado, sem ruído", lambda: RandomForestRegressor(n_estimators=400, min_samples_leaf=5, max_depth=14, random_state=42, n_jobs=-1), True),
        ("Gradient Boosting (scikit-learn), sem ruído", lambda: GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=42), True),
    ]
    if TEM_XGBOOST:
        configs.append(
            (
                "XGBoost, sem ruído",
                lambda: XGBRegressor(n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1),
                True,
            )
        )
    else:
        print("xgboost não instalado (pip install xgboost) — pulando essa configuração.\n")

    resultados = []
    for nome, construir, excluir_ruido in configs:
        inicio_cronometro = time.time()
        mae, mape = avaliar_config(dados_brutos, data_inicio_teste, data_fim_teste, HORIZONTE_PREVISAO_DIAS, construir, excluir_ruido, nome)
        duracao = time.time() - inicio_cronometro
        resultados.append((nome, mae, mape, duracao))
        print(f"  (levou {duracao:.1f}s)\n")

    print("\n=== RESUMO (ordenado por MAE) ===")
    for nome, mae, mape, duracao in sorted(resultados, key=lambda r: r[1]):
        print(f"{nome:45s} MAE={mae:6.3f}  MAPE={mape:5.1f}%  ({duracao:.0f}s)")


if __name__ == "__main__":
    main()
