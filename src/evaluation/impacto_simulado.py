"""Simulação de impacto do baseline versus modelo de ML (Issue #17).

Os resultados deste módulo são cenários sobre dados sintéticos, não evidência
de piloto real. A política simulada compra diariamente o necessário para cobrir
o lead time previsto, mais o estoque de segurança. Pedidos regulares chegam
após o prazo do fornecedor; faltas são supridas por compra emergencial no mesmo
dia e contabilizadas separadamente.
"""

from __future__ import annotations

import pandas as pd

from src.evaluation.comparar_modelos import avaliar_baseline_periodo, avaliar_modelo_periodo


COLUNAS_PREVISAO = {"medicamento_id", "data_previsao", "demanda_prevista"}
COLUNAS_REAL = {"medicamento_id", "data", "consumo_unidades"}
COLUNAS_REFERENCIA = {"medicamento_id", "prazo_entrega_dias", "preco_unitario_reais"}
COLUNAS_ESTOQUE = {"medicamento_id", "estoque_disponivel"}


def simular_impacto(
    previsoes: pd.DataFrame,
    consumo_real: pd.DataFrame,
    medicamentos_ref: pd.DataFrame,
    estoque_inicial: pd.DataFrame,
    fator_seguranca: float = 0.2,
) -> pd.DataFrame:
    """Simula rupturas, compras emergenciais e custo por medicamento.

    ``fator_seguranca`` é a fração da demanda prevista durante o lead time
    usada como buffer. Vencimentos requerem movimentação por lote que ainda
    não é produzida pelo pipeline; portanto ``unidades_vencidas`` permanece
    zero e o relatório deixa essa limitação explícita.
    """
    _validar(previsoes, COLUNAS_PREVISAO, "previsoes")
    _validar(consumo_real, COLUNAS_REAL, "consumo_real")
    _validar(medicamentos_ref, COLUNAS_REFERENCIA, "medicamentos_ref")
    _validar(estoque_inicial, COLUNAS_ESTOQUE, "estoque_inicial")
    if fator_seguranca < 0:
        raise ValueError("fator_seguranca deve ser não negativo.")

    previsao = previsoes.copy()
    previsao["data_previsao"] = pd.to_datetime(previsao["data_previsao"])
    previsao["demanda_prevista"] = pd.to_numeric(previsao["demanda_prevista"])
    real = consumo_real.copy()
    real["data"] = pd.to_datetime(real["data"])
    real["consumo_unidades"] = pd.to_numeric(real["consumo_unidades"])
    referencia = medicamentos_ref[list(COLUNAS_REFERENCIA)].copy()
    inicial = estoque_inicial[list(COLUNAS_ESTOQUE)].copy()

    dados = real.merge(previsao, left_on=["medicamento_id", "data"], right_on=["medicamento_id", "data_previsao"], how="inner")
    dados = dados.merge(referencia, on="medicamento_id", how="inner").merge(inicial, on="medicamento_id", how="inner")
    if dados.empty:
        raise ValueError("Não há interseção entre previsões, consumo real e estoque inicial.")

    resultados = []
    for medicamento, serie in dados.groupby("medicamento_id", sort=True):
        serie = serie.sort_values("data")
        prazo = int(serie["prazo_entrega_dias"].iloc[0])
        preco = float(serie["preco_unitario_reais"].iloc[0])
        estoque = float(serie["estoque_disponivel"].iloc[0])
        chegadas: dict[pd.Timestamp, float] = {}
        rupturas = emergenciais = custo_emergencial = 0.0
        episodios = 0
        for _, dia in serie.iterrows():
            data = dia["data"]
            estoque += chegadas.pop(data, 0.0)
            demanda_lead_time = max(float(dia["demanda_prevista"]), 0.0) * max(prazo, 1)
            pedido = max(demanda_lead_time * (1 + fator_seguranca) - estoque - sum(chegadas.values()), 0.0)
            chegada = data + pd.Timedelta(days=prazo)
            chegadas[chegada] = chegadas.get(chegada, 0.0) + pedido
            realizado = max(float(dia["consumo_unidades"]), 0.0)
            falta = max(realizado - estoque, 0.0)
            if falta > 0:
                episodios += 1
                rupturas += falta
                emergenciais += falta
                custo_emergencial += falta * preco
            estoque = max(estoque - realizado, 0.0)
        resultados.append(
            {
                "medicamento_id": medicamento,
                "episodios_ruptura": episodios,
                "unidades_em_ruptura": rupturas,
                "compras_emergenciais_unidades": emergenciais,
                "custo_compras_emergenciais_reais": custo_emergencial,
                "unidades_vencidas": 0.0,
            }
        )
    return pd.DataFrame(resultados)


def comparar_cenarios(impacto_baseline: pd.DataFrame, impacto_modelo: pd.DataFrame) -> pd.DataFrame:
    """Compara os impactos agregados e calcula a economia estimada em reais."""
    metricas = ["episodios_ruptura", "unidades_em_ruptura", "compras_emergenciais_unidades", "custo_compras_emergenciais_reais", "unidades_vencidas"]
    base = impacto_baseline[metricas].sum().rename("baseline")
    modelo = impacto_modelo[metricas].sum().rename("modelo_ml")
    comparacao = pd.concat([base, modelo], axis=1).reset_index(names="metrica")
    comparacao["reducao"] = comparacao["baseline"] - comparacao["modelo_ml"]
    comparacao["reducao_pct"] = comparacao["reducao"].div(comparacao["baseline"].replace(0, pd.NA)) * 100
    return comparacao


def gerar_relatorio_markdown(comparacao: pd.DataFrame, inicio: str, fim: str) -> str:
    """Formata o resultado sem apresentá-lo como evidência de piloto real."""
    linhas = [
        "# Impacto simulado: baseline vs. modelo de ML (Issue #17)",
        "",
        f"Período simulado: {inicio} a {fim}.",
        "",
        "> **Limitação:** esta é uma simulação sobre dados sintéticos, não um piloto hospitalar real. Compras emergenciais são valoradas pelo preço unitário de referência; vencimentos exigem movimentação de lotes e por isso ainda não são estimados neste cenário.",
        "",
        "| Métrica | Baseline | Modelo ML | Redução | Redução (%) |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, linha in comparacao.iterrows():
        percentual = "—" if pd.isna(linha["reducao_pct"]) else f"{linha['reducao_pct']:.1f}%"
        linhas.append(
            f"| {linha['metrica']} | {linha['baseline']:.2f} | {linha['modelo_ml']:.2f} | {linha['reducao']:.2f} | {percentual} |"
        )
    return "\n".join(linhas) + "\n"


def main() -> None:
    """Executa a comparação para as últimas quatro janelas de teste do MVP."""
    from pathlib import Path

    base = Path(__file__).resolve().parents[2]
    dados = pd.read_csv(base / "data" / "processed" / "consumo_medicamentos.csv")
    estoque = pd.read_csv(base / "data" / "processed" / "consumo_diario.csv")
    referencia = pd.read_csv(base / "data" / "processed" / "medicamentos_ref.csv")
    ultima_data = pd.to_datetime(dados["data"]).max()
    inicio = (ultima_data - pd.Timedelta(days=27)).date().isoformat()
    fim = ultima_data.date().isoformat()
    baseline = avaliar_baseline_periodo(dados, inicio, fim)
    modelo = avaliar_modelo_periodo(dados, inicio, fim)
    corte = pd.Timestamp(inicio) - pd.Timedelta(days=1)
    estoque["data"] = pd.to_datetime(estoque["data"])
    inicial = estoque[estoque["data"] <= corte].sort_values("data").groupby("medicamento_id").tail(1)
    impacto_baseline = simular_impacto(baseline, dados, referencia, inicial)
    impacto_modelo = simular_impacto(modelo, dados, referencia, inicial)
    relatorio = gerar_relatorio_markdown(comparar_cenarios(impacto_baseline, impacto_modelo), inicio, fim)
    destino = base / "docs" / "arquitetura" / "RESULTADOS_IMPACTO_SIMULADO.md"
    destino.write_text(relatorio, encoding="utf-8")
    print(relatorio)
    print(f"Relatório salvo em: {destino}")


def _validar(df: pd.DataFrame, colunas: set[str], nome: str) -> None:
    faltantes = colunas.difference(df.columns)
    if faltantes:
        raise ValueError(f"{nome} sem colunas obrigatórias: {sorted(faltantes)}")


if __name__ == "__main__":
    main()
