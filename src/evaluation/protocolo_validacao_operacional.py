"""Protocolo reproduzível de validação operacional da Issue #77.

Este módulo não treina modelos nem altera políticas de estoque. Ele fixa as
janelas comuns, reconcilia métricas preditivas e operacionais já calculadas
pelos módulos canônicos e produz uma decisão auditável.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.metricas_preditivas import calcular_metricas

MINIMO_JANELAS = 4
FRACAO_MINIMA_JANELAS_COM_META = 0.75
REDUCAO_MINIMA_CUSTO = 0.10
AUMENTO_RELEVANTE_MAXIMO = 0.05
TOLERANCIA_EMPATE = 1e-9
RESSALVA_FINANCEIRA = (
    "Os custos apresentados são estimativas produzidas com dados sintéticos e "
    "preços unitários de referência. Eles não representam economia financeira "
    "comprovada em uma operação hospitalar real."
)

COLUNAS_JANELAS = [
    "janela_id",
    "inicio_treino",
    "fim_treino",
    "inicio_avaliacao",
    "fim_avaliacao",
]
COLUNAS_METRICAS = {
    "janela_id",
    "candidato",
    "mae",
    "mape",
    "vies_previsao",
    "subestimacao",
    "superestimacao",
    "custo_compras_emergenciais_reais",
    "episodios_ruptura",
    "unidades_em_ruptura",
    "unidades_vencidas",
    "quantidade_total_recomendada",
}
COLUNAS_OPERACIONAIS = [
    "custo_compras_emergenciais_reais",
    "episodios_ruptura",
    "unidades_em_ruptura",
    "unidades_vencidas",
    "quantidade_total_recomendada",
]
STATUS_VALIDOS = {"aprovado", "rejeitado", "dados_insuficientes"}


@dataclass(frozen=True)
class ConfiguracaoProtocolo:
    """Limites versionáveis usados na decisão operacional."""

    versao: str = "1.0.0"
    horizonte_dias: int = 7
    treino_minimo_dias: int = 365
    minimo_janelas: int = MINIMO_JANELAS
    fracao_minima_janelas_com_meta: float = FRACAO_MINIMA_JANELAS_COM_META
    reducao_minima_custo: float = REDUCAO_MINIMA_CUSTO
    aumento_relevante_maximo: float = AUMENTO_RELEVANTE_MAXIMO
    tolerancia_empate: float = TOLERANCIA_EMPATE

    def __post_init__(self) -> None:
        _validar_nome(self.versao, "versao")
        _validar_inteiro_positivo(self.horizonte_dias, "horizonte_dias")
        _validar_inteiro_positivo(self.treino_minimo_dias, "treino_minimo_dias")
        _validar_minimo_janelas(self.minimo_janelas)
        _validar_parametro_fracao(
            self.fracao_minima_janelas_com_meta,
            "fracao_minima_janelas_com_meta",
        )
        _validar_parametro_fracao(self.reducao_minima_custo, "reducao_minima_custo")
        _validar_parametro_fracao(
            self.aumento_relevante_maximo, "aumento_relevante_maximo"
        )
        _validar_parametro_nao_negativo(self.tolerancia_empate, "tolerancia_empate")


def gerar_janelas_backtest(
    datas: pd.Series | pd.Index | list[Any],
    horizonte_dias: int = 7,
    treino_minimo_dias: int = 365,
    minimo_janelas: int = MINIMO_JANELAS,
    passo_dias: int | None = None,
) -> pd.DataFrame:
    """Gera janelas expansivas, não sobrepostas e independentes da data atual.

    A primeira avaliação começa após ``treino_minimo_dias`` datas diárias
    consecutivas. Cada treino termina na véspera da avaliação. Janelas
    incompletas no fim são descartadas explicitamente.
    """
    _validar_inteiro_positivo(horizonte_dias, "horizonte_dias")
    _validar_inteiro_positivo(treino_minimo_dias, "treino_minimo_dias")
    _validar_minimo_janelas(minimo_janelas)
    passo = horizonte_dias if passo_dias is None else passo_dias
    _validar_inteiro_positivo(passo, "passo_dias")
    if passo < horizonte_dias:
        raise ValueError(
            "passo_dias deve ser maior ou igual ao horizonte para impedir overlap."
        )

    serie = pd.Series(datas, dtype="object")
    if serie.empty:
        raise ValueError("datas não pode estar vazio.")
    if serie.map(
        lambda valor: isinstance(valor, (bool, np.bool_, int, float, np.number))
    ).any():
        raise TypeError("datas deve conter datas, não números ou booleanos.")
    try:
        normalizadas = pd.to_datetime(serie, errors="raise", utc=True).dt.normalize()
    except (TypeError, ValueError) as erro:
        raise ValueError("datas contém valor inválido.") from erro
    if normalizadas.isna().any():
        raise ValueError("datas não pode conter valores ausentes.")
    unicas = pd.DatetimeIndex(normalizadas.unique()).sort_values()
    esperado = pd.date_range(unicas.min(), unicas.max(), freq="D", tz="UTC")
    if not unicas.equals(esperado):
        raise ValueError("datas deve formar uma série diária contínua, sem lacunas.")

    primeira_avaliacao = unicas.min() + pd.Timedelta(days=treino_minimo_dias)
    linhas: list[dict[str, Any]] = []
    inicio_avaliacao = primeira_avaliacao
    while inicio_avaliacao + pd.Timedelta(days=horizonte_dias - 1) <= unicas.max():
        fim_avaliacao = inicio_avaliacao + pd.Timedelta(days=horizonte_dias - 1)
        linhas.append(
            {
                "janela_id": f"janela_{len(linhas) + 1:03d}",
                "inicio_treino": unicas.min().date().isoformat(),
                "fim_treino": (inicio_avaliacao - pd.Timedelta(days=1))
                .date()
                .isoformat(),
                "inicio_avaliacao": inicio_avaliacao.date().isoformat(),
                "fim_avaliacao": fim_avaliacao.date().isoformat(),
            }
        )
        inicio_avaliacao += pd.Timedelta(days=passo)
    if len(linhas) < minimo_janelas:
        raise ValueError(
            f"Dados insuficientes: são necessárias ao menos {minimo_janelas} janelas completas; "
            f"foram geradas {len(linhas)}."
        )
    return pd.DataFrame(linhas, columns=COLUNAS_JANELAS)


def calcular_metricas_janela(
    comparacao_previsoes: pd.DataFrame,
    impacto_operacional: pd.DataFrame,
    janela_id: str,
    candidato: str,
) -> pd.DataFrame:
    """Consolida uma janela reutilizando o cálculo preditivo canônico.

    O MAPE herda de :func:`calcular_metricas` a política de excluir apenas do
    denominador percentual as observações cujo consumo real é zero. MAE, viés
    e métricas operacionais continuam usando todas as observações.
    """
    _validar_nome(janela_id, "janela_id")
    _validar_nome(candidato, "candidato")
    obrigatorias_previsao = {"medicamento_id", "demanda_prevista", "consumo_unidades"}
    _validar_colunas(
        comparacao_previsoes, obrigatorias_previsao, "comparacao_previsoes"
    )
    _validar_colunas(
        impacto_operacional, set(COLUNAS_OPERACIONAIS), "impacto_operacional"
    )
    previsoes = comparacao_previsoes.copy()
    impacto = impacto_operacional.copy()
    _validar_numericas(
        previsoes, ["demanda_prevista", "consumo_unidades"], "comparacao_previsoes"
    )
    _validar_numericas(impacto, COLUNAS_OPERACIONAIS, "impacto_operacional")
    previsoes[["demanda_prevista", "consumo_unidades"]] = previsoes[
        ["demanda_prevista", "consumo_unidades"]
    ].apply(pd.to_numeric, errors="raise")
    impacto[COLUNAS_OPERACIONAIS] = impacto[COLUNAS_OPERACIONAIS].apply(
        pd.to_numeric, errors="raise"
    )
    if previsoes.empty or impacto.empty:
        raise ValueError(
            "A janela não pode ter previsões ou impacto operacional vazios."
        )
    if (
        (previsoes[["demanda_prevista", "consumo_unidades"]].apply(pd.to_numeric) < 0)
        .any()
        .any()
    ):
        raise ValueError(
            "comparacao_previsoes não aceita demanda ou consumo negativos."
        )
    if (impacto[COLUNAS_OPERACIONAIS].apply(pd.to_numeric) < 0).any().any():
        raise ValueError("impacto_operacional não aceita métricas negativas.")

    previsoes["metodo"] = candidato
    metricas_canonicas = calcular_metricas(previsoes)
    agregado = metricas_canonicas[metricas_canonicas["medicamento_id"] == "TODOS"]
    if len(agregado) != 1:
        raise ValueError(
            "Não foi possível reconciliar as métricas preditivas agregadas."
        )
    erro = previsoes["demanda_prevista"] - previsoes["consumo_unidades"]
    linha = {
        "janela_id": janela_id,
        "candidato": candidato,
        "mae": float(agregado.iloc[0]["mae"]),
        "mape": float(agregado.iloc[0]["mape"]),
        "vies_previsao": float(erro.mean()),
        "subestimacao": float((-erro.clip(upper=0)).sum()),
        "superestimacao": float(erro.clip(lower=0).sum()),
    }
    linha.update(
        {coluna: float(impacto[coluna].sum()) for coluna in COLUNAS_OPERACIONAIS}
    )
    resultado = pd.DataFrame([linha])
    _validar_metricas(resultado, "metricas_janela")
    return resultado


def avaliar_candidato_na_janela(
    previsoes: pd.DataFrame,
    consumo_real: pd.DataFrame,
    medicamentos_ref: pd.DataFrame,
    estoque_inicial: pd.DataFrame,
    janela_id: str,
    candidato: str,
    lotes: pd.DataFrame | None = None,
    fator_seguranca: float = 0.2,
) -> pd.DataFrame:
    """Executa o simulador canônico e consolida uma janela de um candidato."""
    from src.evaluation.impacto_simulado import simular_impacto

    impacto = simular_impacto(
        previsoes,
        consumo_real,
        medicamentos_ref,
        estoque_inicial,
        lotes=lotes,
        fator_seguranca=fator_seguranca,
    )
    comparacao = previsoes[
        ["medicamento_id", "data_previsao", "demanda_prevista"]
    ].merge(
        consumo_real[["medicamento_id", "data", "consumo_unidades"]],
        left_on=["medicamento_id", "data_previsao"],
        right_on=["medicamento_id", "data"],
        how="inner",
        validate="one_to_one",
    )
    if len(comparacao) != len(previsoes) or len(comparacao) != len(consumo_real):
        raise ValueError(
            "Previsões e consumo real devem cobrir exatamente o mesmo recorte temporal."
        )
    return calcular_metricas_janela(comparacao, impacto, janela_id, candidato)


def avaliar_aprovacao(
    metricas_baseline: pd.DataFrame,
    metricas_candidato: pd.DataFrame,
    reducao_minima_custo: float = REDUCAO_MINIMA_CUSTO,
    fracao_minima_janelas_com_meta: float = FRACAO_MINIMA_JANELAS_COM_META,
    aumento_relevante_maximo: float = AUMENTO_RELEVANTE_MAXIMO,
    minimo_janelas: int = MINIMO_JANELAS,
    tolerancia_empate: float = TOLERANCIA_EMPATE,
) -> dict[str, Any]:
    """Decide aprovação pela comparação estrita das mesmas janelas.

    Consistência significa atingir a redução mínima de custo em pelo menos 75%
    das janelas. Piora relevante significa aumento agregado superior a 5% em
    episódios, unidades em ruptura ou vencimentos. Os limites são parâmetros,
    e os defaults são constantes versionadas deste protocolo.
    """
    candidato = "desconhecido"
    motivos_aprovacao: list[str] = []
    motivos_rejeicao: list[str] = []
    base_resultado = {
        "candidato": candidato,
        "status": "dados_insuficientes",
        "aprovado": False,
        "reducao_custo_emergencial_pct": None,
        "janelas_avaliadas": 0,
        "janelas_com_meta_atingida": 0,
        "variacao_episodios_ruptura_pct": None,
        "variacao_unidades_ruptura_pct": None,
        "variacao_vencimento_pct": None,
        "motivos_aprovacao": motivos_aprovacao,
        "motivos_rejeicao": motivos_rejeicao,
    }
    try:
        candidato = _extrair_candidato(metricas_candidato, "metricas_candidato")
        base_resultado["candidato"] = candidato
        _validar_parametro_fracao(reducao_minima_custo, "reducao_minima_custo")
        _validar_parametro_fracao(
            fracao_minima_janelas_com_meta, "fracao_minima_janelas_com_meta"
        )
        _validar_parametro_fracao(aumento_relevante_maximo, "aumento_relevante_maximo")
        _validar_minimo_janelas(minimo_janelas)
        _validar_parametro_nao_negativo(tolerancia_empate, "tolerancia_empate")
        _validar_metricas(metricas_baseline, "metricas_baseline")
        _validar_metricas(metricas_candidato, "metricas_candidato")
        nome_baseline = _extrair_candidato(metricas_baseline, "metricas_baseline")
        if nome_baseline == candidato:
            raise ValueError(
                "Baseline e candidato devem possuir identificadores diferentes."
            )
        baseline_normalizado = _normalizar_metricas(metricas_baseline)
        candidato_normalizado = _normalizar_metricas(metricas_candidato)
        pares = _parear_janelas(baseline_normalizado, candidato_normalizado)
    except (TypeError, ValueError) as erro:
        motivos_rejeicao.append(str(erro))
        return base_resultado

    base_resultado["janelas_avaliadas"] = len(pares)
    if len(pares) < minimo_janelas:
        motivos_rejeicao.append(
            f"Dados insuficientes: {len(pares)} janelas; mínimo exigido é {minimo_janelas}."
        )
        return base_resultado

    try:
        custo_base = _soma_finita(
            pares["custo_compras_emergenciais_reais_baseline"],
            "custo emergencial baseline",
        )
        custo_candidato = _soma_finita(
            pares["custo_compras_emergenciais_reais_candidato"],
            "custo emergencial candidato",
        )
    except ValueError as erro:
        motivos_rejeicao.append(str(erro))
        return base_resultado
    if custo_base <= tolerancia_empate:
        motivos_rejeicao.append(
            "Baseline possui custo emergencial zero; redução percentual é indefinida."
        )
        return base_resultado

    reducoes_janela = 1 - (
        pares["custo_compras_emergenciais_reais_candidato"]
        / pares["custo_compras_emergenciais_reais_baseline"].replace(0, np.nan)
    )
    janelas_validas_custo = (
        pares["custo_compras_emergenciais_reais_baseline"] > tolerancia_empate
    )
    if not janelas_validas_custo.all():
        motivos_rejeicao.append(
            "Dados insuficientes: há janela com custo baseline zero; a comparação percentual é indefinida."
        )
        return base_resultado

    meta = reducoes_janela >= reducao_minima_custo - tolerancia_empate
    janelas_meta = int((meta & janelas_validas_custo).sum())
    base_resultado["janelas_com_meta_atingida"] = janelas_meta
    reducao_agregada = 1 - custo_candidato / custo_base
    base_resultado["reducao_custo_emergencial_pct"] = reducao_agregada * 100

    mapeamento = {
        "episodios_ruptura": "variacao_episodios_ruptura_pct",
        "unidades_em_ruptura": "variacao_unidades_ruptura_pct",
        "unidades_vencidas": "variacao_vencimento_pct",
    }
    pioras: list[str] = []
    try:
        for metrica, campo_saida in mapeamento.items():
            variacao = _variacao_agregada(pares, metrica, tolerancia_empate)
            base_resultado[campo_saida] = None if variacao is None else variacao * 100
            if variacao is None:
                candidato_total = _soma_finita(
                    pares[f"{metrica}_candidato"], f"{metrica} candidato"
                )
                if candidato_total > tolerancia_empate:
                    pioras.append(f"{metrica}: baseline zero e candidato acima de zero")
            elif variacao > aumento_relevante_maximo + tolerancia_empate:
                pioras.append(f"{metrica}: aumento de {variacao * 100:.2f}%")
    except ValueError as erro:
        motivos_rejeicao.append(str(erro))
        return base_resultado

    fracao_meta = janelas_meta / len(pares)
    if reducao_agregada < reducao_minima_custo - tolerancia_empate:
        motivos_rejeicao.append(
            f"Redução agregada de custo {reducao_agregada * 100:.2f}% abaixo da meta de "
            f"{reducao_minima_custo * 100:.2f}%."
        )
    else:
        motivos_aprovacao.append(
            "Meta agregada de redução do custo emergencial atingida."
        )
    if fracao_meta < fracao_minima_janelas_com_meta - tolerancia_empate:
        motivos_rejeicao.append(
            f"Consistência insuficiente: meta atingida em {janelas_meta}/{len(pares)} janelas."
        )
    else:
        motivos_aprovacao.append("Meta atingida na fração mínima exigida de janelas.")
    if pioras:
        motivos_rejeicao.extend(
            f"Piora operacional relevante em {motivo}." for motivo in pioras
        )
    else:
        motivos_aprovacao.append(
            "Sem piora operacional relevante nas métricas de bloqueio."
        )

    aprovado = not motivos_rejeicao
    base_resultado["aprovado"] = aprovado
    base_resultado["status"] = "aprovado" if aprovado else "rejeitado"
    assert base_resultado["status"] in STATUS_VALIDOS
    return base_resultado


def gerar_relatorio_validacao(
    metadados: Mapping[str, Any],
    configuracao: ConfiguracaoProtocolo,
    janelas: pd.DataFrame,
    metricas: pd.DataFrame,
    decisao: Mapping[str, Any],
) -> str:
    """Gera relatório Markdown inteiramente derivado das entradas."""
    if not isinstance(metadados, Mapping):
        raise TypeError("metadados deve ser um mapeamento.")
    if not isinstance(decisao, Mapping):
        raise TypeError("decisao deve ser um mapeamento.")
    _validar_colunas(janelas, set(COLUNAS_JANELAS), "janelas")
    _validar_metricas(metricas, "metricas")
    if decisao.get("status") not in STATUS_VALIDOS:
        raise ValueError("decisao.status inválido.")
    janelas_ordenadas, metricas_ordenadas = _validar_coerencia_relatorio(
        configuracao, janelas, metricas, decisao
    )
    linhas = [
        "# Relatório de validação operacional",
        "",
        f"> **Transparência financeira:** {RESSALVA_FINANCEIRA}",
        "",
        "## Metadados da execução",
        "",
    ]
    linhas.extend(
        f"- **{chave}:** `{valor}`" for chave, valor in sorted(metadados.items())
    )
    linhas += ["", "## Configuração do protocolo", "", "```json"]
    linhas.append(
        json.dumps(asdict(configuracao), ensure_ascii=False, sort_keys=True, indent=2)
    )
    linhas += [
        "```",
        "",
        "## Janelas",
        "",
        _dataframe_markdown(janelas_ordenadas[COLUNAS_JANELAS]),
    ]
    linhas += [
        "",
        "## Métricas por janela e candidato",
        "",
        _dataframe_markdown(metricas_ordenadas),
    ]
    operacionais = COLUNAS_OPERACIONAIS
    consolidado_operacional = metricas_ordenadas.groupby("candidato", as_index=False)[
        operacionais
    ].sum()
    consolidado_preditivo = metricas_ordenadas.groupby("candidato", as_index=False)[
        ["mae", "mape", "vies_previsao", "subestimacao", "superestimacao"]
    ].mean()
    consolidado = consolidado_preditivo.merge(
        consolidado_operacional, on="candidato", validate="one_to_one"
    )
    linhas += ["", "## Consolidação final", "", _dataframe_markdown(consolidado)]
    linhas += ["", "## Decisão final", "", "```json"]
    linhas.append(
        json.dumps(dict(decisao), ensure_ascii=False, sort_keys=True, indent=2)
    )
    linhas += [
        "```",
        "",
        "## Limitações",
        "",
        "- Resultados operacionais dependem das hipóteses do simulador e não substituem piloto real.",
        "- Os dados do MVP são sintéticos; preços são referências para comparação relativa.",
        "- A Issue #76 ainda não está integrada; este relatório não oferece diagnóstico por medicamento e mês.",
    ]
    return "\n".join(linhas) + "\n"


def salvar_relatorio_validacao(
    diretorio: str | Path,
    metadados: Mapping[str, Any],
    configuracao: ConfiguracaoProtocolo,
    janelas: pd.DataFrame,
    metricas: pd.DataFrame,
    decisao: Mapping[str, Any],
) -> dict[str, Path]:
    """Salva CSV, JSON e Markdown suficientes para reproduzir a decisão."""
    destino = Path(diretorio)
    destino.mkdir(parents=True, exist_ok=True)
    janelas_ordenadas, metricas_ordenadas = _validar_coerencia_relatorio(
        configuracao, janelas, metricas, decisao
    )
    caminhos = {
        "janelas": destino / "janelas.csv",
        "metricas": destino / "metricas.csv",
        "configuracao": destino / "configuracao.json",
        "decisao": destino / "decisao.json",
        "relatorio": destino / "RELATORIO_VALIDACAO_OPERACIONAL.md",
    }
    janelas_ordenadas.to_csv(caminhos["janelas"], index=False)
    metricas_ordenadas.to_csv(caminhos["metricas"], index=False)
    caminhos["configuracao"].write_text(
        json.dumps(asdict(configuracao), ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    caminhos["decisao"].write_text(
        json.dumps(dict(decisao), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    caminhos["relatorio"].write_text(
        gerar_relatorio_validacao(
            metadados, configuracao, janelas_ordenadas, metricas_ordenadas, decisao
        ),
        encoding="utf-8",
    )
    return caminhos


def _parear_janelas(baseline: pd.DataFrame, candidato: pd.DataFrame) -> pd.DataFrame:
    if (
        baseline["janela_id"].duplicated().any()
        or candidato["janela_id"].duplicated().any()
    ):
        raise ValueError("Cada candidato deve possuir uma linha por janela_id.")
    ids_base = set(baseline["janela_id"])
    ids_candidato = set(candidato["janela_id"])
    if ids_base != ids_candidato:
        raise ValueError(
            "Baseline e candidato devem conter exatamente as mesmas janelas."
        )
    base = (
        baseline.drop(columns="candidato")
        .add_suffix("_baseline")
        .rename(columns={"janela_id_baseline": "janela_id"})
    )
    cand = (
        candidato.drop(columns="candidato")
        .add_suffix("_candidato")
        .rename(columns={"janela_id_candidato": "janela_id"})
    )
    return base.merge(cand, on="janela_id", validate="one_to_one").sort_values(
        "janela_id"
    )


def _validar_coerencia_relatorio(
    configuracao: ConfiguracaoProtocolo,
    janelas: pd.DataFrame,
    metricas: pd.DataFrame,
    decisao: Mapping[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not isinstance(configuracao, ConfiguracaoProtocolo):
        raise TypeError("configuracao deve ser ConfiguracaoProtocolo.")
    if not isinstance(decisao, Mapping):
        raise TypeError("decisao deve ser um mapeamento.")
    _validar_colunas(janelas, set(COLUNAS_JANELAS), "janelas")
    if janelas.empty:
        raise ValueError("janelas não pode estar vazio.")
    janelas_ordenadas = janelas[COLUNAS_JANELAS].copy()
    if (
        not janelas_ordenadas["janela_id"]
        .map(lambda valor: isinstance(valor, str) and bool(valor.strip()))
        .all()
    ):
        raise ValueError("janelas.janela_id deve conter apenas textos não vazios.")
    janelas_ordenadas = janelas_ordenadas.sort_values("janela_id").reset_index(
        drop=True
    )
    if janelas_ordenadas["janela_id"].duplicated().any():
        raise ValueError("janelas contém janela_id duplicado.")
    _validar_temporalidade_janelas(janelas_ordenadas, configuracao)
    ids_janelas = set(janelas_ordenadas["janela_id"])
    metricas_ordenadas = (
        metricas.copy().sort_values(["janela_id", "candidato"]).reset_index(drop=True)
    )
    if set(metricas_ordenadas["janela_id"]) != ids_janelas:
        raise ValueError(
            "Métricas e tabela de janelas devem conter exatamente os mesmos janela_id."
        )
    candidatos = set(metricas_ordenadas["candidato"])
    candidato_decisao = decisao.get("candidato")
    if not isinstance(candidato_decisao, str) or not candidato_decisao.strip():
        raise ValueError("decisao.candidato deve ser um texto não vazio.")
    if "baseline" not in candidatos or candidato_decisao not in candidatos:
        raise ValueError(
            "Relatório deve conter baseline e o candidato informado na decisão."
        )
    if candidatos != {"baseline", candidato_decisao}:
        raise ValueError(
            "Relatório de uma decisão deve conter apenas baseline e seu candidato."
        )
    recalculada = avaliar_aprovacao(
        metricas_ordenadas[metricas_ordenadas["candidato"] == "baseline"],
        metricas_ordenadas[metricas_ordenadas["candidato"] == candidato_decisao],
        reducao_minima_custo=configuracao.reducao_minima_custo,
        fracao_minima_janelas_com_meta=configuracao.fracao_minima_janelas_com_meta,
        aumento_relevante_maximo=configuracao.aumento_relevante_maximo,
        minimo_janelas=configuracao.minimo_janelas,
        tolerancia_empate=configuracao.tolerancia_empate,
    )
    if dict(decisao) != recalculada:
        raise ValueError("decisao não é reconciliável com métricas e configuração.")
    return janelas_ordenadas, metricas_ordenadas


def _validar_temporalidade_janelas(
    janelas: pd.DataFrame, configuracao: ConfiguracaoProtocolo
) -> None:
    datas = {}
    for coluna in ("inicio_treino", "fim_treino", "inicio_avaliacao", "fim_avaliacao"):
        if (
            janelas[coluna]
            .map(
                lambda valor: isinstance(valor, (bool, np.bool_, int, float, np.number))
            )
            .any()
        ):
            raise TypeError(f"janelas.{coluna} deve conter datas, não números.")
        try:
            datas[coluna] = pd.to_datetime(
                janelas[coluna], errors="raise", utc=True
            ).dt.normalize()
        except (TypeError, ValueError) as erro:
            raise ValueError(f"janelas.{coluna} contém data inválida.") from erro
        if datas[coluna].isna().any():
            raise ValueError(f"janelas.{coluna} contém data ausente.")
    if not (datas["fim_treino"] < datas["inicio_avaliacao"]).all():
        raise ValueError(
            "janelas contém vazamento: treino deve terminar antes da avaliação."
        )
    if not (datas["inicio_treino"] <= datas["fim_treino"]).all():
        raise ValueError("janelas contém período de treino invertido.")
    if not datas["inicio_treino"].eq(datas["inicio_treino"].iloc[0]).all():
        raise ValueError("janelas expansivas devem compartilhar o início do treino.")
    if (
        not datas["fim_treino"]
        .eq(datas["inicio_avaliacao"] - pd.Timedelta(days=1))
        .all()
    ):
        raise ValueError("treino deve terminar na véspera da janela de avaliação.")
    duracao = (datas["fim_avaliacao"] - datas["inicio_avaliacao"]).dt.days + 1
    if not duracao.eq(configuracao.horizonte_dias).all():
        raise ValueError("janelas não respeita horizonte_dias da configuração.")
    ordem = pd.DataFrame(
        {"inicio": datas["inicio_avaliacao"], "fim": datas["fim_avaliacao"]}
    ).sort_values("inicio")
    if (
        ordem["inicio"].iloc[1:].reset_index(drop=True)
        <= ordem["fim"].iloc[:-1].reset_index(drop=True)
    ).any():
        raise ValueError("janelas de avaliação não podem se sobrepor.")


def _variacao_agregada(
    pares: pd.DataFrame, metrica: str, tolerancia: float
) -> float | None:
    base = _soma_finita(pares[f"{metrica}_baseline"], f"{metrica} baseline")
    candidato = _soma_finita(pares[f"{metrica}_candidato"], f"{metrica} candidato")
    return None if base <= tolerancia else candidato / base - 1


def _soma_finita(serie: pd.Series, nome: str) -> float:
    with np.errstate(over="ignore", invalid="ignore"):
        total = float(serie.to_numpy(dtype=float).sum())
    if not math.isfinite(total):
        raise ValueError(f"{nome} produziu valor não finito após agregação.")
    return total


def _extrair_candidato(df: pd.DataFrame, nome: str) -> str:
    if not isinstance(df, pd.DataFrame) or "candidato" not in df.columns or df.empty:
        return "desconhecido"
    valores = df["candidato"].dropna().unique()
    if len(valores) != 1 or not isinstance(valores[0], str) or not valores[0].strip():
        raise ValueError(f"{nome}.candidato deve identificar exatamente um método.")
    return valores[0]


def _validar_metricas(df: pd.DataFrame, nome: str) -> None:
    _validar_colunas(df, COLUNAS_METRICAS, nome)
    if df.empty:
        raise ValueError(f"{nome} não pode estar vazio.")
    for coluna in ("janela_id", "candidato"):
        if (
            not df[coluna]
            .map(lambda valor: isinstance(valor, str) and bool(valor.strip()))
            .all()
        ):
            raise ValueError(f"{nome}.{coluna} deve conter apenas textos não vazios.")
    _validar_numericas(df, sorted(COLUNAS_METRICAS - {"janela_id", "candidato"}), nome)
    nao_negativas = list(
        set(COLUNAS_OPERACIONAIS) | {"mae", "mape", "subestimacao", "superestimacao"}
    )
    valores_nao_negativos = df[nao_negativas].apply(pd.to_numeric, errors="raise")
    if (valores_nao_negativos < 0).any().any():
        raise ValueError(f"{nome} contém métrica que deveria ser não negativa.")


def _normalizar_metricas(df: pd.DataFrame) -> pd.DataFrame:
    resultado = df.copy()
    numericas = sorted(COLUNAS_METRICAS - {"janela_id", "candidato"})
    resultado[numericas] = resultado[numericas].apply(pd.to_numeric, errors="raise")
    return resultado


def _validar_numericas(df: pd.DataFrame, colunas: list[str], nome: str) -> None:
    for coluna in colunas:
        if df[coluna].map(lambda valor: isinstance(valor, (bool, np.bool_))).any():
            raise TypeError(f"{nome}.{coluna} não aceita booleanos.")
        try:
            valores = pd.to_numeric(df[coluna], errors="raise").to_numpy(dtype=float)
        except (TypeError, ValueError) as erro:
            raise ValueError(f"{nome}.{coluna} deve ser numérica.") from erro
        if not np.isfinite(valores).all():
            raise ValueError(f"{nome}.{coluna} deve conter apenas valores finitos.")


def _validar_colunas(df: pd.DataFrame, obrigatorias: set[str], nome: str) -> None:
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{nome} deve ser um pandas.DataFrame.")
    faltantes = obrigatorias.difference(df.columns)
    if faltantes:
        raise ValueError(f"{nome} sem colunas obrigatórias: {sorted(faltantes)}.")


def _validar_nome(valor: str, nome: str) -> None:
    if not isinstance(valor, str) or not valor.strip():
        raise ValueError(f"{nome} deve ser texto não vazio.")


def _validar_inteiro_positivo(valor: int, nome: str) -> None:
    if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
        raise ValueError(f"{nome} deve ser inteiro positivo.")


def _validar_minimo_janelas(valor: int) -> None:
    _validar_inteiro_positivo(valor, "minimo_janelas")
    if valor < 2:
        raise ValueError(
            "minimo_janelas deve exigir múltiplas janelas (valor mínimo: 2)."
        )


def _validar_parametro_fracao(valor: float, nome: str) -> None:
    _validar_parametro_nao_negativo(valor, nome)
    if valor > 1:
        raise ValueError(f"{nome} deve estar entre 0 e 1.")


def _validar_parametro_nao_negativo(valor: float, nome: str) -> None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise TypeError(f"{nome} deve ser numérico.")
    if not math.isfinite(float(valor)) or valor < 0:
        raise ValueError(f"{nome} deve ser finito e não negativo.")


def _dataframe_markdown(df: pd.DataFrame) -> str:
    colunas = list(df.columns)
    cabecalho = "| " + " | ".join(colunas) + " |"
    separador = "|" + "|".join("---" for _ in colunas) + "|"
    linhas = [cabecalho, separador]
    for valores in df.itertuples(index=False, name=None):
        celulas = [
            str(valor).replace("|", "\\|").replace("\n", " ") for valor in valores
        ]
        linhas.append("| " + " | ".join(celulas) + " |")
    return "\n".join(linhas)
