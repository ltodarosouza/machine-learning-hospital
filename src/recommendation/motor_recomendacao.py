"""Motor base de recomendação de compra de medicamentos.

A demanda prevista para cada dia do horizonte é somada por medicamento antes
da aplicação da fórmula definida em ``CONTRATOS.md``. O resultado nunca é
negativo: quando estoque e pedidos já cobrem demanda e segurança, a compra é
zero.
"""

from __future__ import annotations

import pandas as pd

COLUNAS_PREVISOES = {"medicamento_id", "demanda_prevista"}
COLUNAS_ESTOQUE = {"medicamento_id", "estoque_disponivel"}
COLUNAS_SEGURANCA = {"medicamento_id", "estoque_seguranca"}
COLUNAS_PEDIDOS = {"medicamento_id", "quantidade"}
COLUNAS_SAIDA = [
    "medicamento_id",
    "compra_recomendada",
    "risco_falta",
    "risco_vencimento",
    "justificativa",
]


def gerar_recomendacoes(
    previsoes: pd.DataFrame,
    estoque_atual: pd.DataFrame,
    estoque_seguranca: pd.DataFrame,
    pedidos_pendentes: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Calcula uma recomendação por medicamento para o horizonte previsto.

    ``previsoes`` segue a seção 3 do contrato. ``estoque_atual`` contém o
    saldo mais recente de cada medicamento, ``estoque_seguranca`` recebe a
    saída da Issue #14 e ``pedidos_pendentes`` segue a seção 1.5. Pedidos
    ausentes equivalem a zero.
    """
    _validar_colunas(previsoes, COLUNAS_PREVISOES, "previsões")
    _validar_colunas(estoque_atual, COLUNAS_ESTOQUE, "estoque atual")
    _validar_colunas(estoque_seguranca, COLUNAS_SEGURANCA, "estoque de segurança")
    if previsoes.empty:
        raise ValueError("As previsões não podem estar vazias.")

    pedidos = (
        pd.DataFrame(columns=["medicamento_id", "quantidade"])
        if pedidos_pendentes is None
        else pedidos_pendentes.copy()
    )
    _validar_colunas(pedidos, COLUNAS_PEDIDOS, "pedidos pendentes")

    previsoes_tratadas = previsoes[["medicamento_id", "demanda_prevista"]].copy()
    estoque_tratado = estoque_atual[["medicamento_id", "estoque_disponivel"]].copy()
    seguranca_tratada = estoque_seguranca[
        ["medicamento_id", "estoque_seguranca"]
    ].copy()
    pedidos_tratados = pedidos[["medicamento_id", "quantidade"]].copy()

    _validar_identificadores(previsoes_tratadas, "previsões")
    _validar_identificadores(estoque_tratado, "estoque atual")
    _validar_identificadores(seguranca_tratada, "estoque de segurança")
    if not pedidos_tratados.empty:
        _validar_identificadores(pedidos_tratados, "pedidos pendentes")

    _validar_unicidade(estoque_tratado, "estoque atual")
    _validar_unicidade(seguranca_tratada, "estoque de segurança")

    _converter_nao_negativo(previsoes_tratadas, "demanda_prevista")
    _converter_nao_negativo(estoque_tratado, "estoque_disponivel")
    _converter_nao_negativo(seguranca_tratada, "estoque_seguranca")
    _converter_nao_negativo(pedidos_tratados, "quantidade")

    medicamentos = set(previsoes_tratadas["medicamento_id"])
    _validar_cobertura(medicamentos, estoque_tratado, "estoque atual")
    _validar_cobertura(medicamentos, seguranca_tratada, "estoque de segurança")

    demanda = previsoes_tratadas.groupby("medicamento_id", as_index=False)[
        "demanda_prevista"
    ].sum()
    pedidos_agregados = (
        pedidos_tratados.groupby("medicamento_id", as_index=False)["quantidade"]
        .sum()
        .rename(columns={"quantidade": "pedidos_confirmados"})
    )

    resultado = demanda.merge(
        estoque_tratado, on="medicamento_id", validate="one_to_one"
    )
    resultado = resultado.merge(
        seguranca_tratada, on="medicamento_id", validate="one_to_one"
    )
    resultado = resultado.merge(pedidos_agregados, on="medicamento_id", how="left")
    resultado["pedidos_confirmados"] = resultado["pedidos_confirmados"].fillna(0.0)
    resultado["compra_recomendada"] = (
        resultado["demanda_prevista"]
        + resultado["estoque_seguranca"]
        - resultado["estoque_disponivel"]
        - resultado["pedidos_confirmados"]
    ).clip(lower=0.0)
    # A Issue #16 refina estes sinais usando prazo de entrega e validade dos lotes.
    resultado["risco_falta"] = resultado.apply(_classificar_risco_falta, axis=1)
    resultado["risco_vencimento"] = "baixo"
    resultado["justificativa"] = resultado.apply(_gerar_justificativa, axis=1)

    return resultado[COLUNAS_SAIDA].sort_values("medicamento_id").reset_index(drop=True)


def _validar_colunas(df: pd.DataFrame, obrigatorias: set[str], nome: str) -> None:
    faltantes = obrigatorias.difference(df.columns)
    if faltantes:
        raise ValueError(
            f"{nome.capitalize()} sem colunas obrigatórias: {sorted(faltantes)}."
        )


def _validar_identificadores(df: pd.DataFrame, nome: str) -> None:
    if df["medicamento_id"].isna().any():
        raise ValueError(f"{nome.capitalize()} contém medicamento_id ausente.")


def _validar_unicidade(df: pd.DataFrame, nome: str) -> None:
    if df["medicamento_id"].duplicated().any():
        raise ValueError(f"{nome.capitalize()} deve ter uma linha por medicamento.")


def _converter_nao_negativo(df: pd.DataFrame, coluna: str) -> None:
    df[coluna] = pd.to_numeric(df[coluna], errors="raise")
    if df[coluna].isna().any() or (df[coluna] < 0).any():
        raise ValueError(f"{coluna} não pode conter valores ausentes ou negativos.")


def _validar_cobertura(medicamentos: set[str], df: pd.DataFrame, nome: str) -> None:
    faltantes = medicamentos.difference(df["medicamento_id"])
    if faltantes:
        raise ValueError(
            f"{nome.capitalize()} ausente para: {', '.join(sorted(faltantes))}."
        )


def _classificar_risco_falta(linha: pd.Series) -> str:
    cobertura = linha["estoque_disponivel"] + linha["pedidos_confirmados"]
    if cobertura < linha["demanda_prevista"]:
        return "alto"
    if cobertura < linha["demanda_prevista"] + linha["estoque_seguranca"]:
        return "médio"
    return "baixo"


def _gerar_justificativa(linha: pd.Series) -> str:
    componentes = (
        f"demanda prevista {_formatar(linha['demanda_prevista'])}, "
        f"estoque de segurança {_formatar(linha['estoque_seguranca'])}, "
        f"estoque disponível {_formatar(linha['estoque_disponivel'])} e "
        f"pedidos confirmados {_formatar(linha['pedidos_confirmados'])}"
    )
    if linha["compra_recomendada"] > 0:
        return (
            f"Comprar {_formatar(linha['compra_recomendada'])} unidades: {componentes}."
        )
    return f"Não é necessário comprar: {componentes}."


def _formatar(valor: float) -> str:
    return f"{float(valor):g}"
