"""Features temporais de consumo da Issue #8.

As features são calculadas independentemente por ``medicamento_id`` e usam
somente observações anteriores à linha prevista. Isso evita vazamento da
variável alvo (``consumo_unidades``) durante o treino do modelo.
"""

import pandas as pd


COLUNAS_OBRIGATORIAS = {"data", "medicamento_id", "consumo_unidades"}
LAGS_DIAS = (1, 7, 14)
JANELAS_MEDIA_MOVEL_DIAS = (7, 14, 30)


def gerar_features_series_temporais(df: pd.DataFrame) -> pd.DataFrame:
    colunas_faltantes = COLUNAS_OBRIGATORIAS - set(df.columns)
    if colunas_faltantes:
        raise ValueError(
            "DataFrame sem as colunas obrigatórias: "
            + ", ".join(sorted(colunas_faltantes))
        )

    resultado = df.copy()
    resultado["data"] = pd.to_datetime(resultado["data"], errors="coerce")
    if resultado["data"].isna().any():
        raise ValueError("A coluna 'data' contém valores inválidos ou ausentes.")

    if resultado.duplicated(subset=["medicamento_id", "data"]).any():
        raise ValueError(
            "Há mais de uma observação para a mesma combinação de "
            "'medicamento_id' e 'data'."
        )

    resultado = resultado.sort_values(["medicamento_id", "data"]).reset_index(drop=True)
    consumo_por_medicamento = resultado.groupby("medicamento_id", sort=False)[
        "consumo_unidades"
    ]

    for dias in LAGS_DIAS:
        resultado[f"feat_lag_{dias}d"] = consumo_por_medicamento.shift(dias)

    # O shift garante que a média de uma data não inclua o consumo daquela data.
    consumo_anterior = consumo_por_medicamento.shift(1)
    for dias in JANELAS_MEDIA_MOVEL_DIAS:
        resultado[f"feat_media_movel_{dias}d"] = consumo_anterior.groupby(
            resultado["medicamento_id"], sort=False
        ).transform(lambda serie: serie.rolling(window=dias, min_periods=dias).mean())

    return resultado
