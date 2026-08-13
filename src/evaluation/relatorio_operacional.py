"""Relatório operacional por medicamento, mês e tipo de erro (Issue #76).

O relatório de precisão (Issue #13) e o de impacto simulado (Issue #17) só
mostram totais agregados — suficiente para saber *que* o modelo de ML piora
ruptura/custo em algum lugar, mas não *onde*. Este módulo decompõe os dois
relatórios até medicamento × mês, sobre exatamente o mesmo corte temporal,
para permitir diagnosticar quais itens e períodos respondem pela diferença.

Pré-requisito: Issue #75 — sem relatório reproduzível, duas rodadas de
diagnóstico não seriam comparáveis entre si.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_ingestion.gerar_dataset_sintetico import gerar_lotes_no_corte
from src.evaluation.comparar_modelos import avaliar_baseline_periodo, avaliar_modelo_periodo
from src.evaluation.impacto_simulado import simular_impacto

REPO = Path(__file__).resolve().parents[2]
SAIDA_RELATORIO = REPO / "docs" / "arquitetura" / "RESULTADOS_OPERACIONAL_POR_MEDICAMENTO.md"

COLUNAS_METRICAS_IMPACTO = [
    "episodios_ruptura",
    "unidades_em_ruptura",
    "compras_emergenciais_unidades",
    "custo_compras_emergenciais_reais",
    "unidades_vencidas",
]


def calcular_metricas_previsao(comparacao: pd.DataFrame) -> pd.DataFrame:
    """MAE, MAPE, viés e decomposição sub/superestimação, por método e medicamento.

    ``vies`` é o erro médio com sinal (previsto - real): negativo indica
    subestimação sistemática (o tipo de erro que causa ruptura), positivo
    indica superestimação sistemática (o tipo que causa compra/vencimento em
    excesso). ``unidades_subestimadas`` e ``unidades_superestimadas`` somam
    apenas os dias em que o erro foi, respectivamente, para baixo e para
    cima — juntas elas decompõem o erro absoluto total na direção de onde
    ele veio, o que o MAE agregado sozinho não distingue.
    """
    dados = comparacao.copy()
    dados["erro"] = dados["demanda_prevista"] - dados["consumo_unidades"]
    dados["erro_absoluto"] = dados["erro"].abs()
    dados["subestimado"] = (-dados["erro"]).clip(lower=0)
    dados["superestimado"] = dados["erro"].clip(lower=0)

    com_consumo_positivo = dados[dados["consumo_unidades"] > 0].copy()
    com_consumo_positivo["erro_percentual"] = (
        com_consumo_positivo["erro_absoluto"] / com_consumo_positivo["consumo_unidades"]
    ) * 100

    resultado = (
        dados.groupby(["metodo", "medicamento_id"])
        .agg(
            mae=("erro_absoluto", "mean"),
            vies=("erro", "mean"),
            unidades_subestimadas=("subestimado", "sum"),
            unidades_superestimadas=("superestimado", "sum"),
        )
        .reset_index()
    )
    mape = com_consumo_positivo.groupby(["metodo", "medicamento_id"])["erro_percentual"].mean().rename("mape")
    return resultado.merge(mape, on=["metodo", "medicamento_id"], how="left")


def calcular_metricas_mes(
    dados: pd.DataFrame,
    estoque: pd.DataFrame,
    referencia: pd.DataFrame,
    inicio: str,
    fim: str,
) -> pd.DataFrame:
    """Métricas de previsão e de impacto, por medicamento, para um único mês.

    Previsão e impacto são calculados sobre o mesmo `[inicio, fim]` e o mesmo
    snapshot de lotes no corte — é o que garante que as duas famílias de
    métrica sejam comparáveis linha a linha (critério de aceite da Issue #76).
    """
    comparacao_baseline = avaliar_baseline_periodo(dados, inicio, fim)
    comparacao_modelo = avaliar_modelo_periodo(dados, inicio, fim)
    comparacao = pd.concat(
        [
            comparacao_baseline[["metodo", "medicamento_id", "data_previsao", "demanda_prevista", "consumo_unidades"]],
            comparacao_modelo[["metodo", "medicamento_id", "data_previsao", "demanda_prevista", "consumo_unidades"]],
        ],
        ignore_index=True,
    )
    metricas_previsao = calcular_metricas_previsao(comparacao)

    corte = pd.Timestamp(inicio) - pd.Timedelta(days=1)
    estoque_inicial = estoque[estoque["data"] <= corte].sort_values("data").groupby("medicamento_id").tail(1)
    lotes_no_corte = gerar_lotes_no_corte(estoque, corte)

    impacto_baseline = simular_impacto(comparacao_baseline, dados, referencia, estoque_inicial, lotes_no_corte)
    impacto_baseline["metodo"] = "baseline"
    impacto_modelo = simular_impacto(comparacao_modelo, dados, referencia, estoque_inicial, lotes_no_corte)
    impacto_modelo["metodo"] = "modelo_ml"
    impacto = pd.concat([impacto_baseline, impacto_modelo], ignore_index=True)

    return metricas_previsao.merge(impacto, on=["metodo", "medicamento_id"], how="left")


def gerar_detalhamento(
    dados: pd.DataFrame,
    estoque: pd.DataFrame,
    referencia: pd.DataFrame,
    limites: dict[str, tuple[str, str]],
) -> pd.DataFrame:
    """Métricas de previsão e impacto por medicamento, para cada mês em `limites`.

    `limites` é `{rótulo_do_mês: (data_inicio, data_fim)}` — mesmo formato
    usado por `scripts/relatorio_final.py` para o relatório de impacto
    trimestral, de propósito: os dois relatórios devem decompor os mesmos
    totais (critério de aceite da Issue #76).
    """
    partes = []
    for mes, (inicio, fim) in limites.items():
        parte = calcular_metricas_mes(dados, estoque, referencia, inicio, fim)
        parte.insert(0, "mes", mes)
        partes.append(parte)
    return pd.concat(partes, ignore_index=True)


def consolidar_diferenca_por_medicamento(detalhamento: pd.DataFrame) -> pd.DataFrame:
    """Soma, por medicamento, a diferença ML - baseline nas métricas de impacto.

    Positivo em `diferenca_custo_reais` ou `diferenca_episodios_ruptura`
    significa que o modelo de ML piora aquele medicamento no consolidado
    dos meses avaliados — é a base para o destaque de maiores contribuintes
    exigido pela Issue #76.
    """
    consolidado = (
        detalhamento.groupby(["metodo", "medicamento_id"])[COLUNAS_METRICAS_IMPACTO].sum().reset_index()
    )
    pivot = consolidado.pivot(index="medicamento_id", columns="metodo", values=COLUNAS_METRICAS_IMPACTO)

    diferenca = pd.DataFrame(index=pivot.index)
    diferenca["diferenca_custo_reais"] = (
        pivot[("custo_compras_emergenciais_reais", "modelo_ml")] - pivot[("custo_compras_emergenciais_reais", "baseline")]
    )
    diferenca["diferenca_episodios_ruptura"] = (
        pivot[("episodios_ruptura", "modelo_ml")] - pivot[("episodios_ruptura", "baseline")]
    )
    diferenca["diferenca_unidades_vencidas"] = (
        pivot[("unidades_vencidas", "modelo_ml")] - pivot[("unidades_vencidas", "baseline")]
    )
    return diferenca.reset_index()


def gerar_relatorio_markdown(detalhamento: pd.DataFrame) -> str:
    diferenca = consolidar_diferenca_por_medicamento(detalhamento)

    linhas = [
        "# Relatório operacional por medicamento, mês e tipo de erro (Issue #76)",
        "",
        "Decompõe os totais agregados do relatório de precisão "
        "(`RESULTADOS_MODELAGEM.md`) e do relatório de impacto simulado "
        "(`RESULTADOS_IMPACTO_SIMULADO.md`) até medicamento e mês, sobre o "
        "mesmo corte temporal — para identificar quais itens e períodos "
        "explicam a diferença de custo e de ruptura entre baseline e modelo "
        "de ML, sem esconder os casos em que o ML perde.",
        "",
        "**Comando para regenerar:** `python src/evaluation/relatorio_operacional.py` "
        "(ou `python scripts/relatorio_final.py`, que também regenera este relatório).",
        "",
        "## Detalhamento por medicamento e mês",
        "",
        "| Mês | Medicamento | MAE base/ML | Viés base/ML | Subest. (un) base/ML | Superest. (un) base/ML "
        "| Episódios ruptura base/ML | Custo emergencial (R$) base/ML | Vencidas (un) base/ML |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    pivot = detalhamento.set_index(["mes", "medicamento_id", "metodo"])
    combinacoes = detalhamento[["mes", "medicamento_id"]].drop_duplicates().sort_values(["mes", "medicamento_id"])
    for _, linha in combinacoes.iterrows():
        mes, medicamento = linha["mes"], linha["medicamento_id"]
        base = pivot.loc[(mes, medicamento, "baseline")]
        ml = pivot.loc[(mes, medicamento, "modelo_ml")]
        linhas.append(
            f"| {mes} | {medicamento} "
            f"| {base['mae']:.2f} / {ml['mae']:.2f} "
            f"| {base['vies']:+.2f} / {ml['vies']:+.2f} "
            f"| {base['unidades_subestimadas']:.1f} / {ml['unidades_subestimadas']:.1f} "
            f"| {base['unidades_superestimadas']:.1f} / {ml['unidades_superestimadas']:.1f} "
            f"| {base['episodios_ruptura']:.0f} / {ml['episodios_ruptura']:.0f} "
            f"| {base['custo_compras_emergenciais_reais']:.2f} / {ml['custo_compras_emergenciais_reais']:.2f} "
            f"| {base['unidades_vencidas']:.1f} / {ml['unidades_vencidas']:.1f} |"
        )

    piores = diferenca.sort_values("diferenca_custo_reais", ascending=False).head(5)
    melhores = diferenca.sort_values("diferenca_custo_reais", ascending=True).head(5)

    linhas += [
        "",
        "## Medicamentos que mais pioram no consolidado (ML - baseline, custo emergencial)",
        "",
        "Soma da diferença (modelo de ML menos baseline) nos meses avaliados. "
        "Positivo = o modelo de ML custou mais caro nesse medicamento.",
        "",
        "| Medicamento | Diferença de custo (R$) | Diferença de episódios de ruptura | Diferença de unidades vencidas |",
        "|---|---:|---:|---:|",
    ]
    for _, linha in piores.iterrows():
        linhas.append(
            f"| {linha['medicamento_id']} | {linha['diferenca_custo_reais']:+.2f} "
            f"| {linha['diferenca_episodios_ruptura']:+.0f} | {linha['diferenca_unidades_vencidas']:+.1f} |"
        )

    linhas += [
        "",
        "## Medicamentos que mais melhoram no consolidado (ML - baseline, custo emergencial)",
        "",
        "| Medicamento | Diferença de custo (R$) | Diferença de episódios de ruptura | Diferença de unidades vencidas |",
        "|---|---:|---:|---:|",
    ]
    for _, linha in melhores.iterrows():
        linhas.append(
            f"| {linha['medicamento_id']} | {linha['diferenca_custo_reais']:+.2f} "
            f"| {linha['diferenca_episodios_ruptura']:+.0f} | {linha['diferenca_unidades_vencidas']:+.1f} |"
        )

    linhas += [
        "",
        "## Leitura",
        "",
        "`Subest.` e `Superest.` decompõem o erro absoluto na direção em que ele "
        "ocorreu: subestimação é o tipo de erro que causa ruptura (previu de "
        "menos que o consumo real); superestimação é o tipo que causa compra e "
        "vencimento em excesso (previu de mais). Um MAE parecido entre baseline "
        "e modelo pode esconder uma mudança de direção do erro — por isso as "
        "duas colunas são reportadas separadamente, nunca só o MAE agregado.",
        "",
        "Herda a mesma limitação do relatório de impacto simulado: cenário sobre "
        "dados sintéticos, não evidência de piloto real.",
    ]

    return "\n".join(linhas) + "\n"


def main() -> None:
    from scripts.relatorio_final import _limites_dos_ultimos_meses
    from src.utils.config import PERIODO_FIM

    dados = pd.read_csv(REPO / "data" / "processed" / "consumo_medicamentos.csv")
    estoque = pd.read_csv(REPO / "data" / "processed" / "consumo_diario.csv")
    estoque["data"] = pd.to_datetime(estoque["data"])
    referencia = pd.read_csv(REPO / "data" / "processed" / "medicamentos_ref.csv")

    limites = _limites_dos_ultimos_meses(PERIODO_FIM)
    detalhamento = gerar_detalhamento(dados, estoque, referencia, limites)
    relatorio = gerar_relatorio_markdown(detalhamento)

    SAIDA_RELATORIO.write_text(relatorio, encoding="utf-8")
    print(relatorio)
    print(f"Relatório salvo em: {SAIDA_RELATORIO}")


if __name__ == "__main__":
    main()
