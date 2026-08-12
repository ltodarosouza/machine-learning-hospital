"""Dashboard demonstrativo do Machine Learning Hospital.

Este wireframe usa dados mockados para validar a experiência do gestor antes da
integração com o motor de recomendação (Issue #20).
"""

from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_MOCK = BASE_DIR / "data" / "mock_recomendacoes.csv"
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
            "justificativa": "Justificativa",
        }
    )
    st.dataframe(
        tabela[
            [
                "Medicamento",
                "Categoria",
                "Alerta",
                "Compra recomendada (un.)",
                "Justificativa",
            ]
        ],
        hide_index=True,
        width="stretch",
    )


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

    pagina = st.sidebar.radio("Navegação", ("Visão geral", "Detalhe por medicamento"))
    if pagina == "Visão geral":
        mostrar_visao_geral(dados)
    else:
        mostrar_detalhe(dados)


if __name__ == "__main__":
    main()
