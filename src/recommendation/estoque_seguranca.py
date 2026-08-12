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
from numbers import Real

import numpy as np
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

    Todos os medicamentos devem existir nas duas entradas. Diferenças entre o
    histórico e a referência geram erro, em vez de descarte silencioso.
    """
    _validar_entrada(consumo_historico, medicamentos_referencia, fator_seguranca)

    consumo = consumo_historico[["medicamento_id", "consumo_unidades"]].copy()
    _converter_numerico_nao_negativo(consumo, "consumo_unidades", "consumo_historico")

    # ddof=0 considera o histórico fornecido como a população observada do MVP.
    variabilidade = (
        consumo.groupby("medicamento_id", as_index=False)["consumo_unidades"]
        .std(ddof=0)
        .rename(columns={"consumo_unidades": "desvio_padrao_consumo"})
    )
    referencias = medicamentos_referencia[
        ["medicamento_id", "prazo_entrega_dias"]
    ].copy()
    _converter_numerico_nao_negativo(
        referencias, "prazo_entrega_dias", "medicamentos_referencia"
    )

    resultado = referencias.merge(
        variabilidade, on="medicamento_id", how="left", validate="one_to_one"
    )
    buffer = (
        resultado["desvio_padrao_consumo"]
        * fator_seguranca
        * resultado["prazo_entrega_dias"].map(math.sqrt)
    )
    if not np.isfinite(buffer.to_numpy(dtype=float)).all():
        raise ValueError("O cálculo de estoque_seguranca produziu valor não finito.")
    resultado["estoque_seguranca"] = buffer.map(math.ceil)
    return resultado[COLUNAS_SAIDA].sort_values("medicamento_id").reset_index(drop=True)


def _validar_entrada(
    consumo_historico: pd.DataFrame,
    medicamentos_referencia: pd.DataFrame,
    fator_seguranca: float,
) -> None:
    if not isinstance(consumo_historico, pd.DataFrame):
        raise TypeError("consumo_historico deve ser um pandas.DataFrame.")
    if not isinstance(medicamentos_referencia, pd.DataFrame):
        raise TypeError("medicamentos_referencia deve ser um pandas.DataFrame.")
    faltantes_consumo = COLUNAS_CONSUMO.difference(consumo_historico.columns)
    faltantes_referencia = COLUNAS_REFERENCIA.difference(
        medicamentos_referencia.columns
    )
    if faltantes_consumo:
        raise ValueError(
            f"Histórico sem colunas obrigatórias: {sorted(faltantes_consumo)}."
        )
    if faltantes_referencia:
        raise ValueError(
            f"Referência sem colunas obrigatórias: {sorted(faltantes_referencia)}."
        )
    if consumo_historico.empty:
        raise ValueError("consumo_historico não pode estar vazio.")
    if medicamentos_referencia.empty:
        raise ValueError("medicamentos_referencia não pode estar vazio.")
    _validar_identificadores(consumo_historico, "consumo_historico")
    _validar_identificadores(medicamentos_referencia, "medicamentos_referencia")
    if medicamentos_referencia["medicamento_id"].duplicated().any():
        raise ValueError("medicamentos_referencia deve ter um prazo por medicamento.")
    medicamentos_consumo = set(consumo_historico["medicamento_id"])
    medicamentos_referencia_ids = set(medicamentos_referencia["medicamento_id"])
    sem_historico = sorted(medicamentos_referencia_ids - medicamentos_consumo)
    sem_referencia = sorted(medicamentos_consumo - medicamentos_referencia_ids)
    if sem_historico:
        raise ValueError(
            f"medicamentos_referencia sem histórico de consumo: {sem_historico}."
        )
    if sem_referencia:
        raise ValueError(
            f"consumo_historico sem medicamento na referência: {sem_referencia}."
        )
    if isinstance(fator_seguranca, (bool, np.bool_)):
        raise TypeError("fator_seguranca não aceita valor booleano.")
    if not isinstance(fator_seguranca, Real):
        raise TypeError("fator_seguranca deve ser numérico.")
    if not math.isfinite(float(fator_seguranca)):
        raise ValueError("fator_seguranca deve ser finito.")
    if fator_seguranca < 0:
        raise ValueError("fator_seguranca deve ser não negativo.")


def _validar_identificadores(df: pd.DataFrame, nome: str) -> None:
    identificadores = df["medicamento_id"]
    if identificadores.isna().any():
        raise ValueError(f"{nome}.medicamento_id contém valor ausente.")
    if not identificadores.map(lambda valor: isinstance(valor, str)).all():
        raise TypeError(f"{nome}.medicamento_id deve conter apenas strings.")
    if identificadores.str.strip().eq("").any():
        raise ValueError(f"{nome}.medicamento_id contém valor vazio.")
    if identificadores.ne(identificadores.str.strip()).any():
        raise ValueError(
            f"{nome}.medicamento_id não pode conter espaços nas extremidades."
        )


def _converter_numerico_nao_negativo(df: pd.DataFrame, coluna: str, nome: str) -> None:
    if df[coluna].map(lambda valor: isinstance(valor, (bool, np.bool_))).any():
        raise TypeError(f"{nome}.{coluna} não aceita valores booleanos.")
    try:
        df[coluna] = pd.to_numeric(df[coluna], errors="raise")
    except (TypeError, ValueError) as erro:
        raise ValueError(f"{nome}.{coluna} deve conter apenas números.") from erro
    if (
        df[coluna].isna().any()
        or not np.isfinite(df[coluna].to_numpy(dtype=float)).all()
    ):
        raise ValueError(f"{nome}.{coluna} deve conter apenas valores finitos.")
    if (df[coluna] < 0).any():
        raise ValueError(f"{nome}.{coluna} não pode conter valores negativos.")
