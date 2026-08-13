"""Métricas preditivas canônicas compartilhadas pela avaliação."""

from __future__ import annotations

import pandas as pd


def calcular_metricas(comparacao: pd.DataFrame) -> pd.DataFrame:
    """Calcula MAE e MAPE por medicamento e método.

    A política para divisão por zero exclui do MAPE os dias com consumo real
    igual a zero. Esses dias continuam participando do MAE.
    """
    comparacao = comparacao.copy()
    comparacao["erro_absoluto"] = (
        comparacao["consumo_unidades"] - comparacao["demanda_prevista"]
    ).abs()

    com_consumo_positivo = comparacao[comparacao["consumo_unidades"] > 0].copy()
    com_consumo_positivo["erro_percentual"] = (
        com_consumo_positivo["erro_absoluto"] / com_consumo_positivo["consumo_unidades"]
    ) * 100

    mae = (
        comparacao.groupby(["metodo", "medicamento_id"])["erro_absoluto"]
        .mean()
        .rename("mae")
    )
    mape = (
        com_consumo_positivo.groupby(["metodo", "medicamento_id"])["erro_percentual"]
        .mean()
        .rename("mape")
    )
    por_medicamento = pd.concat([mae, mape], axis=1).reset_index()

    agregado = (
        comparacao.groupby("metodo")["erro_absoluto"].mean().rename("mae").reset_index()
    )
    agregado_mape = (
        com_consumo_positivo.groupby("metodo")["erro_percentual"]
        .mean()
        .rename("mape")
        .reset_index()
    )
    agregado = agregado.merge(agregado_mape, on="metodo")
    agregado["medicamento_id"] = "TODOS"
    return pd.concat(
        [por_medicamento, agregado[["metodo", "medicamento_id", "mae", "mape"]]],
        ignore_index=True,
    )
