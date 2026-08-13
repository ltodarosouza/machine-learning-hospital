"""Avalia políticas de reposição por perfil × prazo (Issue #79).

Mantém a previsão fixa e compara apenas a regra de estoque. As políticas são
aplicadas por grupo reutilizável, nunca configuradas manualmente por produto.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.relatorio_final import _limites_dos_ultimos_meses
from src.data_ingestion.gerar_dataset_sintetico import gerar_lotes_no_corte
from src.evaluation.comparar_modelos import (
    DADOS_MODELAGEM,
    N_ESTIMATORS_PADRAO,
    avaliar_baseline_periodo,
    avaliar_modelo_periodo,
)
from src.evaluation.impacto_simulado import simular_impacto
from src.evaluation.protocolo_janela_longa import (
    _previsao_metodo,
    configuracao_janela_longa,
    gerar_janelas_longas,
)
from src.evaluation.protocolo_validacao_operacional import (
    ConfiguracaoProtocolo,
    avaliar_aprovacao,
    calcular_metricas_janela,
)
from src.recommendation.politica_estoque import (
    POLITICAS_CANDIDATAS,
    POLITICA_ATUAL,
    PoliticaEstoque,
)
from src.utils.config import PERIODO_FIM


RAIZ = Path(__file__).resolve().parents[2]
DADOS_ESTOQUE = RAIZ / "data" / "processed" / "consumo_diario.csv"
DADOS_REFERENCIA = RAIZ / "data" / "processed" / "medicamentos_ref.csv"
SAIDA_RELATORIO = RAIZ / "docs" / "avaliacao" / "RESULTADOS_POLITICA_ESTOQUE.md"
METRICAS_IMPACTO = [
    "custo_compras_emergenciais_reais",
    "episodios_ruptura",
    "unidades_em_ruptura",
    "unidades_vencidas",
    "quantidade_total_recomendada",
    "estoque_medio_unidades",
]


def _fatores(politica: PoliticaEstoque, referencia: pd.DataFrame) -> dict[str, float]:
    tabela = politica.fatores_por_medicamento(referencia)
    return tabela.set_index("medicamento_id")["fator_seguranca"].to_dict()


def _estoque_e_lotes_no_corte(estoque: pd.DataFrame, inicio: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    corte = pd.Timestamp(inicio) - pd.Timedelta(days=1)
    inicial = estoque[estoque["data"] <= corte].sort_values("data").groupby("medicamento_id").tail(1)
    return inicial, gerar_lotes_no_corte(estoque, corte)


def simular_politicas_no_periodo(
    dados: pd.DataFrame, estoque: pd.DataFrame, referencia: pd.DataFrame, inicio: str, fim: str
) -> pd.DataFrame:
    """Simula baseline e ML sob a política atual e todas as candidatas."""
    previsoes = {
        "baseline": avaliar_baseline_periodo(dados, inicio, fim),
        "modelo_atual": avaliar_modelo_periodo(dados, inicio, fim, n_estimators=N_ESTIMATORS_PADRAO),
    }
    inicial, lotes = _estoque_e_lotes_no_corte(estoque, inicio)
    partes = []
    for metodo, previsao in previsoes.items():
        for politica in (POLITICA_ATUAL, *POLITICAS_CANDIDATAS):
            impacto = simular_impacto(
                previsao,
                dados,
                referencia,
                inicial,
                lotes,
                fator_seguranca=_fatores(politica, referencia),
            )
            impacto.insert(0, "politica", politica.nome)
            impacto.insert(0, "metodo", metodo)
            partes.append(impacto)
    return pd.concat(partes, ignore_index=True)


def coletar_metricas_protocolo(
    dados: pd.DataFrame, estoque: pd.DataFrame, referencia: pd.DataFrame, configuracao: ConfiguracaoProtocolo
) -> pd.DataFrame:
    """Valida políticas na janela longa v1.1.0, sem resetar estoque dentro dela.

    A previsão continua sendo refeito a cada sete dias pela rotina compartilhada
    da Issue #84. O que muda entre as políticas é exclusivamente o buffer de
    segurança; cada cenário parte do mesmo estoque e dos mesmos lotes no início
    de cada janela de 28 dias.
    """
    linhas = []
    for janela in gerar_janelas_longas(dados, configuracao).itertuples(index=False):
        inicial, lotes = _estoque_e_lotes_no_corte(estoque, janela.inicio_avaliacao)
        previsoes = {
            "baseline": _previsao_metodo(
                dados, janela.inicio_avaliacao, janela.fim_avaliacao, "baseline", None, N_ESTIMATORS_PADRAO
            ),
            "modelo_atual": _previsao_metodo(
                dados, janela.inicio_avaliacao, janela.fim_avaliacao, "modelo_atual", None, N_ESTIMATORS_PADRAO
            ),
        }
        for metodo, previsao in previsoes.items():
            for politica in (POLITICA_ATUAL, *POLITICAS_CANDIDATAS):
                impacto = simular_impacto(
                    previsao[["medicamento_id", "data_previsao", "demanda_prevista"]],
                    previsao[["medicamento_id", "data_previsao", "consumo_unidades"]].rename(
                        columns={"data_previsao": "data"}
                    ),
                    referencia,
                    inicial,
                    lotes=lotes,
                    fator_seguranca=_fatores(politica, referencia),
                )
                resultado = calcular_metricas_janela(
                    previsao[["medicamento_id", "demanda_prevista", "consumo_unidades"]],
                    impacto,
                    janela.janela_id,
                    f"{metodo}:{politica.nome}",
                )
                resultado.insert(1, "metodo", metodo)
                resultado.insert(2, "politica", politica.nome)
                linhas.append(resultado)
    return pd.concat(linhas, ignore_index=True)


def calcular_decisoes(metricas: pd.DataFrame, configuracao: ConfiguracaoProtocolo) -> dict[str, dict[str, dict]]:
    """Compara cada política candidata com a fixa para baseline e modelo atual."""
    decisoes: dict[str, dict[str, dict]] = {}
    for metodo in ("baseline", "modelo_atual"):
        base = metricas[(metricas["metodo"] == metodo) & (metricas["politica"] == POLITICA_ATUAL.nome)].copy()
        base["candidato"] = "politica_atual"
        decisoes[metodo] = {}
        for politica in POLITICAS_CANDIDATAS:
            candidato = metricas[(metricas["metodo"] == metodo) & (metricas["politica"] == politica.nome)].copy()
            candidato["candidato"] = politica.nome
            decisoes[metodo][politica.nome] = avaliar_aprovacao(
                base,
                candidato,
                reducao_minima_custo=configuracao.reducao_minima_custo,
                fracao_minima_janelas_com_meta=configuracao.fracao_minima_janelas_com_meta,
                aumento_relevante_maximo=configuracao.aumento_relevante_maximo,
                minimo_janelas=configuracao.minimo_janelas,
                tolerancia_empate=configuracao.tolerancia_empate,
            )
    return decisoes


def consolidar_resultados_continuos(resultados_mensais: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Soma os meses e calcula variação contra a política fixa do mesmo método."""
    consolidado = pd.concat(resultados_mensais.values(), ignore_index=True).groupby(
        ["metodo", "politica"], as_index=False
    )[METRICAS_IMPACTO].sum()
    partes = []
    for metodo, grupo in consolidado.groupby("metodo", sort=True):
        atual = grupo.loc[grupo["politica"] == POLITICA_ATUAL.nome].iloc[0]
        parte = grupo.copy()
        for metrica in METRICAS_IMPACTO:
            parte[f"variacao_{metrica}_pct"] = (
                (parte[metrica] - atual[metrica]) / atual[metrica] * 100
                if atual[metrica] != 0 else pd.NA
            )
        partes.append(parte)
    return pd.concat(partes, ignore_index=True)


def gerar_relatorio_markdown(
    referencia: pd.DataFrame, metricas_semanais: pd.DataFrame, resultados_mensais: dict[str, pd.DataFrame], decisoes: dict[str, dict[str, dict]]
) -> str:
    linhas = [
        "# Avaliação de política de estoque por perfil e prazo (Issue #79)",
        "",
        "> **Transparência financeira:** custos são estimativas com dados sintéticos e preços de referência; não representam economia comprovada de um hospital.",
        "",
        "A previsão é mantida idêntica em cada comparação. Só muda o buffer de estoque, aplicado por perfil de demanda e faixa de prazo — nunca por configuração manual de medicamento.",
        "",
        "## Grupos e políticas avaliadas",
        "",
        "| Política | Medicamento | Perfil | Prazo | Buffer |",
        "|---|---|---|---|---:|",
    ]
    for politica in (POLITICA_ATUAL, *POLITICAS_CANDIDATAS):
        for _, item in politica.fatores_por_medicamento(referencia).sort_values("medicamento_id").iterrows():
            linhas.append(f"| {politica.nome} | {item['medicamento_id']} | {item['perfil_demanda']} | {item['faixa_prazo']} | {item['fator_seguranca']:.2f} |")

    linhas += ["", "## Decisão formal no protocolo v1.1.0 (janela longa)", "", "A decisão abaixo usa as quatro janelas temporais de 28 dias da Issue #84. O modelo é retreinado a cada 7 dias, mas estoque e lotes não são reiniciados dentro da janela; assim o prazo de entrega de 5–12 dias pode afetar a operação avaliada. Cada política é comparada à `fixa_020` com a mesma previsão."]
    for metodo, por_politica in decisoes.items():
        linhas += ["", f"### Previsão: {metodo}", "", "| Política | Status | Redução de custo | Janelas na meta | Motivo principal |", "|---|---|---:|---:|---|"]
        for nome, decisao in por_politica.items():
            motivo = "; ".join(decisao["motivos_rejeicao"] or decisao["motivos_aprovacao"])
            reducao = decisao["reducao_custo_emergencial_pct"]
            linhas.append(f"| {nome} | {decisao['status']} | {'—' if reducao is None else f'{reducao:.1f}%'} | {decisao['janelas_com_meta_atingida']}/{decisao['janelas_avaliadas']} | {motivo} |")

    linhas += ["", "## Simulação contínua mensal (evidência complementar)", "", "Dentro de cada mês o estoque não é reiniciado semanalmente, então pedidos têm tempo de chegar. `estoque_medio_unidades` explicita o trade-off de capital/estoque excedente; não foi convertido em reais porque o MVP não possui custo real de armazenagem.", "", "| Mês | Previsão | Política | Custo emergencial (R$) | Episódios | Unidades em ruptura | Vencidas | Recomendada | Estoque médio |", "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for mes, resultado in resultados_mensais.items():
        for (metodo, politica), grupo in resultado.groupby(["metodo", "politica"], sort=True):
            total = grupo[METRICAS_IMPACTO].sum()
            linhas.append(f"| {mes} | {metodo} | {politica} | {total['custo_compras_emergenciais_reais']:.2f} | {total['episodios_ruptura']:.0f} | {total['unidades_em_ruptura']:.2f} | {total['unidades_vencidas']:.2f} | {total['quantidade_total_recomendada']:.2f} | {total['estoque_medio_unidades']:.2f} |")
    linhas += ["", "## Consolidado contínuo e trade-offs", "", "Variação contra `fixa_020` do mesmo método; negativo em custo/ruptura é melhora e positivo em estoque médio é o capital adicional mantido no cenário.", "", "| Previsão | Política | Custo (R$) | Δ custo | Episódios | Δ episódios | Unidades ruptura | Δ ruptura | Vencidas | Estoque médio | Δ estoque médio |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _, item in consolidar_resultados_continuos(resultados_mensais).sort_values(["metodo", "politica"]).iterrows():
        linhas.append(f"| {item['metodo']} | {item['politica']} | {item['custo_compras_emergenciais_reais']:.2f} | {item['variacao_custo_compras_emergenciais_reais_pct']:+.1f}% | {item['episodios_ruptura']:.0f} | {item['variacao_episodios_ruptura_pct']:+.1f}% | {item['unidades_em_ruptura']:.2f} | {item['variacao_unidades_em_ruptura_pct']:+.1f}% | {item['unidades_vencidas']:.2f} | {item['estoque_medio_unidades']:.2f} | {item['variacao_estoque_medio_unidades_pct']:+.1f}% |")
    linhas += ["", "## Limitações e próximo passo", "", "A aprovação valida somente o cenário simulado, não uma operação hospitalar real. Antes de adotar uma política aprovada, o time deve decidir o limite aceitável de estoque médio e validar o comportamento em piloto; nenhuma política é aplicada ao dashboard ou ao motor de recomendação nesta issue."]
    return "\n".join(linhas) + "\n"


def main() -> None:
    dados = pd.read_csv(DADOS_MODELAGEM)
    estoque = pd.read_csv(DADOS_ESTOQUE)
    estoque["data"] = pd.to_datetime(estoque["data"])
    referencia = pd.read_csv(DADOS_REFERENCIA)
    configuracao = configuracao_janela_longa()
    metricas = coletar_metricas_protocolo(dados, estoque, referencia, configuracao)
    limites = _limites_dos_ultimos_meses(PERIODO_FIM)
    mensais = {mes: simular_politicas_no_periodo(dados, estoque, referencia, inicio, fim) for mes, (inicio, fim) in limites.items()}
    SAIDA_RELATORIO.write_text(
        gerar_relatorio_markdown(referencia, metricas, mensais, calcular_decisoes(metricas, configuracao)),
        encoding="utf-8",
    )
    print(f"Relatório salvo em: {SAIDA_RELATORIO}")


if __name__ == "__main__":
    main()
