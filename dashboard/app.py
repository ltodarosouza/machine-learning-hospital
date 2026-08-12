"""Dashboard demonstrativo do Machine Learning Hospital.

Este wireframe usa dados mockados para validar a experiência do gestor antes da
integração com o motor de recomendação (Issue #20).
"""

from pathlib import Path
import sys

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
RAIZ_PROJETO = BASE_DIR.parent
sys.path.append(str(RAIZ_PROJETO))
ARQUIVO_MOCK = BASE_DIR / "data" / "mock_recomendacoes.csv"
ARQUIVO_CONSUMO = RAIZ_PROJETO / "data" / "processed" / "consumo_medicamentos.csv"
COLUNAS_OBRIGATORIAS = {
    "medicamento_id",
    "nome",
    "categoria",
    "compra_recomendada",
    "risco_falta",
    "risco_vencimento",
    "justificativa",
}
RISCO_CONFIG = {
    "alto": ("🔴", "Alto"),
    "médio": ("🟡", "Médio"),
    "medio": ("🟡", "Médio"),
    "baixo": ("🟢", "Baixo"),
}


@st.cache_data
def carregar_dados(caminho: Path = ARQUIVO_MOCK) -> pd.DataFrame:
    """Carrega recomendações para o painel.

    A função é o único ponto de acesso aos dados. Na Issue #20, a leitura do
    CSV mockado deve ser substituída pela chamada ao motor de recomendação,
    preservando o DataFrame no contrato da seção 4 de CONTRATOS.md.
    """
    dados = pd.read_csv(caminho)
    faltantes = COLUNAS_OBRIGATORIAS.difference(dados.columns)
    if faltantes:
        nomes = ", ".join(sorted(faltantes))
        raise ValueError(f"O dataset do dashboard não contém: {nomes}.")

    for coluna in ("risco_falta", "risco_vencimento"):
        dados[coluna] = dados[coluna].fillna("baixo").astype(str).str.lower()

    dados["compra_recomendada"] = pd.to_numeric(
        dados["compra_recomendada"], errors="coerce"
    ).fillna(0)
    return dados


def rotulo_risco(risco: str) -> str:
    """Retorna o indicador visual padronizado para um nível de risco."""
    icone, rotulo = RISCO_CONFIG.get(str(risco).lower(), ("⚪", "Não informado"))
    return f"{icone} {rotulo}"


def risco_principal(linha: pd.Series) -> str:
    """Escolhe o maior risco para ordenar os alertas da visão geral."""
    prioridade = {"alto": 3, "médio": 2, "medio": 2, "baixo": 1}
    riscos = [linha["risco_falta"], linha["risco_vencimento"]]
    return max(riscos, key=lambda risco: prioridade.get(risco, 0))


def mostrar_visao_geral(dados: pd.DataFrame) -> None:
    st.title("Visão geral do estoque")
    st.caption("Recomendações simuladas para validar o fluxo do painel.")

    alertas_altos = dados.apply(risco_principal, axis=1).eq("alto").sum()
    recomendacoes = dados.loc[dados["compra_recomendada"] > 0, "compra_recomendada"].sum()
    primeira, segunda, terceira = st.columns(3)
    primeira.metric("Medicamentos monitorados", len(dados))
    segunda.metric("Alertas críticos", alertas_altos)
    terceira.metric("Unidades sugeridas para compra", f"{recomendacoes:,.0f}")

    st.subheader("Alertas e recomendações")
    tabela = dados.copy()
    tabela["risco"] = tabela.apply(lambda linha: rotulo_risco(risco_principal(linha)), axis=1)
    tabela["compra_recomendada"] = tabela["compra_recomendada"].map(lambda valor: f"{valor:,.0f}")
    tabela = tabela.rename(
        columns={
            "nome": "Medicamento",
            "categoria": "Categoria",
            "risco": "Alerta",
            "compra_recomendada": "Compra recomendada (un.)",
        }
    )
    st.dataframe(
        tabela[
            [
                "Medicamento",
                "Categoria",
                "Alerta",
                "Compra recomendada (un.)",
            ]
        ],
        hide_index=True,
        width="stretch",
    )

    st.subheader("Justificativas das recomendações")
    st.caption("Abra um medicamento para ler a justificativa completa, sem alterar a tabela resumida.")
    for _, medicamento in dados.iterrows():
        titulo = (
            f"{rotulo_risco(risco_principal(medicamento))} "
            f"{medicamento['nome']} · {medicamento['compra_recomendada']:,.0f} un."
        )
        with st.expander(titulo):
            st.write(medicamento["justificativa"])


def mostrar_detalhe(dados: pd.DataFrame) -> None:
    st.title("Detalhe por medicamento")
    opcoes = dados["medicamento_id"].tolist()
    selecionado = st.selectbox(
        "Selecione um medicamento",
        opcoes,
        format_func=lambda identificador: dados.loc[
            dados["medicamento_id"].eq(identificador), "nome"
        ].iloc[0],
    )


@st.cache_data(show_spinner="Calculando previsões históricas do modelo...")
def carregar_dados_previsao(caminho: Path = ARQUIVO_CONSUMO) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Gera uma janela de validação temporal para o gráfico do dashboard.

    A janela contém os últimos sete dias conhecidos do dataset. O modelo e o
    baseline são calculados somente com dados anteriores a ela e comparados
    com o consumo efetivamente registrado. É, portanto, uma demonstração de
    acurácia histórica, não uma previsão de um futuro ainda desconhecido.
    """
    from src.evaluation.comparar_modelos import avaliar_baseline_periodo, calcular_metricas
    from src.models.modelo_demanda import avaliar_validacao_temporal
    from src.utils.config import HORIZONTE_PREVISAO_DIAS

    dados = pd.read_csv(caminho)
    dados["data"] = pd.to_datetime(dados["data"])
    fim = dados["data"].max()
    inicio = fim - pd.Timedelta(days=HORIZONTE_PREVISAO_DIAS - 1)
    corte = inicio - pd.Timedelta(days=1)

    baseline = avaliar_baseline_periodo(dados, inicio.date().isoformat(), fim.date().isoformat())
    modelo = avaliar_validacao_temporal(dados, data_corte=corte, n_estimators=100)
    modelo["metodo"] = "modelo_ml"

    comparacao = pd.concat([baseline, modelo], ignore_index=True)
    metricas = calcular_metricas(comparacao)
    metricas = metricas[metricas["medicamento_id"] != "TODOS"].copy()

    realizado = modelo[["medicamento_id", "data_previsao", "consumo_unidades"]].copy()
    realizado = realizado.rename(columns={"consumo_unidades": "unidades"})
    realizado["serie"] = "Consumo real"
    previsto = comparacao.rename(columns={"demanda_prevista": "unidades", "metodo": "serie"})[
        ["medicamento_id", "data_previsao", "unidades", "serie"]
    ]
    previsto["serie"] = previsto["serie"].replace(
        {"baseline": "Baseline", "modelo_ml": "Modelo ML"}
    )
    grafico = pd.concat(
        [realizado[["medicamento_id", "data_previsao", "unidades", "serie"]], previsto],
        ignore_index=True,
    )
    grafico["data_previsao"] = pd.to_datetime(grafico["data_previsao"])
    return grafico, metricas


def mostrar_previsao_demanda() -> None:
    """Exibe consumo realizado e previsões no mesmo período de validação."""
    st.title("Previsão de demanda vs. consumo real")
    st.caption(
        "Janela histórica de validação de 7 dias: os dois métodos só usam dados "
        "anteriores ao período exibido."
    )

    try:
        grafico, metricas = carregar_dados_previsao()
    except (OSError, ValueError) as erro:
        st.error(f"Não foi possível calcular a previsão histórica: {erro}")
        return

    opcoes = sorted(grafico["medicamento_id"].unique())
    medicamento = st.selectbox("Selecione um medicamento", opcoes, key="previsao_medicamento")
    dados_medicamento = grafico[grafico["medicamento_id"] == medicamento]
    metricas_medicamento = metricas[metricas["medicamento_id"] == medicamento].set_index("metodo")

    primeira, segunda = st.columns(2)
    primeira.metric("MAE do modelo", f"{metricas_medicamento.loc['modelo_ml', 'mae']:.2f} un./dia")
    segunda.metric("MAPE do modelo", f"{metricas_medicamento.loc['modelo_ml', 'mape']:.1f}%")

    dados_para_grafico = dados_medicamento.rename(
        columns={"data_previsao": "Data", "unidades": "Unidades", "serie": "Série"}
    )
    st.line_chart(dados_para_grafico, x="Data", y="Unidades", color="Série", width="stretch")

    mae_baseline = metricas_medicamento.loc["baseline", "mae"]
    mae_modelo = metricas_medicamento.loc["modelo_ml", "mae"]
    if mae_modelo < mae_baseline:
        diferenca = (1 - mae_modelo / mae_baseline) * 100 if mae_baseline else 0
        st.success(f"Nesta janela, o modelo reduziu o MAE em {diferenca:.1f}% frente ao baseline.")
    else:
        st.info("Nesta janela, o baseline teve MAE menor. O dashboard mostra os dois métodos para comparação transparente.")

    st.caption(
        "MAE: erro absoluto médio em unidades/dia. MAPE: erro percentual médio. "
        "A avaliação consolidada em quatro janelas está documentada na Issue #13."
    )
    medicamento = dados.loc[dados["medicamento_id"].eq(selecionado)].iloc[0]

    st.subheader(f"{medicamento['nome']} · {medicamento['categoria']}")
    primeira, segunda, terceira = st.columns(3)
    primeira.metric("Compra recomendada", f"{medicamento['compra_recomendada']:,.0f} un.")
    segunda.metric("Risco de falta", rotulo_risco(medicamento["risco_falta"]))
    terceira.metric("Risco de vencimento", rotulo_risco(medicamento["risco_vencimento"]))

    st.info(medicamento["justificativa"], icon="💡")
    st.caption(
        "Os valores desta tela são simulados. A integração com dados reais será feita na Issue #20."
    )


def main() -> None:
    st.set_page_config(page_title="ML Hospital", page_icon="🏥", layout="wide")
    st.sidebar.title("🏥 ML Hospital")
    st.sidebar.caption("Gestão preditiva de medicamentos")

    try:
        dados = carregar_dados()
    except (OSError, ValueError) as erro:
        st.error(f"Não foi possível carregar os dados do painel: {erro}")
        st.stop()

    pagina = st.sidebar.radio(
        "Navegação", ("Visão geral", "Detalhe por medicamento", "Previsão de demanda")
    )
    if pagina == "Visão geral":
        mostrar_visao_geral(dados)
    elif pagina == "Detalhe por medicamento":
        mostrar_detalhe(dados)
    else:
        mostrar_previsao_demanda()


if __name__ == "__main__":
    main()
