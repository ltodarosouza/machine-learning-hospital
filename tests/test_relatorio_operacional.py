"""Testes do relatório operacional por medicamento, mês e tipo de erro (Issue #76)."""

import pandas as pd
import pytest

from src.evaluation.relatorio_operacional import (
    calcular_metricas_previsao,
    consolidar_diferenca_por_medicamento,
    gerar_relatorio_markdown,
)


def _comparacao() -> pd.DataFrame:
    datas = pd.date_range("2026-01-01", periods=3)
    return pd.DataFrame(
        {
            "metodo": ["baseline"] * 3 + ["modelo_ml"] * 3,
            "medicamento_id": ["med_a"] * 6,
            "data_previsao": list(datas) * 2,
            "demanda_prevista": [5.0, 5.0, 5.0, 8.0, 12.0, 10.0],
            "consumo_unidades": [10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
        }
    )


def test_vies_negativo_quando_previsao_fica_abaixo_do_real() -> None:
    metricas = calcular_metricas_previsao(_comparacao())
    baseline = metricas[(metricas["metodo"] == "baseline") & (metricas["medicamento_id"] == "med_a")].iloc[0]

    assert baseline["vies"] < 0
    assert baseline["unidades_subestimadas"] == 15.0
    assert baseline["unidades_superestimadas"] == 0.0


def test_decompoe_subestimacao_e_superestimacao_no_mesmo_medicamento() -> None:
    metricas = calcular_metricas_previsao(_comparacao())
    modelo = metricas[(metricas["metodo"] == "modelo_ml") & (metricas["medicamento_id"] == "med_a")].iloc[0]

    # dias: -2 (sub), +2 (super), 0 (nenhum)
    assert modelo["unidades_subestimadas"] == 2.0
    assert modelo["unidades_superestimadas"] == 2.0
    assert modelo["mae"] == (2.0 + 2.0 + 0.0) / 3


def test_erro_absoluto_decomposto_soma_subestimado_mais_superestimado() -> None:
    comparacao = _comparacao()
    metricas = calcular_metricas_previsao(comparacao)
    n_dias = comparacao.groupby(["metodo", "medicamento_id"]).size().iloc[0]

    for _, linha in metricas.iterrows():
        assert linha["mae"] * n_dias == pytest.approx(linha["unidades_subestimadas"] + linha["unidades_superestimadas"])


def _detalhamento_dois_meses() -> pd.DataFrame:
    linhas = []
    for mes, custo_baseline, custo_modelo, episodios_baseline, episodios_modelo in [
        ("01", 100.0, 300.0, 2, 5),
        ("02", 50.0, 20.0, 1, 0),
    ]:
        linhas.append(
            {
                "mes": mes,
                "medicamento_id": "med_a",
                "metodo": "baseline",
                "mae": 1.0,
                "vies": -0.5,
                "unidades_subestimadas": 3.0,
                "unidades_superestimadas": 0.0,
                "mape": 10.0,
                "episodios_ruptura": episodios_baseline,
                "unidades_em_ruptura": 5.0,
                "compras_emergenciais_unidades": 5.0,
                "custo_compras_emergenciais_reais": custo_baseline,
                "unidades_vencidas": 1.0,
            }
        )
        linhas.append(
            {
                "mes": mes,
                "medicamento_id": "med_a",
                "metodo": "modelo_ml",
                "mae": 0.8,
                "vies": 0.2,
                "unidades_subestimadas": 0.0,
                "unidades_superestimadas": 2.0,
                "mape": 8.0,
                "episodios_ruptura": episodios_modelo,
                "unidades_em_ruptura": 8.0,
                "compras_emergenciais_unidades": 8.0,
                "custo_compras_emergenciais_reais": custo_modelo,
                "unidades_vencidas": 3.0,
            }
        )
    return pd.DataFrame(linhas)


def test_consolidacao_soma_diferenca_atraves_dos_meses() -> None:
    diferenca = consolidar_diferenca_por_medicamento(_detalhamento_dois_meses()).set_index("medicamento_id")

    # custo: (300-100) + (20-50) = 200 - 30 = 170
    assert diferenca.loc["med_a", "diferenca_custo_reais"] == 170.0
    # episodios: (5-2) + (0-1) = 3 - 1 = 2
    assert diferenca.loc["med_a", "diferenca_episodios_ruptura"] == 2.0


def test_relatorio_markdown_lista_o_medicamento_no_detalhamento_e_no_destaque() -> None:
    relatorio = gerar_relatorio_markdown(_detalhamento_dois_meses())

    assert "med_a" in relatorio
    assert "01" in relatorio and "02" in relatorio
    assert "Medicamentos que mais pioram" in relatorio
    assert "Medicamentos que mais melhoram" in relatorio
