"""Motor de recomendacao de compras da Issue #15.

A previsao recebida tem uma linha por dia do horizonte. Este modulo soma o
horizonte por medicamento antes de calcular uma unica recomendacao::

    compra_recomendada = (
        demanda_prevista + estoque_seguranca
        - estoque_disponivel - pedidos_confirmados
    )

A data de referencia e o dia anterior ao inicio da previsao. Somente o estoque
mais recente ate essa data pode ser usado. Pedidos sem datas sao aceitos por
compatibilidade com a API original e integralmente descontados. Quando existe
``data_prevista_entrega``, somente entregas dentro do horizonte sao
descontadas; entregas vencidas ou posteriores sao ignoradas.

Valores numericos ausentes, nao finitos, booleanos ou negativos sao rejeitados.
As previsoes definem os medicamentos da saida. Seguranca e estoque sao
obrigatorios para todos eles; pedidos ausentes equivalem a zero.

Os riscos sao heuristicas. Risco de falta compara cobertura de estoque com o
prazo de entrega do fornecedor. Risco de vencimento (corrigido na Issue #53)
compara, lote a lote, a quantidade de cada lote com o consumo esperado
(demanda diaria x dias ate a validade) ate sua propria data de validade --
nao depende do prazo de entrega do fornecedor, que e uma informacao de
compra, nao de consumo. Quando nao ha lotes informados, o risco de
vencimento permanece ``baixo`` por falta de dado, nao por avaliacao real;
essa limitacao consta na justificativa.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

COLUNAS_PREVISOES = {"medicamento_id", "data_previsao", "demanda_prevista"}
COLUNAS_ESTOQUE_SEGURANCA = {"medicamento_id", "estoque_seguranca"}
COLUNAS_ESTOQUE = {"medicamento_id", "data", "estoque_disponivel"}
COLUNAS_PEDIDOS = {"medicamento_id", "quantidade"}
COLUNAS_REFERENCIA = {"medicamento_id", "prazo_entrega_dias"}
COLUNAS_LOTES = {"medicamento_id", "quantidade_atual", "data_validade"}
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
    medicamentos_referencia: pd.DataFrame | None = None,
    lotes: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Gera uma recomendacao de compra por medicamento previsto.

    Os DataFrames recebidos nunca sao modificados. A recomendacao permanece
    fracionaria porque o contrato define ``float`` e nao exige arredondamento.
    A ordem dos argumentos segue o contrato: estoque atual antes do estoque de
    seguranca. Chamadas que desejem evitar dependencia da ordem podem usar os
    nomes dos parametros.
    """
    _validar_dataframe(previsoes, "previsoes")
    _validar_dataframe(estoque_atual, "estoque_atual")
    _validar_dataframe(estoque_seguranca, "estoque_seguranca")
    pedidos_pendentes = (
        pd.DataFrame() if pedidos_pendentes is None else pedidos_pendentes
    )
    medicamentos_referencia = (
        pd.DataFrame() if medicamentos_referencia is None else medicamentos_referencia
    )
    lotes = pd.DataFrame() if lotes is None else lotes

    previsoes = previsoes.copy()
    estoque_atual = estoque_atual.copy()
    if "data_previsao" not in previsoes.columns:
        ordem = previsoes.groupby("medicamento_id", sort=False).cumcount()
        previsoes["data_previsao"] = pd.Timestamp("1970-01-02") + pd.to_timedelta(
            ordem, unit="D"
        )
    if "data" not in estoque_atual.columns:
        estoque_atual["data"] = pd.Timestamp("1970-01-01")

    _validar_colunas(previsoes, COLUNAS_PREVISOES, "previsoes")
    _validar_colunas(estoque_seguranca, COLUNAS_ESTOQUE_SEGURANCA, "estoques_seguranca")
    _validar_colunas(estoque_atual, COLUNAS_ESTOQUE, "estoque_historico")
    _validar_dataframe(pedidos_pendentes, "pedidos_pendentes")
    _validar_dataframe(medicamentos_referencia, "medicamentos_referencia")
    _validar_dataframe(lotes, "lotes")
    if not pedidos_pendentes.empty:
        _validar_colunas(pedidos_pendentes, COLUNAS_PEDIDOS, "pedidos_pendentes")
    if not medicamentos_referencia.empty:
        _validar_colunas(
            medicamentos_referencia, COLUNAS_REFERENCIA, "medicamentos_referencia"
        )
    if not lotes.empty:
        _validar_colunas(lotes, COLUNAS_LOTES, "lotes")
    if previsoes.empty:
        raise ValueError("previsoes nao pode estar vazio.")

    demanda = previsoes[["medicamento_id", "data_previsao", "demanda_prevista"]].copy()
    seguranca = estoque_seguranca[["medicamento_id", "estoque_seguranca"]].copy()
    estoque = estoque_atual[["medicamento_id", "data", "estoque_disponivel"]].copy()
    colunas_pedidos = [
        coluna
        for coluna in (
            "medicamento_id",
            "quantidade",
            "pedido_id",
            "data_pedido",
            "data_prevista_entrega",
        )
        if coluna in pedidos_pendentes.columns
    ]
    pedidos = pedidos_pendentes[colunas_pedidos].copy()
    referencia = (
        medicamentos_referencia[["medicamento_id", "prazo_entrega_dias"]].copy()
        if not medicamentos_referencia.empty
        else pd.DataFrame(columns=["medicamento_id", "prazo_entrega_dias"])
    )
    lotes = (
        lotes[["medicamento_id", "quantidade_atual", "data_validade"]].copy()
        if not lotes.empty
        else pd.DataFrame(
            columns=["medicamento_id", "quantidade_atual", "data_validade"]
        )
    )

    _validar_identificadores(demanda, "previsoes")
    _validar_identificadores(seguranca, "estoques_seguranca")
    _validar_identificadores(estoque, "estoque_historico")
    if not pedidos.empty:
        _validar_identificadores(pedidos, "pedidos_pendentes")
    if not referencia.empty:
        _validar_identificadores(referencia, "medicamentos_referencia")
    if not lotes.empty:
        _validar_identificadores(lotes, "lotes")
    _converter_numerico_nao_negativo(demanda, "demanda_prevista", "previsoes")
    _converter_numerico_nao_negativo(
        seguranca, "estoque_seguranca", "estoques_seguranca"
    )
    _converter_numerico_nao_negativo(estoque, "estoque_disponivel", "estoque_historico")
    if not pedidos.empty:
        _converter_numerico_nao_negativo(pedidos, "quantidade", "pedidos_pendentes")
    if not referencia.empty:
        _converter_numerico_nao_negativo(
            referencia, "prazo_entrega_dias", "medicamentos_referencia"
        )
    if not lotes.empty:
        _converter_numerico_nao_negativo(lotes, "quantidade_atual", "lotes")

    demanda["data_previsao"] = _converter_datas(
        demanda["data_previsao"], "previsoes.data_previsao"
    )
    estoque["data"] = _converter_datas(estoque["data"], "estoque_historico.data")
    inicio_horizonte = demanda["data_previsao"].min()
    fim_horizonte = demanda["data_previsao"].max()
    data_referencia = inicio_horizonte - pd.Timedelta(days=1)
    if not lotes.empty:
        lotes["data_validade"] = _converter_datas(
            lotes["data_validade"], "lotes.data_validade"
        )

    _rejeitar_duplicatas(demanda, ["medicamento_id", "data_previsao"], "previsoes")
    _validar_horizonte_compartilhado(demanda)
    _rejeitar_duplicatas(seguranca, ["medicamento_id"], "estoques_seguranca")
    _rejeitar_duplicatas(estoque, ["medicamento_id", "data"], "estoque_historico")
    if (
        "pedido_id" in pedidos.columns
        and not pedidos.empty
        and (
            pedidos["pedido_id"].isna().any() or pedidos["pedido_id"].duplicated().any()
        )
    ):
        raise ValueError("pedidos_pendentes contem pedido_id ausente ou duplicado.")

    demanda_total = demanda.groupby("medicamento_id", as_index=False)[
        "demanda_prevista"
    ].sum()
    _validar_resultado_finito(demanda_total, "demanda_prevista", "demanda agregada")
    estoque_elegivel = estoque[estoque["data"] <= data_referencia]
    estoque_atual = (
        estoque_elegivel.sort_values(["medicamento_id", "data"])
        .groupby("medicamento_id", as_index=False)
        .tail(1)[["medicamento_id", "estoque_disponivel"]]
    )
    pedidos = _selecionar_pedidos_do_horizonte(
        pedidos, data_referencia, inicio_horizonte, fim_horizonte
    )
    pedidos_total = (
        pedidos.groupby("medicamento_id", as_index=False)["quantidade"]
        .sum()
        .rename(columns={"quantidade": "pedidos_confirmados"})
        if not pedidos.empty
        else pd.DataFrame(columns=["medicamento_id", "pedidos_confirmados"])
    )
    if not pedidos_total.empty:
        _validar_resultado_finito(
            pedidos_total, "pedidos_confirmados", "pedidos agregados"
        )

    resultado = demanda_total.merge(
        seguranca, on="medicamento_id", how="left", validate="one_to_one"
    )
    resultado = resultado.merge(
        estoque_atual, on="medicamento_id", how="left", validate="one_to_one"
    )
    _validar_cobertura(resultado, "estoque_seguranca", "estoques_seguranca")
    _validar_cobertura(
        resultado,
        "estoque_disponivel",
        "Estoque atual ausente; estoque_historico ate a data de referencia",
    )
    resultado = resultado.merge(
        pedidos_total, on="medicamento_id", how="left", validate="one_to_one"
    )
    resultado["pedidos_confirmados"] = resultado["pedidos_confirmados"].fillna(0.0)
    resultado = resultado.merge(referencia, on="medicamento_id", how="left")
    resultado["prazo_entrega_dias"] = resultado["prazo_entrega_dias"].fillna(0.0)
    resultado["demanda_diaria"] = resultado["demanda_prevista"] / len(
        demanda["data_previsao"].unique()
    )
    resultado = resultado.merge(
        _avaliar_lotes(lotes, data_referencia, resultado),
        on="medicamento_id",
        how="left",
    )
    resultado[["quantidade_proxima_validade", "dias_ate_validade"]] = resultado[
        ["quantidade_proxima_validade", "dias_ate_validade"]
    ].fillna(0.0)
    resultado["risco_vencimento"] = resultado["risco_vencimento"].fillna("baixo")

    calculo = (
        resultado["demanda_prevista"]
        + resultado["estoque_seguranca"]
        - resultado["estoque_disponivel"]
        - resultado["pedidos_confirmados"]
    )
    _validar_resultado_finito(
        calculo.to_frame("compra_recomendada"),
        "compra_recomendada",
        "calculo da recomendacao",
    )
    calculo = calculo.mask(np.isclose(calculo, 0.0, rtol=0.0, atol=1e-12), 0.0)
    resultado["compra_recomendada"] = calculo.clip(lower=0.0)
    resultado["risco_falta"] = resultado.apply(_classificar_risco_falta, axis=1)
    resultado["justificativa"] = resultado.apply(_criar_justificativa, axis=1)
    return resultado[COLUNAS_SAIDA].sort_values("medicamento_id").reset_index(drop=True)


def _validar_dataframe(df: pd.DataFrame, nome: str) -> None:
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{nome} deve ser um pandas.DataFrame.")


def _validar_colunas(df: pd.DataFrame, obrigatorias: set[str], nome: str) -> None:
    _validar_dataframe(df, nome)
    faltantes = obrigatorias.difference(df.columns)
    if faltantes:
        raise ValueError(f"{nome} sem colunas obrigatorias: {sorted(faltantes)}.")


def _validar_identificadores(df: pd.DataFrame, nome: str) -> None:
    identificadores = df["medicamento_id"]
    if identificadores.isna().any():
        raise ValueError(f"{nome}.medicamento_id contem valor ausente.")
    if not identificadores.map(lambda valor: isinstance(valor, str)).all():
        raise TypeError(f"{nome}.medicamento_id deve conter apenas strings.")
    if identificadores.str.strip().eq("").any():
        raise ValueError(f"{nome}.medicamento_id contem valor vazio.")
    if identificadores.ne(identificadores.str.strip()).any():
        raise ValueError(
            f"{nome}.medicamento_id nao pode conter espacos nas extremidades."
        )


def _converter_numerico_nao_negativo(df: pd.DataFrame, coluna: str, nome: str) -> None:
    if df[coluna].map(lambda valor: isinstance(valor, (bool, np.bool_))).any():
        raise TypeError(f"{nome}.{coluna} nao aceita valores booleanos.")
    try:
        df[coluna] = pd.to_numeric(df[coluna], errors="raise")
    except (TypeError, ValueError) as erro:
        raise ValueError(f"{nome}.{coluna} deve conter apenas numeros.") from erro
    if (
        df[coluna].isna().any()
        or not np.isfinite(df[coluna].to_numpy(dtype=float)).all()
    ):
        raise ValueError(f"{nome}.{coluna} deve conter apenas valores finitos.")
    if (df[coluna] < 0).any():
        raise ValueError(f"{nome}.{coluna} nao pode conter valores negativos.")


def _converter_datas(serie: pd.Series, nome: str) -> pd.Series:
    if serie.map(lambda valor: isinstance(valor, (bool, np.bool_, int, float))).any():
        raise TypeError(
            f"{nome} deve conter datas, nao valores numericos ou booleanos."
        )
    try:
        datas = pd.to_datetime(serie, errors="raise", utc=True)
    except (TypeError, ValueError) as erro:
        raise ValueError(f"{nome} contem datas invalidas.") from erro
    if datas.isna().any():
        raise ValueError(f"{nome} nao pode conter datas ausentes.")
    return datas.dt.normalize()


def _selecionar_pedidos_do_horizonte(
    pedidos: pd.DataFrame,
    data_referencia: pd.Timestamp,
    inicio_horizonte: pd.Timestamp,
    fim_horizonte: pd.Timestamp,
) -> pd.DataFrame:
    if pedidos.empty:
        return pedidos
    if "data_pedido" in pedidos.columns:
        pedidos["data_pedido"] = _converter_datas(
            pedidos["data_pedido"], "pedidos_pendentes.data_pedido"
        )
    if "data_prevista_entrega" in pedidos.columns:
        pedidos["data_prevista_entrega"] = _converter_datas(
            pedidos["data_prevista_entrega"], "pedidos_pendentes.data_prevista_entrega"
        )
    if (
        "data_pedido" in pedidos.columns
        and "data_prevista_entrega" in pedidos.columns
        and (pedidos["data_pedido"] > pedidos["data_prevista_entrega"]).any()
    ):
        raise ValueError(
            "pedidos_pendentes.data_pedido nao pode ser posterior a data_prevista_entrega."
        )
    if "data_pedido" in pedidos.columns:
        pedidos = pedidos[pedidos["data_pedido"] <= data_referencia]
    if "data_prevista_entrega" not in pedidos.columns:
        return pedidos
    return pedidos[
        pedidos["data_prevista_entrega"].between(
            inicio_horizonte, fim_horizonte, inclusive="both"
        )
    ]


def _validar_horizonte_compartilhado(demanda: pd.DataFrame) -> None:
    horizontes = demanda.groupby("medicamento_id")["data_previsao"].agg(frozenset)
    if horizontes.map(lambda datas: datas != horizontes.iloc[0]).any():
        raise ValueError(
            "previsoes deve usar as mesmas datas de horizonte para todos os medicamentos."
        )


def _validar_resultado_finito(df: pd.DataFrame, coluna: str, contexto: str) -> None:
    if not np.isfinite(df[coluna].to_numpy(dtype=float)).all():
        raise ValueError(f"{contexto}.{coluna} produziu valor nao finito.")


def _rejeitar_duplicatas(df: pd.DataFrame, colunas: list[str], nome: str) -> None:
    if df.duplicated(colunas).any():
        raise ValueError(f"{nome} contem chaves duplicadas em {colunas}.")


def _validar_cobertura(resultado: pd.DataFrame, coluna: str, origem: str) -> None:
    ausentes = resultado.loc[resultado[coluna].isna(), "medicamento_id"].tolist()
    if ausentes:
        raise ValueError(f"{origem} sem dados para medicamentos previstos: {ausentes}.")


RISCO_VENCIMENTO_ORDEM = {"baixo": 0, "médio": 1, "alto": 2}
# razao = quantidade_do_lote / consumo_esperado_ate_a_validade.
# > 1.0  -> nao da tempo de consumir tudo -> alto.
# > 0.7  -> vai ficar apertado, ainda sem estourar -> medio.
# caso contrario -> baixo.
LIMIAR_VENCIMENTO_MEDIO = 0.7


def _avaliar_lotes(
    lotes: pd.DataFrame, data_referencia: pd.Timestamp, resultado: pd.DataFrame
) -> pd.DataFrame:
    """Avalia cada lote contra o consumo esperado até sua validade; retorna o pior caso por medicamento.

    Corrigido na Issue #53: a versão anterior só considerava lotes que
    venciam até o `prazo_entrega_dias` do fornecedor — um lote vencendo em
    15 dias era ignorado se o prazo de entrega fosse 7, mesmo que 15 dias não
    bastassem para consumir a quantidade daquele lote no ritmo normal. Agora
    cada lote é comparado, individualmente, ao que se espera consumir
    (`demanda_diaria × dias até a validade`) até a sua própria data de
    validade — sem depender do prazo de entrega, que é informação de compra,
    não de consumo. Quando um medicamento tem mais de um lote, reportamos o
    pior caso (maior severidade), com a quantidade/prazo do lote responsável.
    """
    colunas_vazias = ["medicamento_id", "quantidade_proxima_validade", "dias_ate_validade", "risco_vencimento"]
    if lotes.empty:
        return pd.DataFrame(columns=colunas_vazias)

    demanda_diaria = resultado.set_index("medicamento_id")["demanda_diaria"]
    copia = lotes.copy()
    copia["dias_ate_validade"] = (
        copia["data_validade"] - data_referencia
    ).dt.days.clip(lower=0)
    copia["demanda_diaria"] = copia["medicamento_id"].map(demanda_diaria).fillna(0)
    consumo_esperado = copia["demanda_diaria"] * copia["dias_ate_validade"]

    razao = np.where(
        consumo_esperado > 0,
        copia["quantidade_atual"] / consumo_esperado,
        np.where(copia["quantidade_atual"] > 0, np.inf, 0.0),
    )
    copia["risco_vencimento"] = np.select(
        [razao > 1.0, razao > LIMIAR_VENCIMENTO_MEDIO],
        ["alto", "médio"],
        default="baixo",
    )
    copia["_ordem_risco"] = copia["risco_vencimento"].map(RISCO_VENCIMENTO_ORDEM)

    pior_lote_por_medicamento = copia.loc[
        copia.groupby("medicamento_id")["_ordem_risco"].idxmax()
    ]
    return pior_lote_por_medicamento.rename(columns={"quantidade_atual": "quantidade_proxima_validade"})[
        ["medicamento_id", "quantidade_proxima_validade", "dias_ate_validade", "risco_vencimento"]
    ]


def _classificar_risco_falta(linha: pd.Series) -> str:
    """Alto: cobertura até o lead time; médio: até 1,5x; baixo: acima disso."""
    demanda_diaria = linha["demanda_diaria"]
    if demanda_diaria <= 0:
        return "baixo"
    cobertura_dias = linha["estoque_disponivel"] / demanda_diaria
    prazo = linha["prazo_entrega_dias"]
    if prazo <= 0:
        return "alto" if linha["compra_recomendada"] > 0 else "baixo"
    if cobertura_dias <= prazo:
        return "alto"
    if cobertura_dias <= prazo * 1.5:
        return "médio"
    return "baixo"


def _formatar_quantidade(valor: float) -> str:
    return f"{valor:g}"


def _criar_justificativa(linha: pd.Series) -> str:
    demanda = _formatar_quantidade(linha["demanda_prevista"])
    seguranca = _formatar_quantidade(linha["estoque_seguranca"])
    disponivel = _formatar_quantidade(linha["estoque_disponivel"])
    pedidos = _formatar_quantidade(linha["pedidos_confirmados"])
    compra = _formatar_quantidade(linha["compra_recomendada"])
    cobertura = (
        linha["estoque_disponivel"] / linha["demanda_diaria"]
        if linha["demanda_diaria"] > 0
        else 0
    )
    texto = (
        f"Comprar {compra} unidades. Demanda prevista para o horizonte: {demanda} unidades; "
        f"estoque de seguranca: {seguranca}; estoque disponivel mais recente: {disponivel}; "
        f"pedidos confirmados: {pedidos}. Risco de falta {linha['risco_falta']}: "
        f"estoque cobre {cobertura:.1f} dias para prazo de entrega de {linha['prazo_entrega_dias']:g} dias. "
    )
    if linha["quantidade_proxima_validade"] > 0:
        texto += (
            f"Risco de vencimento {linha['risco_vencimento']}: "
            f"{linha['quantidade_proxima_validade']:g} unidades vencem em até "
            f"{linha['dias_ate_validade']:g} dias."
        )
    else:
        texto += "Risco de vencimento baixo: nenhum lote tem quantidade acima do consumo esperado até sua validade."
    return texto
