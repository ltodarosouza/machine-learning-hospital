"""Avaliação de candidatos de previsão assimétrica (Issue #78).

O modelo oficial treina para MAE, que penaliza subestimar e superestimar a
demanda igualmente. O diagnóstico da Issue #76 mostrou que isso pode reduzir
o erro médio e ainda piorar ruptura nos poucos picos que mais custam. Este
módulo testa candidatos de regressão quantílica (`quantile_alpha > 0.5`,
`src/models/modelo_demanda_assimetrico.py`) que penalizam mais a
subestimação, nas mesmas janelas oficiais do protocolo da Issue #77
(`gerar_janelas_backtest`) e com a mesma função de aprovação
(`avaliar_aprovacao`) — nenhum critério novo é inventado aqui.

Fora do escopo (Issue #78): a política de estoque/compra não muda —
`simular_impacto` roda com o `fator_seguranca` padrão para isolar o efeito
da previsão, e nenhum candidato é usado para gerar previsão específica por
medicamento.

Cada candidato recebe duas decisões, calculadas com a mesma
`avaliar_aprovacao`:

- **vs. baseline** — vocabulário literal do protocolo (candidato contra a
  média móvel).
- **vs. modelo atual** — a pergunta operacionalmente relevante: o candidato
  substituiria o XGBoost simétrico que está em uso? Mesma função e mesmos
  limiares, só troca qual tabela de métricas faz o papel de referência. Se
  nenhum candidato for aprovado nesta comparação, o modelo atual é mantido
  (critério de aceite da Issue #78).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_ingestion.gerar_dataset_sintetico import gerar_lotes_no_corte
from src.evaluation.comparar_modelos import (
    DADOS_MODELAGEM,
    N_ESTIMATORS_PADRAO,
    _commit_atual,
    _hash_arquivo,
    _versoes_dependencias,
    avaliar_baseline_periodo,
    avaliar_modelo_periodo,
)
from src.evaluation.impacto_simulado import simular_impacto
from src.evaluation.protocolo_validacao_operacional import (
    ConfiguracaoProtocolo,
    avaliar_aprovacao,
    avaliar_candidato_na_janela,
    gerar_janelas_backtest,
)
from src.evaluation.relatorio_operacional import calcular_metricas_previsao
from src.models.modelo_demanda import HIPERPARAMETROS_XGBOOST
from src.models.modelo_demanda_assimetrico import avaliar_validacao_temporal_quantilico
from src.utils.config import HORIZONTE_PREVISAO_DIAS, PERIODO_FIM

RAIZ = Path(__file__).resolve().parents[2]
DADOS_ESTOQUE = RAIZ / "data" / "processed" / "consumo_diario.csv"
DADOS_REFERENCIA = RAIZ / "data" / "processed" / "medicamentos_ref.csv"
DESTINO = RAIZ / "docs" / "avaliacao"
SAIDA_RELATORIO = DESTINO / "RESULTADOS_PREVISAO_ASSIMETRICA.md"
SAIDA_METRICAS_JANELA = DESTINO / "previsao_assimetrica_metricas_janela.csv"
SAIDA_DETALHAMENTO = DESTINO / "previsao_assimetrica_detalhamento_medicamento.csv"
QUANTIDADE_JANELAS_OFICIAL = 4

# Dois candidatos, não um só — para não escolher um único alpha "de sorte"
# depois de olhar o resultado. 0.6 é um desvio moderado da mediana; 0.8 é
# agressivo o bastante para valer a pena testar se ajuda nos picos.
CANDIDATOS_QUANTILICOS: dict[str, float] = {
    "quantile_060": 0.6,
    "quantile_080": 0.8,
}


def gerar_janelas_oficiais(dados: pd.DataFrame, configuracao: ConfiguracaoProtocolo) -> pd.DataFrame:
    """As mesmas quatro janelas mais recentes usadas por `scripts/gerar_validacao_operacional.py`."""
    janelas = (
        gerar_janelas_backtest(
            dados["data"],
            horizonte_dias=configuracao.horizonte_dias,
            treino_minimo_dias=configuracao.treino_minimo_dias,
            minimo_janelas=configuracao.minimo_janelas,
        )
        .tail(QUANTIDADE_JANELAS_OFICIAL)
        .reset_index(drop=True)
    )
    janelas["janela_id"] = [f"janela_{indice + 1:03d}" for indice in range(len(janelas))]
    return janelas


def _previsoes_por_candidato(
    dados: pd.DataFrame, inicio: str, fim: str, corte: pd.Timestamp, horizonte: int
) -> dict[str, pd.DataFrame]:
    """Previsões (já unidas ao consumo real) de baseline, modelo atual e candidatos, na janela."""
    previsoes = {
        "baseline": avaliar_baseline_periodo(dados, inicio, fim, horizonte=horizonte),
        "modelo_atual": avaliar_modelo_periodo(
            dados, inicio, fim, horizonte=horizonte, n_estimators=N_ESTIMATORS_PADRAO
        ),
    }
    for nome, alpha in CANDIDATOS_QUANTILICOS.items():
        comparacao = avaliar_validacao_temporal_quantilico(
            dados,
            data_corte=corte,
            quantile_alpha=alpha,
            horizonte=horizonte,
            n_estimators=N_ESTIMATORS_PADRAO,
        )
        previsoes[nome] = comparacao[
            ["medicamento_id", "data_previsao", "demanda_prevista", "consumo_unidades"]
        ]
    return previsoes


def avaliar_candidato_periodo(
    dados_brutos: pd.DataFrame,
    data_inicio_teste: str,
    data_fim_teste: str,
    quantile_alpha: float,
    horizonte: int = HORIZONTE_PREVISAO_DIAS,
    n_estimators: int = N_ESTIMATORS_PADRAO,
) -> pd.DataFrame:
    """Previsões do candidato quantílico no período inteiro — mesma lógica de `avaliar_modelo_periodo`.

    Concatena várias janelas semanais sucessivas numa série contínua, sem
    resetar nada entre elas. É o que permite testar de verdade o efeito da
    previsão em `simular_periodo_continuo`, abaixo: um pedido feito numa
    semana tem chance de chegar (prazo de entrega de 5-12 dias) e afetar o
    estoque de semanas seguintes, ao contrário da avaliação por janela
    isolada do protocolo oficial (`coletar_resultados`).
    """
    inicio = pd.Timestamp(data_inicio_teste)
    fim = pd.Timestamp(data_fim_teste)
    janelas = []
    corte = inicio - pd.Timedelta(days=1)
    while corte + pd.Timedelta(days=1) <= fim:
        comparacao_janela = avaliar_validacao_temporal_quantilico(
            dados_brutos, data_corte=corte, quantile_alpha=quantile_alpha, horizonte=horizonte, n_estimators=n_estimators
        )
        janelas.append(
            comparacao_janela[["medicamento_id", "data_previsao", "demanda_prevista", "consumo_unidades"]]
        )
        corte += pd.Timedelta(days=horizonte)
    return pd.concat(janelas, ignore_index=True)


def simular_periodo_continuo(
    dados: pd.DataFrame, estoque: pd.DataFrame, referencia: pd.DataFrame, inicio: str, fim: str
) -> pd.DataFrame:
    """Impacto simulado por medicamento, para todos os candidatos, sem resetar estoque dentro do período.

    A avaliação oficial do protocolo #77 (`coletar_resultados`) reconstrói o
    estoque inicial a cada janela de 7 dias — descoberta ao rodar esta
    avaliação: como o prazo de entrega mínimo do MVP é 5 dias, quase nenhum
    pedido chega a tempo de afetar a própria janela em que foi feito, então
    a comparação operacional fica quase insensível à previsão (ver seção
    "Sensibilidade da janela de 7 dias" no relatório). Esta função usa a
    mesma abordagem contínua de `impacto_simulado.simular_periodo` (Issue
    #17) e `relatorio_operacional.calcular_metricas_mes` (Issue #76) — um
    único estoque inicial no começo do período, previsão e simulação
    cobrindo o período inteiro numa passada só — para dar tempo real dos
    pedidos chegarem e realmente testar se a previsão assimétrica muda o
    resultado.
    """
    previsoes: dict[str, pd.DataFrame] = {
        "baseline": avaliar_baseline_periodo(dados, inicio, fim),
        "modelo_atual": avaliar_modelo_periodo(dados, inicio, fim, n_estimators=N_ESTIMATORS_PADRAO),
    }
    for nome, alpha in CANDIDATOS_QUANTILICOS.items():
        previsoes[nome] = avaliar_candidato_periodo(dados, inicio, fim, alpha, n_estimators=N_ESTIMATORS_PADRAO)

    corte = pd.Timestamp(inicio) - pd.Timedelta(days=1)
    estoque_inicial = estoque[estoque["data"] <= corte].sort_values("data").groupby("medicamento_id").tail(1)
    lotes = gerar_lotes_no_corte(estoque, corte)

    resultados = []
    for nome, previsao in previsoes.items():
        impacto = simular_impacto(previsao, dados, referencia, estoque_inicial, lotes)
        impacto.insert(0, "candidato", nome)
        resultados.append(impacto)
    return pd.concat(resultados, ignore_index=True)


def coletar_resultados(
    dados: pd.DataFrame,
    estoque: pd.DataFrame,
    referencia: pd.DataFrame,
    janelas: pd.DataFrame,
    configuracao: ConfiguracaoProtocolo,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Métricas do protocolo (agregadas por janela) e detalhamento por medicamento.

    Previsão e impacto usam o mesmo corte e o mesmo snapshot de lotes por
    janela, para todos os candidatos — condição do critério de aceite da
    Issue #78 ("avaliação reproduzível e sem vazamento temporal").
    """
    metricas_protocolo = []
    detalhamento = []

    for janela in janelas.itertuples(index=False):
        inicio, fim = janela.inicio_avaliacao, janela.fim_avaliacao
        corte = pd.Timestamp(inicio) - pd.Timedelta(days=1)
        estoque_inicial = (
            estoque[estoque["data"] <= corte].sort_values("data").groupby("medicamento_id").tail(1)
        )
        lotes = gerar_lotes_no_corte(estoque, corte)

        previsoes = _previsoes_por_candidato(dados, inicio, fim, corte, configuracao.horizonte_dias)

        comparacao_geral = pd.concat(
            [
                df.assign(metodo=nome)[
                    ["metodo", "medicamento_id", "data_previsao", "demanda_prevista", "consumo_unidades"]
                ]
                for nome, df in previsoes.items()
            ],
            ignore_index=True,
        )
        metricas_previsao_medicamento = calcular_metricas_previsao(comparacao_geral).rename(
            columns={"metodo": "candidato"}
        )
        metricas_previsao_medicamento.insert(0, "janela_id", janela.janela_id)

        impacto_partes = []
        for nome, df in previsoes.items():
            previsoes_candidato = df[["medicamento_id", "data_previsao", "demanda_prevista"]]
            consumo_real = df[["medicamento_id", "data_previsao", "consumo_unidades"]].rename(
                columns={"data_previsao": "data"}
            )
            impacto = simular_impacto(previsoes_candidato, consumo_real, referencia, estoque_inicial, lotes=lotes)
            impacto.insert(0, "candidato", nome)
            impacto_partes.append(impacto)

            metricas_protocolo.append(
                avaliar_candidato_na_janela(
                    previsoes_candidato,
                    consumo_real,
                    referencia,
                    estoque_inicial,
                    janela.janela_id,
                    nome,
                    lotes=lotes,
                )
            )

        impacto_medicamento = pd.concat(impacto_partes, ignore_index=True)
        impacto_medicamento.insert(0, "janela_id", janela.janela_id)

        detalhamento.append(
            metricas_previsao_medicamento.merge(
                impacto_medicamento, on=["janela_id", "candidato", "medicamento_id"], how="left"
            )
        )

    return pd.concat(metricas_protocolo, ignore_index=True), pd.concat(detalhamento, ignore_index=True)


def calcular_decisoes(metricas_protocolo: pd.DataFrame, configuracao: ConfiguracaoProtocolo) -> dict[str, dict[str, Any]]:
    """Para cada candidato quantílico, decisão vs. baseline e vs. modelo atual.

    Ambas usam `avaliar_aprovacao` — mesma função, mesmos limiares. "vs.
    modelo atual" é a que importa operacionalmente: só ela decide se algum
    candidato substituiria o que está em produção hoje.
    """
    limites = dict(
        reducao_minima_custo=configuracao.reducao_minima_custo,
        fracao_minima_janelas_com_meta=configuracao.fracao_minima_janelas_com_meta,
        aumento_relevante_maximo=configuracao.aumento_relevante_maximo,
        minimo_janelas=configuracao.minimo_janelas,
        tolerancia_empate=configuracao.tolerancia_empate,
    )
    metricas_baseline = metricas_protocolo[metricas_protocolo["candidato"] == "baseline"]
    metricas_modelo_atual = metricas_protocolo[metricas_protocolo["candidato"] == "modelo_atual"]

    decisoes: dict[str, dict[str, Any]] = {}
    for nome in CANDIDATOS_QUANTILICOS:
        metricas_candidato = metricas_protocolo[metricas_protocolo["candidato"] == nome]
        decisoes[nome] = {
            "vs_baseline": avaliar_aprovacao(metricas_baseline, metricas_candidato, **limites),
            "vs_modelo_atual": avaliar_aprovacao(metricas_modelo_atual, metricas_candidato, **limites),
        }
    return decisoes


def _tabela_markdown(df: pd.DataFrame, formato: dict[str, str] | None = None) -> str:
    formato = formato or {}
    colunas = list(df.columns)
    linhas = ["| " + " | ".join(colunas) + " |", "|" + "|".join(["---"] * len(colunas)) + "|"]
    for _, linha in df.iterrows():
        celulas = []
        for coluna in colunas:
            valor = linha[coluna]
            if coluna in formato and isinstance(valor, (int, float)):
                celulas.append(format(valor, formato[coluna]))
            else:
                celulas.append(str(valor))
        linhas.append("| " + " | ".join(celulas) + " |")
    return "\n".join(linhas)


def _resumo_decisao(nome: str, decisao: dict[str, Any]) -> list[str]:
    # Texto puro (sem emoji): `print(relatorio)` roda em consoles Windows com
    # codepage cp1252 por padrão, que não codifica emoji e derruba o processo
    # depois do relatório já ter sido salvo em UTF-8 — mensagem de status tem
    # que ser segura em qualquer console, não só no arquivo.
    status = "[aprovado]" if decisao["aprovado"] else f"[{decisao['status']}]"
    reducao = decisao["reducao_custo_emergencial_pct"]
    reducao_texto = "—" if reducao is None else f"{reducao:.1f}%"
    linhas = [
        f"- **{nome}:** {status} — redução de custo emergencial: {reducao_texto}, "
        f"meta atingida em {decisao['janelas_com_meta_atingida']}/{decisao['janelas_avaliadas']} janelas.",
    ]
    for motivo in decisao["motivos_rejeicao"]:
        linhas.append(f"  - rejeição: {motivo}")
    for motivo in decisao["motivos_aprovacao"]:
        linhas.append(f"  - aprovação: {motivo}")
    return linhas


def _secao_sensibilidade(detalhamento: pd.DataFrame) -> list[str]:
    """Quantifica quantos pares (janela, medicamento) o candidato realmente mudou o custo simulado.

    Achado ao rodar esta avaliação pela primeira vez: `custo_compras_emergenciais_reais`
    saiu **idêntico** entre modelo atual e candidatos na maioria dos pares,
    apesar de `demanda_prevista` e `quantidade_total_recomendada` diferirem.
    Causa: o prazo de entrega mínimo do MVP é 5 dias (`medicamentos_ref.csv`)
    contra um horizonte de avaliação de 7 dias — um pedido feito durante a
    janela só chega a tempo de afetar a própria janela em poucos dias no
    fim dela, se chegar. A ruptura de uma janela isolada de 7 dias é
    dominada pelo estoque inicial (histórico real, igual para todo
    candidato), não pela previsão sendo testada. Isso não invalida a
    decisão do protocolo (ela ainda é a regra oficial da Issue #77), mas
    explica por que a comparação operacional aqui tem pouca sensibilidade —
    calculado a cada execução, nunca escrito à mão, para não silenciar essa
    limitação se os dados mudarem.
    """
    referencia = detalhamento[detalhamento["candidato"] == "modelo_atual"][
        ["janela_id", "medicamento_id", "custo_compras_emergenciais_reais"]
    ].rename(columns={"custo_compras_emergenciais_reais": "custo_modelo_atual"})

    linhas = [
        "O prazo de entrega mínimo do MVP (5 dias) é próximo do horizonte de "
        "avaliação (7 dias): um pedido feito durante a janela raramente chega a "
        "tempo de afetar a própria janela, então a ruptura observada é dominada "
        "pelo estoque inicial (idêntico para todo candidato), não pela previsão. "
        "Por isso a comparação de custo abaixo pode ter pouca sensibilidade à "
        "previsão testada — reportado explicitamente, calculado a cada execução.",
        "",
        "| Candidato | Pares (janela, medicamento) com custo diferente do modelo atual | Total de pares |",
        "|---|---:|---:|",
    ]
    for nome in CANDIDATOS_QUANTILICOS:
        candidato_df = detalhamento[detalhamento["candidato"] == nome][
            ["janela_id", "medicamento_id", "custo_compras_emergenciais_reais"]
        ]
        comparado = candidato_df.merge(referencia, on=["janela_id", "medicamento_id"], how="inner")
        diferentes = int(
            ((comparado["custo_compras_emergenciais_reais"] - comparado["custo_modelo_atual"]).abs() > 1e-9).sum()
        )
        linhas.append(f"| {nome} | {diferentes} | {len(comparado)} |")
    return linhas


def _candidatos_promissores_na_simulacao_continua(
    resultados_mensais: dict[str, pd.DataFrame], reducao_minima: float = 0.10
) -> list[str]:
    """Candidatos com redução de custo emergencial >= `reducao_minima` em TODOS os meses simulados.

    Mesmo espírito de consistência do protocolo #77 (Issue #77, seção 7:
    meta atingida numa fração mínima das janelas), aplicado à simulação
    contínua em vez das janelas isoladas — não é uma aprovação formal
    (só `avaliar_aprovacao` decide isso), é um sinal para priorizar qual
    candidato revalidar com o protocolo oficial numa janela mais longa.
    """
    promissores = []
    for nome in CANDIDATOS_QUANTILICOS:
        reducoes = []
        for impacto_mes in resultados_mensais.values():
            modelo_atual = impacto_mes[impacto_mes["candidato"] == "modelo_atual"][
                "custo_compras_emergenciais_reais"
            ].sum()
            candidato = impacto_mes[impacto_mes["candidato"] == nome]["custo_compras_emergenciais_reais"].sum()
            if modelo_atual <= 0:
                reducoes.append(False)
                continue
            reducoes.append((1 - candidato / modelo_atual) >= reducao_minima)
        if reducoes and all(reducoes):
            promissores.append(nome)
    return promissores


def gerar_relatorio_markdown(
    janelas: pd.DataFrame,
    metricas_protocolo: pd.DataFrame,
    detalhamento: pd.DataFrame,
    decisoes: dict[str, dict[str, Any]],
    configuracao: ConfiguracaoProtocolo,
    metadados: dict[str, Any],
    resultados_mensais: dict[str, pd.DataFrame] | None = None,
) -> str:
    algum_aprovado_vs_modelo_atual = any(
        decisao["vs_modelo_atual"]["aprovado"] for decisao in decisoes.values()
    )

    linhas = [
        "# Avaliação de previsão assimétrica (Issue #78)",
        "",
        "> **Transparência financeira:** os custos apresentados são estimativas "
        "produzidas com dados sintéticos e preços unitários de referência. Não "
        "representam economia financeira comprovada em uma operação hospitalar real.",
        "",
        "Testa se penalizar mais a subestimação de demanda (regressão quantílica "
        "do XGBoost, `quantile_alpha > 0.5`) reduz rupturas nos picos, mantendo a "
        "política de estoque/compra inalterada. Usa as mesmas janelas oficiais e a "
        "mesma função de aprovação do protocolo da "
        "[Issue #77](../avaliacao/PROTOCOLO_VALIDACAO_OPERACIONAL.md).",
        "",
        "## Candidatos avaliados",
        "",
    ]
    for nome, alpha in CANDIDATOS_QUANTILICOS.items():
        linhas.append(f"- `{nome}`: `quantile_alpha={alpha}` (XGBoost, `objective=reg:quantileerror`).")

    linhas += ["", "## Janelas (mesmas do protocolo oficial da Issue #77)", "", _tabela_markdown(janelas)]

    linhas += ["", "## Métricas por candidato e janela", "", _tabela_markdown(
        metricas_protocolo.sort_values(["janela_id", "candidato"]).reset_index(drop=True),
        formato={
            "mae": ".2f", "mape": ".1f", "vies_previsao": "+.2f", "subestimacao": ".1f",
            "superestimacao": ".1f", "custo_compras_emergenciais_reais": ".2f",
            "episodios_ruptura": ".0f", "unidades_em_ruptura": ".1f", "unidades_vencidas": ".1f",
            "quantidade_total_recomendada": ".1f",
        },
    )]

    consolidado_operacional = metricas_protocolo.groupby("candidato", as_index=False)[
        ["custo_compras_emergenciais_reais", "episodios_ruptura", "unidades_em_ruptura", "unidades_vencidas"]
    ].sum()
    consolidado_preditivo = metricas_protocolo.groupby("candidato", as_index=False)[
        ["mae", "mape", "vies_previsao"]
    ].mean()
    consolidado = consolidado_preditivo.merge(consolidado_operacional, on="candidato")
    linhas += ["", "## Consolidação (soma dos custos/rupturas, média do MAE/MAPE/viés)", "", _tabela_markdown(
        consolidado,
        formato={
            "mae": ".2f", "mape": ".1f", "vies_previsao": "+.2f",
            "custo_compras_emergenciais_reais": ".2f", "episodios_ruptura": ".0f",
            "unidades_em_ruptura": ".1f", "unidades_vencidas": ".1f",
        },
    )]

    linhas += ["", "## Decisões (protocolo da Issue #77, `avaliar_aprovacao`)", ""]
    linhas.append(
        "`vs_baseline` é o vocabulário literal do protocolo (candidato contra a "
        "média móvel). `vs_modelo_atual` é a pergunta operacional — só ela decide "
        "se o candidato substituiria o XGBoost simétrico em uso hoje."
    )
    for nome, decisao in decisoes.items():
        linhas += ["", f"### {nome}", ""]
        linhas += ["**vs. baseline**"] + _resumo_decisao(nome, decisao["vs_baseline"])
        linhas += ["", "**vs. modelo atual**"] + _resumo_decisao(nome, decisao["vs_modelo_atual"])

    linhas += ["", "## Recomendação", ""]
    if algum_aprovado_vs_modelo_atual:
        aprovados = [nome for nome, decisao in decisoes.items() if decisao["vs_modelo_atual"]["aprovado"]]
        linhas.append(
            f"**{', '.join(aprovados)}** atende(m) ao critério de aprovação da Issue #77 "
            "contra o modelo atual — candidato(s) elegível(is) para substituir o modelo em produção."
        )
    else:
        linhas.append(
            "**Nenhum candidato atingiu o critério de aprovação da Issue #77 contra o "
            "modelo atual. O modelo atual é mantido** (critério de aceite da Issue #78: "
            "sem aprovação, não há adoção). Essa rejeição é honesta em relação ao "
            "protocolo, mas ver a seção **Sensibilidade da janela de 7 dias**, abaixo: "
            "nas janelas oficiais, o custo simulado é quase insensível à previsão "
            "testada, então a rejeição não deve ser lida como \"a previsão assimétrica "
            "não ajuda\" — só como \"não passou neste teste específico\", que tem pouco "
            "poder para detectar diferença nesta configuração."
        )
        if resultados_mensais is not None:
            promissores = _candidatos_promissores_na_simulacao_continua(resultados_mensais)
            if promissores:
                linhas.append(
                    f"\n\nNa **simulação contínua** (seção abaixo, que dá tempo real do pedido "
                    f"chegar), **{', '.join(promissores)}** reduziu o custo de compra emergencial "
                    "em pelo menos 10% em todos os meses simulados frente ao modelo atual — sinal "
                    "forte o bastante para justificar revalidar formalmente com o protocolo #77 "
                    "numa configuração de janela mais longa (ex.: janelas mensais em vez de "
                    "semanais), antes de descartar o candidato só pela rejeição acima."
                )

    linhas += ["", "## Sensibilidade da janela de 7 dias ao pedido", ""]
    linhas.extend(_secao_sensibilidade(detalhamento))

    if resultados_mensais is not None:
        linhas += ["", "## Simulação contínua complementar (estoque não reseta a cada semana)", ""]
        linhas.extend(_secao_simulacao_continua(resultados_mensais))

    if resultados_mensais is not None:
        linhas += [
            "",
            "## Ganhos e perdas por medicamento (simulação contínua, custo de compra emergencial)",
            "",
            "Reportado por completo — inclui os medicamentos onde o candidato perde, não só "
            "onde ganha. Vem da simulação contínua (estoque não reseta a cada semana), não das "
            "janelas oficiais de 7 dias — é a decomposição que tem sinal real, dada a "
            "insensibilidade descrita na seção acima.",
            "",
        ]
        consolidado_continuo = pd.concat(resultados_mensais.values())
        consolidado_medicamento_continuo = (
            consolidado_continuo[consolidado_continuo["candidato"].isin({"modelo_atual", *CANDIDATOS_QUANTILICOS})]
            .groupby(["candidato", "medicamento_id"], as_index=False)["custo_compras_emergenciais_reais"]
            .sum()
        )
        pivot_continuo = consolidado_medicamento_continuo.pivot(
            index="medicamento_id", columns="candidato", values="custo_compras_emergenciais_reais"
        )
        for nome in CANDIDATOS_QUANTILICOS:
            diferenca = (pivot_continuo[nome] - pivot_continuo["modelo_atual"]).sort_values(ascending=False)
            linhas += [f"### {nome} - modelo atual (R$, positivo = candidato mais caro)", ""]
            tabela_diferenca = diferenca.reset_index()
            tabela_diferenca.columns = ["medicamento_id", "diferenca_custo_reais"]
            linhas.append(_tabela_markdown(tabela_diferenca, formato={"diferenca_custo_reais": "+.2f"}))
            linhas.append("")

    linhas += [
        "",
        "## Ganhos e perdas por medicamento (janelas oficiais de 7 dias, custo de compra emergencial)",
        "",
        "Reportado por completo — inclui os medicamentos onde o candidato perde, não só onde "
        "ganha. **Atenção:** vem das janelas isoladas do protocolo #77; a seção "
        "\"Sensibilidade da janela de 7 dias\" mostra que essa comparação tem pouco sinal "
        "aqui — use a decomposição da simulação contínua acima para decidir algo.",
        "",
    ]
    consolidado_medicamento = (
        detalhamento[detalhamento["candidato"].isin({"modelo_atual", *CANDIDATOS_QUANTILICOS})]
        .groupby(["candidato", "medicamento_id"], as_index=False)["custo_compras_emergenciais_reais"]
        .sum()
    )
    pivot_medicamento = consolidado_medicamento.pivot(
        index="medicamento_id", columns="candidato", values="custo_compras_emergenciais_reais"
    )
    for nome in CANDIDATOS_QUANTILICOS:
        diferenca = (pivot_medicamento[nome] - pivot_medicamento["modelo_atual"]).sort_values(ascending=False)
        linhas += [f"### {nome} - modelo atual (R$, positivo = candidato mais caro)", ""]
        tabela_diferenca = diferenca.reset_index()
        tabela_diferenca.columns = ["medicamento_id", "diferenca_custo_reais"]
        linhas.append(_tabela_markdown(tabela_diferenca, formato={"diferenca_custo_reais": "+.2f"}))
        linhas.append("")

    hiperparametros_texto = ", ".join(
        f"{chave}={valor}" for chave, valor in json.loads(metadados["hiperparametros_modelo"]).items()
    )
    linhas += [
        "## Reprodutibilidade",
        "",
        f"- **Protocolo:** versão `{configuracao.versao}` (Issue #77), `avaliar_aprovacao` sem alteração de limiares.",
        f"- **Commit:** `{metadados['commit']}`",
        f"- **Hash do dataset avaliado:** `{metadados['hash_consumo_medicamentos']}`",
        f"- **Ambiente:** `{metadados['versoes']}`",
        f"- **Hiperparâmetros compartilhados (herdados de `modelo_demanda.py::HIPERPARAMETROS_XGBOOST`):** {hiperparametros_texto}",
        f"- **n_estimators:** {metadados['n_estimators']}",
        "- **Comando para regenerar:** `python src/evaluation/avaliacao_previsao_assimetrica.py`",
        "",
        "## Limitações",
        "",
        "- Herda todas as limitações do simulador de impacto (Issue #17): dados "
        "sintéticos, preços de referência, snapshot de lotes reconstruído.",
        "- A política de estoque/compra (`fator_seguranca`) foi mantida idêntica "
        "à do modelo atual de propósito, para isolar o efeito da previsão — "
        "calibrar a política por perfil de medicamento é escopo da Issue #79, "
        "não desta avaliação.",
        "- Quatro janelas detectam inconsistência grosseira, não substituem "
        "validação retrospectiva longa ou piloto hospitalar.",
    ]
    return "\n".join(linhas) + "\n"


def coletar_simulacao_continua_trimestral(
    dados: pd.DataFrame, estoque: pd.DataFrame, referencia: pd.DataFrame, fim_periodo: str = PERIODO_FIM, n_meses: int = 3
) -> dict[str, pd.DataFrame]:
    """Simulação contínua (sem reset semanal) para os últimos `n_meses` meses fechados do dataset.

    Mesmos limites de mês que `scripts/relatorio_final.py::_limites_dos_ultimos_meses`
    usa para o relatório trimestral oficial de impacto (Issue #17) — reaproveita
    a função em vez de duplicar a lógica de "últimos N meses fechados".
    """
    from scripts.relatorio_final import _limites_dos_ultimos_meses

    limites = _limites_dos_ultimos_meses(fim_periodo, n_meses)
    return {
        mes: simular_periodo_continuo(dados, estoque, referencia, inicio, fim)
        for mes, (inicio, fim) in limites.items()
    }


def _secao_simulacao_continua(resultados_mensais: dict[str, pd.DataFrame]) -> list[str]:
    """Compara candidatos ao modelo atual com estoque contínuo (não reseta a cada semana).

    Ao contrário da decisão oficial (janelas isoladas de 7 dias), aqui o
    pedido tem chance real de chegar dentro do período simulado — resposta
    mais direta à pergunta da Issue #78 ("isso economiza de verdade?"), mas
    **não é a decisão formal do protocolo #77** (que exige janelas
    independentes, não sobrepostas, com no mínimo 4 repetições).
    """
    metricas = [
        "episodios_ruptura",
        "unidades_em_ruptura",
        "custo_compras_emergenciais_reais",
        "unidades_vencidas",
    ]
    linhas = [
        "Estoque inicial único no começo de cada mês, sem reset semanal — o "
        "pedido de uma semana pode chegar e afetar semanas seguintes do mesmo "
        "mês (mesma abordagem do relatório de impacto trimestral, Issue #17, e "
        "do relatório por medicamento/mês, Issue #76). **Não substitui a decisão "
        "formal do protocolo #77** — é evidência complementar sobre se a "
        "previsão assimétrica economiza de verdade, quando o pedido tem tempo "
        "de fazer efeito.",
        "",
    ]
    for nome in CANDIDATOS_QUANTILICOS:
        linhas += [f"### {nome} vs. modelo atual", "", "| Mês | Métrica | Modelo atual | Candidato | Redução | Redução (%) |", "|---|---|---:|---:|---:|---:|"]
        for mes, impacto_mes in resultados_mensais.items():
            modelo_atual = impacto_mes[impacto_mes["candidato"] == "modelo_atual"][metricas].sum()
            candidato = impacto_mes[impacto_mes["candidato"] == nome][metricas].sum()
            for metrica in metricas:
                reducao = modelo_atual[metrica] - candidato[metrica]
                reducao_pct = "—" if modelo_atual[metrica] == 0 else f"{(reducao / modelo_atual[metrica]) * 100:.1f}%"
                linhas.append(f"| {mes} | {metrica} | {modelo_atual[metrica]:.2f} | {candidato[metrica]:.2f} | {reducao:.2f} | {reducao_pct} |")
        linhas.append("")

        consolidado = pd.concat(resultados_mensais.values())
        modelo_atual_total = consolidado[consolidado["candidato"] == "modelo_atual"][metricas].sum()
        candidato_total = consolidado[consolidado["candidato"] == nome][metricas].sum()
        linhas += ["**Consolidado (todos os meses):**", "", "| Métrica | Modelo atual | Candidato | Redução | Redução (%) |", "|---|---:|---:|---:|---:|"]
        for metrica in metricas:
            reducao = modelo_atual_total[metrica] - candidato_total[metrica]
            reducao_pct = "—" if modelo_atual_total[metrica] == 0 else f"{(reducao / modelo_atual_total[metrica]) * 100:.1f}%"
            linhas.append(f"| {metrica} | {modelo_atual_total[metrica]:.2f} | {candidato_total[metrica]:.2f} | {reducao:.2f} | {reducao_pct} |")
        linhas.append("")
    return linhas


def main() -> None:
    configuracao = ConfiguracaoProtocolo()
    dados = pd.read_csv(DADOS_MODELAGEM)
    estoque = pd.read_csv(DADOS_ESTOQUE)
    estoque["data"] = pd.to_datetime(estoque["data"])
    referencia = pd.read_csv(DADOS_REFERENCIA)

    janelas = gerar_janelas_oficiais(dados, configuracao)
    metricas_protocolo, detalhamento = coletar_resultados(dados, estoque, referencia, janelas, configuracao)
    decisoes = calcular_decisoes(metricas_protocolo, configuracao)

    print("Rodando simulação contínua complementar (3 meses, sem reset semanal)...")
    resultados_mensais = coletar_simulacao_continua_trimestral(dados, estoque, referencia)

    metadados = {
        "commit": _commit_atual(),
        "hash_consumo_medicamentos": _hash_arquivo(DADOS_MODELAGEM),
        "hash_consumo_diario": _hash_arquivo(DADOS_ESTOQUE),
        "hash_medicamentos_ref": _hash_arquivo(DADOS_REFERENCIA),
        "versoes": json.dumps(_versoes_dependencias(), sort_keys=True),
        "hiperparametros_modelo": json.dumps(HIPERPARAMETROS_XGBOOST, sort_keys=True),
        "n_estimators": N_ESTIMATORS_PADRAO,
    }

    relatorio = gerar_relatorio_markdown(
        janelas, metricas_protocolo, detalhamento, decisoes, configuracao, metadados, resultados_mensais
    )
    DESTINO.mkdir(parents=True, exist_ok=True)
    SAIDA_RELATORIO.write_text(relatorio, encoding="utf-8")
    metricas_protocolo.to_csv(SAIDA_METRICAS_JANELA, index=False)
    detalhamento.to_csv(SAIDA_DETALHAMENTO, index=False)
    pd.concat(
        [df.assign(mes=mes) for mes, df in resultados_mensais.items()], ignore_index=True
    ).to_csv(DESTINO / "previsao_assimetrica_simulacao_continua.csv", index=False)

    # Não faz `print(relatorio)`: o relatório completo já foi salvo em UTF-8
    # acima; alguns consoles Windows usam cp1252 por padrão e derrubam o
    # processo ao tentar imprimir certos caracteres — visto na prática nesta
    # avaliação. Um resumo curto é suficiente no terminal.
    for nome, decisao in decisoes.items():
        print(f"{nome}: vs_baseline={decisao['vs_baseline']['status']}, vs_modelo_atual={decisao['vs_modelo_atual']['status']}")
    print(f"Relatorio salvo em: {SAIDA_RELATORIO}")


if __name__ == "__main__":
    main()
