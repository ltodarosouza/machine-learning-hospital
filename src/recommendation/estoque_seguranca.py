"""Cálculo de estoque de segurança para a Issue #14.

O buffer protege o hospital contra oscilações normais de consumo durante o
prazo de reposição do fornecedor. A fórmula adotada no MVP é:

    estoque_seguranca = desvio_padrao_consumo * fator_seguranca * sqrt(prazo_entrega_dias)

O ``fator_seguranca`` padrão de 1,65 representa aproximadamente 95% de nível
de serviço em uma aproximação normal. É uma premissa explícita e pode ser
ajustada pelo motor de recomendação conforme a criticidade do medicamento.
"""

from __future__ import annotations

import math

import pandas as pd


COLUNAS_CONSUMO = {"medicamento_id", "consumo_unidades"}
COLUNAS_REFERENCIA = {"medicamento_id", "prazo_entrega_dias"}
COLUNAS_SAIDA = [
    "medicamento_id",
    "desvio_padrao_consumo",
    "prazo_entrega_dias",
    "estoque_seguranca",
]
FATOR_SEGURANCA_PADRAO = 1.65


def calcular_estoque_seguranca(
    consumo_historico: pd.DataFrame,
    medicamentos_referencia: pd.DataFrame,
    fator_seguranca: float = FATOR_SEGURANCA_PADRAO,
) -> pd.DataFrame:
    """Calcula o estoque de segurança por medicamento.

    Args:
        consumo_historico: histórico no schema de ``consumo_diario.csv``;
            requer ``medicamento_id`` e ``consumo_unidades``.
        medicamentos_referencia: tabela ``medicamentos_ref.csv``; requer
            ``medicamento_id`` e ``prazo_entrega_dias``.
        fator_seguranca: multiplicador do desvio-padrão; deve ser não negativo.

    Returns:
        DataFrame no nível de medicamento, com os componentes do cálculo e o
        buffer ``estoque_seguranca``. O resultado é arredondado para cima pois
        não é possível manter uma fração de unidade em estoque.
    """
    _validar_entrada(consumo_historico, medicamentos_referencia, fator_seguranca)

    consumo = consumo_historico[["medicamento_id", "consumo_unidades"]].copy()
    consumo["consumo_unidades"] = pd.to_numeric(consumo["consumo_unidades"], errors="raise")
    if (consumo["consumo_unidades"] < 0).any():
        raise ValueError("consumo_unidades não pode conter valores negativos.")

    # ddof=0 considera o histórico fornecido como a população observada do MVP.
    variabilidade = (
        consumo.groupby("medicamento_id", as_index=False)["consumo_unidades"]
        .std(ddof=0)
        .rename(columns={"consumo_unidades": "desvio_padrao_consumo"})
    )
    referencias = medicamentos_referencia[["medicamento_id", "prazo_entrega_dias"]].copy()
    referencias["prazo_entrega_dias"] = pd.to_numeric(
        referencias["prazo_entrega_dias"], errors="raise"
    )
    if (referencias["prazo_entrega_dias"] < 0).any():
        raise ValueError("prazo_entrega_dias não pode conter valores negativos.")

    resultado = referencias.merge(variabilidade, on="medicamento_id", how="inner")
    resultado["estoque_seguranca"] = (
        resultado["desvio_padrao_consumo"]
        * fator_seguranca
        * resultado["prazo_entrega_dias"].map(math.sqrt)
    ).map(math.ceil)
    return resultado[COLUNAS_SAIDA].sort_values("medicamento_id").reset_index(drop=True)


def _validar_entrada(
    consumo_historico: pd.DataFrame,
    medicamentos_referencia: pd.DataFrame,
    fator_seguranca: float,
) -> None:
    faltantes_consumo = COLUNAS_CONSUMO.difference(consumo_historico.columns)
    faltantes_referencia = COLUNAS_REFERENCIA.difference(medicamentos_referencia.columns)
    if faltantes_consumo:
        raise ValueError(f"Histórico sem colunas obrigatórias: {sorted(faltantes_consumo)}.")
    if faltantes_referencia:
        raise ValueError(f"Referência sem colunas obrigatórias: {sorted(faltantes_referencia)}.")
    if consumo_historico.empty:
        raise ValueError("consumo_historico não pode estar vazio.")
    if medicamentos_referencia["medicamento_id"].duplicated().any():
        raise ValueError("medicamentos_referencia deve ter um prazo por medicamento.")
    if fator_seguranca < 0:
        raise ValueError("fator_seguranca deve ser não negativo.")
