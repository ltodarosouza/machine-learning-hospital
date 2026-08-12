"""Pipeline robusto de features da Issue #10.

Integra as features temporais e de calendário/variáveis externas. Estratégia
para dados imperfeitos:

* consumo negativo é corrigido para zero, pois não existe consumo negativo;
* consumo ausente é preenchido pela mediana do medicamento (ou zero quando a
  série inteira está ausente);
* picos de consumo são limitados por medicamento ao intervalo de 3 IQRs;
* variáveis externas ausentes são preenchidas pela mediana da coluna e feriado
  ausente equivale a ``False``;
* linhas sem histórico suficiente para lags e médias móveis são descartadas.

O último item preserva a semântica das séries temporais: preencher uma média
móvel inexistente inventaria informação que o modelo não tinha naquele dia.
"""

from __future__ import annotations

import pandas as pd

from src.features.calendario_externas import gerar_features_calendario_externas
from src.features.series_temporais import gerar_features_series_temporais


COLUNAS_OBRIGATORIAS = {
    "data",
    "medicamento_id",
    "consumo_unidades",
    "feriado",
    "temperatura_media",
    "chuva_mm",
    "casos_dengue_regiao",
}
COLUNAS_EXTERNAS = ["temperatura_media", "chuva_mm", "casos_dengue_regiao"]


def gerar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Gera uma matriz de features pronta para treinamento, sem valores nulos.

    A entrada segue o schema de ``consumo_medicamentos.csv``. A saída preserva
    as colunas originais e acrescenta todas as colunas ``feat_*`` das Issues
    #8 e #9; as linhas iniciais de cada medicamento são removidas quando não
    há histórico suficiente para a média móvel de 30 dias.
    """
    _validar_entrada(df)
    resultado = df.copy()
    resultado["data"] = pd.to_datetime(resultado["data"], errors="coerce")
    if resultado["data"].isna().any():
        raise ValueError("A coluna 'data' contém valores inválidos ou ausentes.")
    if resultado["medicamento_id"].isna().any():
        raise ValueError("A coluna 'medicamento_id' não pode conter valores ausentes.")
    if resultado.duplicated(["medicamento_id", "data"]).any():
        raise ValueError("Há mais de uma observação para o mesmo medicamento e data.")

    resultado = resultado.sort_values(["medicamento_id", "data"]).reset_index(drop=True)
    resultado = _tratar_consumo(resultado)
    resultado = _tratar_variaveis_externas(resultado)
    resultado = gerar_features_series_temporais(resultado)
    resultado = gerar_features_calendario_externas(resultado)

    colunas_features = [coluna for coluna in resultado.columns if coluna.startswith("feat_")]
    resultado = resultado.dropna(subset=colunas_features).reset_index(drop=True)
    if resultado.empty:
        raise ValueError("Não há histórico suficiente para gerar features após o tratamento.")
    return resultado


def _tratar_consumo(df: pd.DataFrame) -> pd.DataFrame:
    resultado = df.copy()
    consumo = pd.to_numeric(resultado["consumo_unidades"], errors="coerce").clip(lower=0)
    mediana_por_medicamento = consumo.groupby(resultado["medicamento_id"]).transform("median")
    resultado["consumo_unidades"] = consumo.fillna(mediana_por_medicamento).fillna(0.0)

    def limitar_outliers(serie: pd.Series) -> pd.Series:
        primeiro_quartil = serie.quantile(0.25)
        terceiro_quartil = serie.quantile(0.75)
        iqr = terceiro_quartil - primeiro_quartil
        limite_inferior = max(0.0, primeiro_quartil - 3 * iqr)
        limite_superior = terceiro_quartil + 3 * iqr
        return serie.clip(lower=limite_inferior, upper=limite_superior)

    resultado["consumo_unidades"] = resultado.groupby("medicamento_id")[
        "consumo_unidades"
    ].transform(limitar_outliers)
    return resultado


def _tratar_variaveis_externas(df: pd.DataFrame) -> pd.DataFrame:
    resultado = df.copy()
    for coluna in COLUNAS_EXTERNAS:
        valores = pd.to_numeric(resultado[coluna], errors="coerce")
        mediana = valores.median()
        if pd.isna(mediana):
            raise ValueError(f"A coluna externa '{coluna}' não contém valores numéricos válidos.")
        resultado[coluna] = valores.fillna(mediana)
    resultado["feriado"] = resultado["feriado"].astype("boolean").fillna(False).astype(bool)
    return resultado


def _validar_entrada(df: pd.DataFrame) -> None:
    colunas_faltantes = COLUNAS_OBRIGATORIAS.difference(df.columns)
    if colunas_faltantes:
        raise ValueError(
            "DataFrame sem as colunas obrigatórias: " + ", ".join(sorted(colunas_faltantes))
        )
    if df.empty:
        raise ValueError("O DataFrame de entrada não pode estar vazio.")
