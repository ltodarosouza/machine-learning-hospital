"""Testes do protocolo formal de validação operacional (Issue #77)."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src.evaluation.protocolo_validacao_operacional import (
    RESSALVA_FINANCEIRA,
    ConfiguracaoProtocolo,
    avaliar_aprovacao,
    avaliar_candidato_na_janela,
    calcular_metricas_janela,
    gerar_janelas_backtest,
    gerar_relatorio_validacao,
    salvar_relatorio_validacao,
)


def _metricas(
    candidato: str,
    custos: list[float],
    episodios: list[float] | None = None,
    rupturas: list[float] | None = None,
    vencimentos: list[float] | None = None,
    mae: float = 10.0,
) -> pd.DataFrame:
    quantidade = len(custos)
    episodios = [10.0] * quantidade if episodios is None else episodios
    rupturas = [20.0] * quantidade if rupturas is None else rupturas
    vencimentos = [5.0] * quantidade if vencimentos is None else vencimentos
    return pd.DataFrame(
        {
            "janela_id": [f"janela_{indice + 1:03d}" for indice in range(quantidade)],
            "candidato": [candidato] * quantidade,
            "mae": [mae] * quantidade,
            "mape": [10.0] * quantidade,
            "vies_previsao": [0.0] * quantidade,
            "subestimacao": [1.0] * quantidade,
            "superestimacao": [1.0] * quantidade,
            "custo_compras_emergenciais_reais": custos,
            "episodios_ruptura": episodios,
            "unidades_em_ruptura": rupturas,
            "unidades_vencidas": vencimentos,
            "quantidade_total_recomendada": [100.0] * quantidade,
        }
    )


def test_geracao_de_janelas_e_deterministica_sem_vazamento() -> None:
    datas = pd.date_range("2024-01-01", periods=393)

    primeira = gerar_janelas_backtest(datas, treino_minimo_dias=365, minimo_janelas=4)
    segunda = gerar_janelas_backtest(
        datas[::-1], treino_minimo_dias=365, minimo_janelas=4
    )

    pd.testing.assert_frame_equal(primeira, segunda)
    assert len(primeira) == 4
    assert (
        pd.to_datetime(primeira["fim_treino"])
        < pd.to_datetime(primeira["inicio_avaliacao"])
    ).all()
    assert (
        (
            pd.to_datetime(primeira["fim_avaliacao"])
            - pd.to_datetime(primeira["inicio_avaliacao"])
        )
        .dt.days.eq(6)
        .all()
    )


def test_janelas_falham_com_dados_insuficientes_lacunas_ou_overlap() -> None:
    with pytest.raises(ValueError, match="Dados insuficientes"):
        gerar_janelas_backtest(pd.date_range("2024-01-01", periods=380))
    datas_com_lacuna = pd.date_range("2024-01-01", periods=393).delete(100)
    with pytest.raises(ValueError, match="sem lacunas"):
        gerar_janelas_backtest(datas_com_lacuna)
    with pytest.raises(ValueError, match="overlap"):
        gerar_janelas_backtest(pd.date_range("2024-01-01", periods=393), passo_dias=6)


def test_calcula_metricas_preditivas_e_operacionais_sem_mutar_entradas() -> None:
    previsoes = pd.DataFrame(
        {
            "medicamento_id": ["a", "a", "a"],
            "demanda_prevista": [8.0, 14.0, 5.0],
            "consumo_unidades": [10.0, 10.0, 0.0],
        }
    )
    impacto = pd.DataFrame(
        {
            "custo_compras_emergenciais_reais": [20.0, 5.0],
            "episodios_ruptura": [1.0, 2.0],
            "unidades_em_ruptura": [2.0, 3.0],
            "unidades_vencidas": [1.0, 0.0],
            "quantidade_total_recomendada": [30.0, 20.0],
        }
    )
    copia_previsoes = previsoes.copy(deep=True)
    copia_impacto = impacto.copy(deep=True)

    resultado = calcular_metricas_janela(previsoes, impacto, "janela_001", "candidato")

    assert resultado.loc[0, "mae"] == pytest.approx((2 + 4 + 5) / 3)
    assert resultado.loc[0, "mape"] == pytest.approx(30.0)
    assert resultado.loc[0, "vies_previsao"] == pytest.approx(7 / 3)
    assert resultado.loc[0, "subestimacao"] == 2
    assert resultado.loc[0, "superestimacao"] == 9
    assert resultado.loc[0, "custo_compras_emergenciais_reais"] == 25
    assert resultado.loc[0, "quantidade_total_recomendada"] == 50
    pd.testing.assert_frame_equal(previsoes, copia_previsoes)
    pd.testing.assert_frame_equal(impacto, copia_impacto)


def test_aprova_reducao_superior_a_dez_por_cento_sem_piora() -> None:
    decisao = avaliar_aprovacao(
        _metricas("baseline", [100, 100, 100, 100]),
        _metricas("modelo", [85, 85, 85, 85]),
    )

    assert decisao["status"] == "aprovado"
    assert decisao["aprovado"] is True
    assert decisao["janelas_com_meta_atingida"] == 4
    assert decisao["reducao_custo_emergencial_pct"] == pytest.approx(15.0)


def test_limite_exato_de_dez_por_cento_aprova() -> None:
    decisao = avaliar_aprovacao(
        _metricas("baseline", [100] * 4), _metricas("modelo", [90] * 4)
    )
    assert decisao["status"] == "aprovado"


def test_abaixo_de_dez_por_cento_rejeita() -> None:
    decisao = avaliar_aprovacao(
        _metricas("baseline", [100] * 4), _metricas("modelo", [91] * 4)
    )
    assert decisao["status"] == "rejeitado"
    assert any("abaixo da meta" in motivo for motivo in decisao["motivos_rejeicao"])


def test_reducao_causada_por_apenas_uma_janela_rejeita_por_inconsistencia() -> None:
    decisao = avaliar_aprovacao(
        _metricas("baseline", [100] * 4), _metricas("modelo", [50, 100, 100, 100])
    )
    assert decisao["status"] == "rejeitado"
    assert decisao["janelas_com_meta_atingida"] == 1
    assert any(
        "Consistência insuficiente" in motivo for motivo in decisao["motivos_rejeicao"]
    )


@pytest.mark.parametrize(
    "campo,argumento",
    [
        ("episodios_ruptura", {"episodios": [11] * 4}),
        ("unidades_em_ruptura", {"rupturas": [22] * 4}),
        ("unidades_vencidas", {"vencimentos": [6] * 4}),
    ],
)
def test_reducao_com_piora_operacional_relevante_rejeita(campo, argumento) -> None:
    decisao = avaliar_aprovacao(
        _metricas("baseline", [100] * 4),
        _metricas("modelo", [80] * 4, mae=5.0, **argumento),
    )
    assert decisao["status"] == "rejeitado"
    assert any(campo in motivo for motivo in decisao["motivos_rejeicao"])


def test_mae_menor_nao_aprova_operacao_pior() -> None:
    decisao = avaliar_aprovacao(
        _metricas("baseline", [100] * 4, mae=10),
        _metricas("modelo", [110] * 4, mae=1),
    )
    assert decisao["status"] == "rejeitado"


def test_metricas_ausentes_nao_finitas_ou_janelas_faltantes_dao_dados_insuficientes() -> (
    None
):
    baseline = _metricas("baseline", [100] * 4)
    candidato = _metricas("modelo", [80] * 4)
    assert (
        avaliar_aprovacao(baseline, candidato.drop(columns="mape"))["status"]
        == "dados_insuficientes"
    )
    candidato.loc[0, "mae"] = float("nan")
    assert avaliar_aprovacao(baseline, candidato)["status"] == "dados_insuficientes"
    assert (
        avaliar_aprovacao(baseline, _metricas("modelo", [80] * 3))["status"]
        == "dados_insuficientes"
    )


def test_baseline_com_custo_zero_nunca_aprova() -> None:
    decisao = avaliar_aprovacao(
        _metricas("baseline", [0] * 4), _metricas("modelo", [0] * 4)
    )
    assert decisao["status"] == "dados_insuficientes"
    assert decisao["reducao_custo_emergencial_pct"] is None


def test_uma_janela_com_custo_baseline_zero_invalida_comparacao() -> None:
    decisao = avaliar_aprovacao(
        _metricas("baseline", [100, 100, 100, 0, 100]),
        _metricas("modelo", [80, 80, 80, 0, 80]),
    )
    assert decisao["status"] == "dados_insuficientes"


def test_mape_sem_denominador_positivo_invalida_janela() -> None:
    previsoes = pd.DataFrame(
        {
            "medicamento_id": ["a"],
            "demanda_prevista": [1.0],
            "consumo_unidades": [0.0],
        }
    )
    impacto = pd.DataFrame(
        {
            "custo_compras_emergenciais_reais": [0.0],
            "episodios_ruptura": [0.0],
            "unidades_em_ruptura": [0.0],
            "unidades_vencidas": [0.0],
            "quantidade_total_recomendada": [1.0],
        }
    )
    with pytest.raises(ValueError, match="reconciliar"):
        calcular_metricas_janela(previsoes, impacto, "janela_001", "modelo")


def test_integracao_reutiliza_simulador_e_reconcilia_recorte() -> None:
    datas = pd.date_range("2026-01-01", periods=3)
    previsoes = pd.DataFrame(
        {
            "medicamento_id": ["a"] * 3,
            "data_previsao": datas,
            "demanda_prevista": [10.0] * 3,
        }
    )
    consumo = pd.DataFrame(
        {
            "medicamento_id": ["a"] * 3,
            "data": datas,
            "consumo_unidades": [10.0] * 3,
        }
    )
    referencia = pd.DataFrame(
        {
            "medicamento_id": ["a"],
            "prazo_entrega_dias": [1],
            "preco_unitario_reais": [2.0],
        }
    )
    estoque = pd.DataFrame({"medicamento_id": ["a"], "estoque_disponivel": [10.0]})

    resultado = avaliar_candidato_na_janela(
        previsoes,
        consumo,
        referencia,
        estoque,
        "janela_001",
        "modelo",
        fator_seguranca=0,
    )

    assert resultado.loc[0, "mae"] == 0
    assert resultado.loc[0, "quantidade_total_recomendada"] >= 0

    with pytest.raises(ValueError, match="mesmo recorte"):
        avaliar_candidato_na_janela(
            previsoes.iloc[:-1], consumo, referencia, estoque, "janela_001", "modelo"
        )


def test_independencia_de_ordenacao_e_reprodutibilidade_total(tmp_path) -> None:
    baseline = _metricas("baseline", [100, 120, 90, 110])
    candidato = _metricas("modelo", [85, 100, 75, 90])
    primeira = avaliar_aprovacao(baseline, candidato)
    segunda = avaliar_aprovacao(
        baseline.sample(frac=1, random_state=1),
        candidato.sample(frac=1, random_state=2),
    )
    assert primeira == segunda

    janelas = gerar_janelas_backtest(pd.date_range("2024-01-01", periods=393))
    metricas = pd.concat([baseline, candidato], ignore_index=True)
    config = ConfiguracaoProtocolo()
    metadados = {"commit": "abc123", "dataset_hash": "def456"}
    pasta_1 = tmp_path / "primeira"
    pasta_2 = tmp_path / "segunda"
    salvar_relatorio_validacao(pasta_1, metadados, config, janelas, metricas, primeira)
    salvar_relatorio_validacao(pasta_2, metadados, config, janelas, metricas, primeira)
    for nome in [
        "janelas.csv",
        "metricas.csv",
        "configuracao.json",
        "decisao.json",
        "RELATORIO_VALIDACAO_OPERACIONAL.md",
    ]:
        assert (pasta_1 / nome).read_bytes() == (pasta_2 / nome).read_bytes()


def test_relatorio_reconcilia_decisao_e_inclui_ressalva_financeira() -> None:
    baseline = _metricas("baseline", [100] * 4)
    candidato = _metricas("modelo", [85] * 4)
    decisao = avaliar_aprovacao(baseline, candidato)
    janelas = gerar_janelas_backtest(pd.date_range("2024-01-01", periods=393))
    relatorio = gerar_relatorio_validacao(
        {"commit": "abc"},
        ConfiguracaoProtocolo(),
        janelas,
        pd.concat([baseline, candidato], ignore_index=True),
        decisao,
    )

    assert RESSALVA_FINANCEIRA in relatorio
    assert (
        json.dumps(decisao, ensure_ascii=False, sort_keys=True, indent=2) in relatorio
    )
    assert "Issue #76 ainda não está integrada" in relatorio
