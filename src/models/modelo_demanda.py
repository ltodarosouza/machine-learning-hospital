"""
O modelo aprende sete horizontes diretamente: para uma observação no dia ``t``,
estima o consumo em ``t + 1`` até ``t + 7``. Dessa forma não precisa alimentar
uma previsão de volta como lag para prever o dia seguinte, evitando acúmulo de
erro no horizonte do MVP.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import Pipeline

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.config import HORIZONTE_PREVISAO_DIAS


COLUNAS_SAIDA = [
    "medicamento_id",
    "data_previsao",
    "demanda_prevista",
    "intervalo_inferior",
    "intervalo_superior",
]
COLUNAS_OBRIGATORIAS = {"data", "medicamento_id", "consumo_unidades"}
CAMINHO_MODELO_PADRAO = Path(__file__).resolve().parents[2] / "models_output" / "modelo_demanda.joblib"
DADOS_MODELAGEM = Path(__file__).resolve().parents[2] / "data" / "processed" / "consumo_medicamentos.csv"
Z_INTERVALO = 1.0


@dataclass
class ModeloDemanda:
    """Artefato necessário para gerar previsões reproduzíveis."""

    pipeline: Pipeline
    colunas_preditivas: list[str]
    desvio_residual_por_medicamento: dict[str, float]


def preparar_dados_supervisionados(
    dados_features: pd.DataFrame, horizonte: int = HORIZONTE_PREVISAO_DIAS
) -> pd.DataFrame:
    """Cria pares ``features em t`` -> ``consumo em t + horizonte`` por medicamento."""
    _validar_dados_features(dados_features)
    if horizonte < 1:
        raise ValueError("O horizonte deve ser maior ou igual a 1.")

    dados = dados_features.copy()
    dados["data"] = pd.to_datetime(dados["data"])
    dados = dados.sort_values(["medicamento_id", "data"]).reset_index(drop=True)

    conjuntos = []
    for dias_a_frente in range(1, horizonte + 1):
        parte = dados.copy()
        grupo = parte.groupby("medicamento_id", sort=False)
        parte["_alvo_consumo"] = grupo["consumo_unidades"].shift(-dias_a_frente)
        parte["_data_alvo"] = grupo["data"].shift(-dias_a_frente)
        parte["horizonte_dias"] = dias_a_frente
        conjuntos.append(parte.dropna(subset=["_alvo_consumo", "_data_alvo"]))

    return pd.concat(conjuntos, ignore_index=True)


def treinar_modelo(
    dados_features: pd.DataFrame,
    horizonte: int = HORIZONTE_PREVISAO_DIAS,
    n_estimators: int = 100,
    random_state: int = 42,
) -> ModeloDemanda:
    #Treina uma Random Forest compartilhada entre medicamentos e horizontes.
    supervisionado = preparar_dados_supervisionados(dados_features, horizonte)
    colunas_preditivas = _colunas_preditivas(supervisionado)
    entrada = supervisionado[colunas_preditivas]
    alvo = supervisionado["_alvo_consumo"].astype(float)

    pre_processador = ColumnTransformer(
        transformers=[
            ("medicamento", _codificador_medicamento(), ["medicamento_id"]),
        ],
        remainder="passthrough",
        verbose_feature_names_out=False,
    )
    regressor = RandomForestRegressor(
        n_estimators=n_estimators,
        min_samples_leaf=3,
        random_state=random_state,
        n_jobs=-1,
    )
    pipeline = Pipeline([("pre_processamento", pre_processador), ("regressor", regressor)])
    pipeline.fit(entrada, alvo)

    residuos = alvo - pipeline.predict(entrada)
    desvios = (
        pd.DataFrame(
            {"medicamento_id": supervisionado["medicamento_id"], "residuo": residuos}
        )
        .groupby("medicamento_id")["residuo"]
        .std(ddof=0)
        .fillna(0.0)
        .to_dict()
    )
    return ModeloDemanda(pipeline, colunas_preditivas, desvios)


def prever_demanda(
    modelo: ModeloDemanda,
    dados_features: pd.DataFrame,
    data_corte: str | pd.Timestamp,
    horizonte: int = HORIZONTE_PREVISAO_DIAS,
) -> pd.DataFrame:
    #Prevê os próximos dias a partir da última feature disponível por medicamento.
    _validar_dados_features(dados_features)
    corte = pd.Timestamp(data_corte)
    dados = dados_features.copy()
    dados["data"] = pd.to_datetime(dados["data"])
    dados = dados[dados["data"] <= corte].sort_values(["medicamento_id", "data"])
    if dados.empty:
        raise ValueError("Não há dados de features até a data de corte informada.")

    ultimas_linhas = dados.groupby("medicamento_id", sort=False).tail(1).copy()
    colunas_base = [coluna for coluna in modelo.colunas_preditivas if coluna != "horizonte_dias"]
    faltantes = set(colunas_base).difference(ultimas_linhas.columns)
    if faltantes:
        raise ValueError("Features ausentes para a previsão: " + ", ".join(sorted(faltantes)))

    linhas = []
    for dias_a_frente in range(1, horizonte + 1):
        entrada = ultimas_linhas[colunas_base].copy()
        entrada["horizonte_dias"] = dias_a_frente
        entrada = entrada[modelo.colunas_preditivas]
        estimativas = np.maximum(modelo.pipeline.predict(entrada), 0.0)
        for (_, item), estimativa in zip(ultimas_linhas.iterrows(), estimativas, strict=True):
            desvio = float(modelo.desvio_residual_por_medicamento.get(item["medicamento_id"], 0.0))
            linhas.append(
                {
                    "medicamento_id": item["medicamento_id"],
                    "data_previsao": (corte + pd.Timedelta(days=dias_a_frente)).date().isoformat(),
                    "demanda_prevista": float(estimativa),
                    "intervalo_inferior": float(max(estimativa - Z_INTERVALO * desvio, 0.0)),
                    "intervalo_superior": float(estimativa + Z_INTERVALO * desvio),
                }
            )
    return pd.DataFrame(linhas, columns=COLUNAS_SAIDA).sort_values(
        ["medicamento_id", "data_previsao"]
    ).reset_index(drop=True)


def avaliar_validacao_temporal(
    dados_brutos: pd.DataFrame,
    data_corte: str | pd.Timestamp,
    horizonte: int = HORIZONTE_PREVISAO_DIAS,
    n_estimators: int = 100,
) -> pd.DataFrame:
    #Avalia o modelo em dados futuros, sem embaralhar a série temporal.
    from src.features.pipeline import gerar_features

    corte = pd.Timestamp(data_corte)
    bruto = dados_brutos.copy()
    bruto["data"] = pd.to_datetime(bruto["data"])
    historico = bruto[bruto["data"] <= corte]
    if historico.empty:
        raise ValueError("Não há histórico antes da data de corte para validação.")

    features_treino = gerar_features(historico)
    modelo = treinar_modelo(features_treino, horizonte=horizonte, n_estimators=n_estimators)
    previsao = prever_demanda(modelo, features_treino, corte, horizonte=horizonte)
    realizado = bruto[(bruto["data"] > corte) & (bruto["data"] <= corte + pd.Timedelta(days=horizonte))][
        ["medicamento_id", "data", "consumo_unidades"]
    ].copy()
    realizado["data_previsao"] = realizado.pop("data").dt.date.astype(str)

    comparacao = previsao.merge(realizado, on=["medicamento_id", "data_previsao"], how="inner")
    if comparacao.empty:
        raise ValueError("Não há consumo realizado no horizonte de validação.")
    comparacao.attrs["mae"] = float(
        mean_absolute_error(comparacao["consumo_unidades"], comparacao["demanda_prevista"])
    )
    return comparacao


def salvar_modelo(modelo: ModeloDemanda, caminho: Path = CAMINHO_MODELO_PADRAO) -> None:
    """Persiste o artefato treinado; o diretório de saída não é versionado."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, caminho)


def carregar_modelo(caminho: Path = CAMINHO_MODELO_PADRAO) -> ModeloDemanda:
    """Carrega um artefato salvo por :func:`salvar_modelo`."""
    return joblib.load(caminho)


def validar_saida_modelo(
    previsao: pd.DataFrame, medicamentos_esperados: set[str], horizonte: int = HORIZONTE_PREVISAO_DIAS
) -> None:
    """Confere o contrato de previsão consumido por recommendation/evaluation."""
    if list(previsao.columns) != COLUNAS_SAIDA:
        raise ValueError(f"Colunas da previsão não batem com o contrato: {list(previsao.columns)}")
    if set(previsao["medicamento_id"]) != medicamentos_esperados:
        raise ValueError("medicamento_id da previsão não bate com o esperado.")
    if not (previsao.groupby("medicamento_id").size() == horizonte).all():
        raise ValueError("Cada medicamento deve ter uma previsão por dia do horizonte.")
    if previsao[COLUNAS_SAIDA[2:]].isna().any().any() or (previsao[COLUNAS_SAIDA[2:]] < 0).any().any():
        raise ValueError("A previsão contém valores nulos ou negativos.")
    if (previsao["intervalo_inferior"] > previsao["demanda_prevista"]).any() or (
        previsao["intervalo_superior"] < previsao["demanda_prevista"]
    ).any():
        raise ValueError("Intervalo de previsão inconsistente.")


def _colunas_preditivas(dados: pd.DataFrame) -> list[str]:
    excluir = {"data", "consumo_unidades", "_alvo_consumo", "_data_alvo"}
    return [coluna for coluna in dados.columns if coluna not in excluir]


def _codificador_medicamento():
    from sklearn.preprocessing import OneHotEncoder

    return OneHotEncoder(handle_unknown="ignore", sparse_output=False)


def _validar_dados_features(dados: pd.DataFrame) -> None:
    faltantes = COLUNAS_OBRIGATORIAS.difference(dados.columns)
    if faltantes:
        raise ValueError("Dados de features sem colunas obrigatórias: " + ", ".join(sorted(faltantes)))
    if dados.empty:
        raise ValueError("Dados de features não podem estar vazios.")


def main() -> None:
    """Executa uma validação temporal e salva o modelo final reproduzível."""
    from src.features.pipeline import gerar_features

    bruto = pd.read_csv(DADOS_MODELAGEM)
    ultima_data = pd.to_datetime(bruto["data"]).max()
    corte_validacao = ultima_data - pd.Timedelta(days=HORIZONTE_PREVISAO_DIAS)

    comparacao = avaliar_validacao_temporal(bruto, corte_validacao)
    print(f"Validação temporal até {corte_validacao.date()}: MAE = {comparacao.attrs['mae']:.2f}")

    features_completas = gerar_features(bruto)
    modelo_final = treinar_modelo(features_completas)
    salvar_modelo(modelo_final)
    print(f"Modelo final salvo em: {CAMINHO_MODELO_PADRAO}")


if __name__ == "__main__":
    main()
