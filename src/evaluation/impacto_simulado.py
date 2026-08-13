"""Simulação de impacto do baseline versus modelo de ML (Issue #17).

Os resultados deste módulo são cenários sobre dados sintéticos, não evidência
de piloto real. A política simulada compra diariamente o necessário para cobrir
o lead time previsto, mais o estoque de segurança. Pedidos regulares chegam
após o prazo do fornecedor; faltas são supridas por compra emergencial no mesmo
dia e contabilizadas separadamente.
"""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Real

import numpy as np
import pandas as pd

from src.data_ingestion.gerar_dataset_sintetico import gerar_lotes_no_corte

COLUNAS_PREVISAO = {"medicamento_id", "data_previsao", "demanda_prevista"}
COLUNAS_REAL = {"medicamento_id", "data", "consumo_unidades"}
COLUNAS_REFERENCIA = {"medicamento_id", "prazo_entrega_dias", "preco_unitario_reais"}
COLUNAS_ESTOQUE = {"medicamento_id", "estoque_disponivel"}
COLUNAS_LOTES = {
    "medicamento_id",
    "quantidade_atual",
    "data_entrada",
    "data_validade",
}
VALIDADE_REPOSICAO_SIMULADA_DIAS = 365


def simular_impacto(
    previsoes: pd.DataFrame,
    consumo_real: pd.DataFrame,
    medicamentos_ref: pd.DataFrame,
    estoque_inicial: pd.DataFrame,
    lotes: pd.DataFrame | None = None,
    fator_seguranca: float | Mapping[str, float] = 0.2,
) -> pd.DataFrame:
    """Simula rupturas, compras emergenciais e custo por medicamento.

    ``fator_seguranca`` é a fração da demanda prevista durante o lead time
    usada como buffer. Pode ser um único valor ou um mapa por medicamento,
    usado pelas políticas de estoque agrupadas da Issue #79. O estoque
    agregado no corte é a fonte de verdade para quantidade; os lotes apenas
    repartem esse saldo por validade.
    """
    _validar(previsoes, COLUNAS_PREVISAO, "previsoes")
    _validar(consumo_real, COLUNAS_REAL, "consumo_real")
    _validar(medicamentos_ref, COLUNAS_REFERENCIA, "medicamentos_ref")
    _validar(estoque_inicial, COLUNAS_ESTOQUE, "estoque_inicial")
    if lotes is not None:
        _validar(lotes, COLUNAS_LOTES, "lotes")
    fatores = _normalizar_fatores_seguranca(fator_seguranca, set(previsoes["medicamento_id"]))

    previsao = previsoes[["medicamento_id", "data_previsao", "demanda_prevista"]].copy()
    previsao["data_previsao"] = pd.to_datetime(previsao["data_previsao"])
    previsao["demanda_prevista"] = pd.to_numeric(previsao["demanda_prevista"])
    real = consumo_real[["medicamento_id", "data", "consumo_unidades"]].copy()
    real["data"] = pd.to_datetime(real["data"])
    real["consumo_unidades"] = pd.to_numeric(real["consumo_unidades"])
    referencia = medicamentos_ref[list(COLUNAS_REFERENCIA)].copy()
    inicial = estoque_inicial[list(COLUNAS_ESTOQUE)].copy()
    lotes = (
        pd.DataFrame(columns=sorted(COLUNAS_LOTES))
        if lotes is None
        else lotes[list(COLUNAS_LOTES)].copy()
    )
    if not lotes.empty:
        lotes["data_entrada"] = pd.to_datetime(lotes["data_entrada"])
        lotes["data_validade"] = pd.to_datetime(lotes["data_validade"])

    dados = real.merge(previsao, left_on=["medicamento_id", "data"], right_on=["medicamento_id", "data_previsao"], how="inner")
    dados = dados.merge(referencia, on="medicamento_id", how="inner").merge(inicial, on="medicamento_id", how="inner")
    if dados.empty:
        raise ValueError("Não há interseção entre previsões, consumo real e estoque inicial.")

    resultados = []
    for medicamento, serie in dados.groupby("medicamento_id", sort=True):
        serie = serie.sort_values("data")
        prazo = int(serie["prazo_entrega_dias"].iloc[0])
        preco = float(serie["preco_unitario_reais"].iloc[0])
        fator_item = fatores[medicamento]
        estoque_inicial_item = float(serie["estoque_disponivel"].iloc[0])
        data_referencia = serie["data"].iloc[0] - pd.Timedelta(days=1)
        lotes_item = lotes[lotes["medicamento_id"] == medicamento].copy()
        estoque_lotes = _montar_estoque_lotes_inicial(
            lotes_item,
            data_referencia,
            estoque_inicial_item,
        )
        chegadas: dict[pd.Timestamp, float] = {}
        rupturas = emergenciais = custo_emergencial = vencidas = 0.0
        quantidade_total_recomendada = estoque_acumulado = 0.0
        episodios = 0
        for _, dia in serie.iterrows():
            data = dia["data"]
            chegada = chegadas.pop(data, 0.0)
            if chegada:
                estoque_lotes.append(
                    (data + pd.Timedelta(days=VALIDADE_REPOSICAO_SIMULADA_DIAS), chegada)
                )
            validos = []
            for validade, quantidade in estoque_lotes:
                if validade < data:
                    vencidas += quantidade
                else:
                    validos.append((validade, quantidade))
            estoque_lotes = validos
            estoque = sum(quantidade for _, quantidade in estoque_lotes)
            demanda_lead_time = max(float(dia["demanda_prevista"]), 0.0) * max(prazo, 1)
            pedido = max(demanda_lead_time * (1 + fator_item) - estoque - sum(chegadas.values()), 0.0)
            quantidade_total_recomendada += pedido
            chegada = data + pd.Timedelta(days=prazo)
            chegadas[chegada] = chegadas.get(chegada, 0.0) + pedido
            realizado = max(float(dia["consumo_unidades"]), 0.0)
            falta = max(realizado - estoque, 0.0)
            if falta > 0:
                episodios += 1
                rupturas += falta
                emergenciais += falta
                custo_emergencial += falta * preco
            restante = realizado
            atualizados = []
            for validade, quantidade in sorted(estoque_lotes):
                consumido = min(quantidade, restante)
                restante -= consumido
                if quantidade > consumido:
                    atualizados.append((validade, quantidade - consumido))
            estoque_lotes = atualizados
            estoque_acumulado += sum(quantidade for _, quantidade in estoque_lotes)
        resultados.append(
            {
                "medicamento_id": medicamento,
                "episodios_ruptura": episodios,
                "unidades_em_ruptura": rupturas,
                "compras_emergenciais_unidades": emergenciais,
                "custo_compras_emergenciais_reais": custo_emergencial,
                "unidades_vencidas": vencidas,
                "quantidade_total_recomendada": quantidade_total_recomendada,
                "estoque_medio_unidades": estoque_acumulado / len(serie),
            }
        )
    return pd.DataFrame(resultados)


def _normalizar_fatores_seguranca(
    fator_seguranca: float | Mapping[str, float], medicamentos: set[str]
) -> dict[str, float]:
    """Valida valor único ou mapa completo, sem fallback silencioso por item."""
    if isinstance(fator_seguranca, Mapping):
        if set(fator_seguranca) != medicamentos:
            raise ValueError("fator_seguranca por medicamento deve cobrir exatamente as previsões.")
        fatores = dict(fator_seguranca)
    else:
        fatores = {medicamento: fator_seguranca for medicamento in medicamentos}
    for medicamento, fator in fatores.items():
        if isinstance(fator, (bool, np.bool_)) or not isinstance(fator, Real):
            raise TypeError(f"fator_seguranca de {medicamento} deve ser numérico.")
        if not np.isfinite(float(fator)) or fator < 0:
            raise ValueError(f"fator_seguranca de {medicamento} deve ser finito e não negativo.")
        fatores[medicamento] = float(fator)
    return fatores


def comparar_cenarios(impacto_baseline: pd.DataFrame, impacto_modelo: pd.DataFrame) -> pd.DataFrame:
    """Compara os impactos agregados e calcula a economia estimada em reais."""
    metricas = [
        "episodios_ruptura",
        "unidades_em_ruptura",
        "compras_emergenciais_unidades",
        "custo_compras_emergenciais_reais",
        "unidades_vencidas",
        "quantidade_total_recomendada",
    ]
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
        "> **Limitação:** esta é uma simulação sobre dados sintéticos, não um piloto hospitalar real. Compras emergenciais são valoradas pelo preço unitário de referência. O consumo segue FEFO (primeiro a vencer, primeiro a sair); cada corte recebe um snapshot sintético de lotes temporalmente compatível com seu estoque agregado, e reposições simuladas recebem validade de 365 dias. Não há histórico completo de movimentação por lote, portanto esse snapshot não reproduz os lotes físicos que existiriam no hospital.",
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


def simular_periodo(
    dados: pd.DataFrame,
    estoque: pd.DataFrame,
    referencia: pd.DataFrame,
    inicio: str,
    fim: str,
) -> pd.DataFrame:
    """Executa a comparação com snapshot de lotes do próprio corte."""
    from src.evaluation.comparar_modelos import (
        avaliar_baseline_periodo,
        avaliar_modelo_periodo,
    )

    baseline = avaliar_baseline_periodo(dados, inicio, fim)
    modelo = avaliar_modelo_periodo(dados, inicio, fim)
    corte = pd.Timestamp(inicio) - pd.Timedelta(days=1)
    inicial = estoque[estoque["data"] <= corte].sort_values("data").groupby("medicamento_id").tail(1)
    lotes_no_corte = gerar_lotes_no_corte(estoque, corte)
    return comparar_cenarios(
        simular_impacto(baseline, dados, referencia, inicial, lotes_no_corte),
        simular_impacto(modelo, dados, referencia, inicial, lotes_no_corte),
    )


def gerar_relatorio_trimestral(resultados_mensais: dict[str, pd.DataFrame]) -> str:
    """Gera visão mensal e total para evitar conclusões de um mês atípico."""
    linhas = [
        "# Impacto simulado: baseline vs. modelo de ML (Issue #17)",
        "",
        "Período simulado: outubro a dezembro de 2025, com validação temporal por janelas de 7 dias.",
        "",
        "> **Limitação:** simulação sobre dados sintéticos, não piloto hospitalar. Compras emergenciais usam o preço unitário de referência. O consumo segue FEFO; cada corte recebe um snapshot sintético de lotes temporalmente compatível com seu estoque agregado e reposições simuladas recebem validade de 365 dias. Como não há histórico completo de movimentação por lote, esse snapshot não reproduz os lotes físicos que existiriam no hospital.",
        "",
        "## Resultado por mês",
        "",
        "| Mês | Métrica | Baseline | Modelo ML | Redução | Redução (%) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for mes, comparacao in resultados_mensais.items():
        for _, linha in comparacao.iterrows():
            percentual = "—" if pd.isna(linha["reducao_pct"]) else f"{linha['reducao_pct']:.1f}%"
            linhas.append(f"| {mes} | {linha['metrica']} | {linha['baseline']:.2f} | {linha['modelo_ml']:.2f} | {linha['reducao']:.2f} | {percentual} |")

    consolidado = pd.concat(resultados_mensais.values()).groupby("metrica")[["baseline", "modelo_ml"]].sum().reset_index()
    consolidado["reducao"] = consolidado["baseline"] - consolidado["modelo_ml"]
    consolidado["reducao_pct"] = consolidado["reducao"].div(consolidado["baseline"].replace(0, pd.NA)) * 100
    linhas += ["", "## Consolidado (3 meses)", "", "| Métrica | Baseline | Modelo ML | Redução | Redução (%) |", "|---|---:|---:|---:|---:|"]
    for _, linha in consolidado.iterrows():
        percentual = "—" if pd.isna(linha["reducao_pct"]) else f"{linha['reducao_pct']:.1f}%"
        linhas.append(f"| {linha['metrica']} | {linha['baseline']:.2f} | {linha['modelo_ml']:.2f} | {linha['reducao']:.2f} | {percentual} |")
    linhas += ["", "## Leitura", "", "No recorte de três meses, o modelo não demonstra ganho operacional consistente frente ao baseline. A comparação deve orientar novos ajustes e validação antes de qualquer uso real."]
    return "\n".join(linhas) + "\n"


def main() -> None:
    """Executa a comparação para as últimas quatro janelas de teste do MVP."""
    from pathlib import Path

    base = Path(__file__).resolve().parents[2]
    dados = pd.read_csv(base / "data" / "processed" / "consumo_medicamentos.csv")
    estoque = pd.read_csv(base / "data" / "processed" / "consumo_diario.csv")
    referencia = pd.read_csv(base / "data" / "processed" / "medicamentos_ref.csv")
    estoque["data"] = pd.to_datetime(estoque["data"])
    inicio, fim = "2025-12-04", "2025-12-31"
    comparacao = simular_periodo(dados, estoque, referencia, inicio, fim)
    relatorio = gerar_relatorio_markdown(comparacao, inicio, fim)
    destino = base / "docs" / "arquitetura" / "RESULTADOS_IMPACTO_SIMULADO.md"
    destino.write_text(relatorio, encoding="utf-8")
    print(relatorio)
    print(f"Relatório salvo em: {destino}")


def _validar(df: pd.DataFrame, colunas: set[str], nome: str) -> None:
    faltantes = colunas.difference(df.columns)
    if faltantes:
        raise ValueError(f"{nome} sem colunas obrigatórias: {sorted(faltantes)}")


def _montar_estoque_lotes_inicial(
    lotes_item: pd.DataFrame,
    data_referencia: pd.Timestamp,
    estoque_inicial: float,
) -> list[tuple[pd.Timestamp, float]]:
    """Cria a composição de validade do estoque no corte sem usar lotes futuros.

    ``lotes.csv`` é uma fotografia do fim do dataset, enquanto a simulação
    pode começar meses antes. O saldo total do corte vem de
    ``consumo_diario.csv``; para distribuí-lo por validade, usamos apenas os
    lotes cuja entrada e validade já são compatíveis com aquela data e
    preservamos sua proporção relativa. Quando não há lote elegível, o saldo
    recebe uma validade residual longa e explícita: não é correto importar um
    lote que só entraria no futuro para preencher essa lacuna.
    """
    elegiveis = lotes_item[
        (lotes_item["data_entrada"] <= data_referencia)
        & (lotes_item["data_validade"] >= data_referencia)
        & (lotes_item["quantidade_atual"] > 0)
    ].copy()
    if elegiveis.empty:
        return [
            (
                data_referencia + pd.Timedelta(days=VALIDADE_REPOSICAO_SIMULADA_DIAS),
                estoque_inicial,
            )
        ]

    total_elegivel = float(elegiveis["quantidade_atual"].sum())
    escala = estoque_inicial / total_elegivel
    return list(
        zip(
            elegiveis["data_validade"],
            elegiveis["quantidade_atual"] * escala,
            strict=True,
        )
    )


if __name__ == "__main__":
    main()
