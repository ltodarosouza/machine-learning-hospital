import pandas as pd
import pytest

from src.evaluation.impacto_simulado import comparar_cenarios, gerar_relatorio_trimestral, simular_impacto


def _entrada(previsao: list[float]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    datas = pd.date_range("2026-01-01", periods=3)
    return (
        pd.DataFrame({"medicamento_id": ["med_a"] * 3, "data_previsao": datas, "demanda_prevista": previsao}),
        pd.DataFrame({"medicamento_id": ["med_a"] * 3, "data": datas, "consumo_unidades": [10.0] * 3}),
        pd.DataFrame({"medicamento_id": ["med_a"], "prazo_entrega_dias": [1], "preco_unitario_reais": [2.0]}),
        pd.DataFrame({"medicamento_id": ["med_a"], "estoque_disponivel": [10.0]}),
    )


def test_previsao_melhor_reduz_compras_emergenciais():
    ruim = simular_impacto(*_entrada([0.0, 0.0, 0.0]), fator_seguranca=0)
    boa = simular_impacto(*_entrada([10.0, 10.0, 10.0]), fator_seguranca=0)
    comparacao = comparar_cenarios(ruim, boa).set_index("metrica")

    assert ruim.loc[0, "compras_emergenciais_unidades"] > boa.loc[0, "compras_emergenciais_unidades"]
    assert comparacao.loc["custo_compras_emergenciais_reais", "reducao"] > 0


def test_aceita_fator_de_seguranca_por_medicamento_e_reporta_estoque_medio() -> None:
    resultado = simular_impacto(*_entrada([10.0, 10.0, 10.0]), fator_seguranca={"med_a": 0.5})

    assert resultado.loc[0, "quantidade_total_recomendada"] >= 0
    assert resultado.loc[0, "estoque_medio_unidades"] >= 0


def test_rejeita_mapa_de_fator_incompleto() -> None:
    with pytest.raises(ValueError, match="cobrir exatamente"):
        simular_impacto(*_entrada([10.0, 10.0, 10.0]), fator_seguranca={})


def test_contabiliza_lote_vencido_antes_do_consumo():
    previsao, real, referencia, estoque = _entrada([0.0, 0.0, 0.0])
    lotes = pd.DataFrame(
        {
            "medicamento_id": ["med_a"],
            "quantidade_atual": [10.0],
            "data_entrada": ["2025-12-01"],
            "data_validade": ["2025-12-31"],
        }
    )
    resultado = simular_impacto(previsao, real, referencia, estoque, lotes=lotes)
    assert resultado.loc[0, "unidades_vencidas"] == 10.0


def test_ignora_lote_que_ainda_nao_existia_no_corte() -> None:
    previsao, real, referencia, estoque = _entrada([0.0, 0.0, 0.0])
    real["consumo_unidades"] = 0.0
    lotes = pd.DataFrame(
        {
            "medicamento_id": ["med_a", "med_a"],
            "quantidade_atual": [5.0, 100.0],
            "data_entrada": ["2025-12-01", "2026-01-02"],
            "data_validade": ["2026-01-02", "2027-01-01"],
        }
    )

    resultado = simular_impacto(previsao, real, referencia, estoque, lotes=lotes)

    # Em 31/12 só o primeiro lote existia. Ele deve representar as 10 unidades
    # do estoque inicial, em vez de ser diluído por 100 unidades futuras.
    assert resultado.loc[0, "unidades_vencidas"] == 10.0


def test_cria_saldo_residual_sem_vazar_lote_futuro() -> None:
    previsao, real, referencia, estoque = _entrada([0.0, 0.0, 0.0])
    lotes = pd.DataFrame(
        {
            "medicamento_id": ["med_a"],
            "quantidade_atual": [10.0],
            "data_entrada": ["2026-01-02"],
            "data_validade": ["2026-01-03"],
        }
    )

    resultado = simular_impacto(previsao, real, referencia, estoque, lotes=lotes)

    # O lote só entrou depois do corte. O saldo de 31/12 continua existindo,
    # mas recebe validade residual em vez de herdar uma validade futura.
    assert resultado.loc[0, "unidades_vencidas"] == 0.0


def _comparacao_mensal(baseline: float, modelo_ml: float) -> pd.DataFrame:
    metricas = ["episodios_ruptura", "unidades_em_ruptura", "compras_emergenciais_unidades", "custo_compras_emergenciais_reais", "unidades_vencidas", "quantidade_total_recomendada"]
    dados = {"metrica": metricas, "baseline": [baseline] * len(metricas), "modelo_ml": [modelo_ml] * len(metricas)}
    df = pd.DataFrame(dados)
    df["reducao"] = df["baseline"] - df["modelo_ml"]
    df["reducao_pct"] = df["reducao"].div(df["baseline"].replace(0, pd.NA)) * 100
    return df


def test_leitura_trimestral_reflete_reducao_consistente_de_custo() -> None:
    """Regressão: uma versão anterior citava, em texto fixo, 'sem ganho operacional
    consistente' — passou a contradizer a própria tabela do relatório assim que o
    modelo mudou (Issue #86). A leitura precisa ser derivada, não escrita à mão."""
    resultados_mensais = {
        "10": _comparacao_mensal(100.0, 70.0),
        "11": _comparacao_mensal(100.0, 65.0),
        "12": _comparacao_mensal(100.0, 60.0),
    }
    relatorio = gerar_relatorio_trimestral(resultados_mensais)

    assert "reduz o custo de compra emergencial em 35.0%" in relatorio
    assert "não demonstra ganho operacional" not in relatorio


def test_leitura_trimestral_reporta_falta_de_reducao_sem_maquiagem() -> None:
    resultados_mensais = {
        "10": _comparacao_mensal(100.0, 110.0),
        "11": _comparacao_mensal(100.0, 100.0),
    }
    relatorio = gerar_relatorio_trimestral(resultados_mensais)

    assert "não demonstra ganho operacional consistente" in relatorio
