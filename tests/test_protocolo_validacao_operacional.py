"""Testes do protocolo formal de validação operacional (Issue #77)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src.evaluation.protocolo_validacao_operacional import (
    COLUNAS_OPERACIONAIS,
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
    assert "relatório operacional da Issue #76" in relatorio


def test_candidato_invalido_retorna_dados_insuficientes_sem_excecao() -> None:
    baseline = _metricas("baseline", [100] * 4)
    candidato = _metricas("modelo", [80] * 4)
    candidato.loc[1, "candidato"] = "outro"

    decisao = avaliar_aprovacao(baseline, candidato)

    assert decisao["status"] == "dados_insuficientes"
    assert decisao["candidato"] == "desconhecido"


def test_rejeita_baseline_e_candidato_com_mesmo_identificador() -> None:
    decisao = avaliar_aprovacao(
        _metricas("modelo", [100] * 4), _metricas("modelo", [80] * 4)
    )
    assert decisao["status"] == "dados_insuficientes"
    assert any(
        "identificadores diferentes" in motivo for motivo in decisao["motivos_rejeicao"]
    )


@pytest.mark.parametrize("valor", [True, 0, 1.5])
def test_rejeita_numero_ou_booleano_como_data_de_backtest(valor) -> None:
    datas = pd.Series(pd.date_range("2024-01-01", periods=393), dtype=object)
    datas.iloc[0] = valor
    with pytest.raises(TypeError, match="não números"):
        gerar_janelas_backtest(datas)


def test_rejeita_valores_negativos_individuais_antes_da_agregacao() -> None:
    previsoes = pd.DataFrame(
        {
            "medicamento_id": ["a", "b"],
            "demanda_prevista": [10.0, -10.0],
            "consumo_unidades": [5.0, 5.0],
        }
    )
    impacto = pd.DataFrame(
        {
            "custo_compras_emergenciais_reais": [10.0, -10.0],
            "episodios_ruptura": [1.0, 0.0],
            "unidades_em_ruptura": [1.0, 0.0],
            "unidades_vencidas": [0.0, 0.0],
            "quantidade_total_recomendada": [1.0, 0.0],
        }
    )
    with pytest.raises(ValueError, match="demanda ou consumo negativos"):
        impacto_positivo = impacto.copy()
        impacto_positivo["custo_compras_emergenciais_reais"] = impacto_positivo[
            "custo_compras_emergenciais_reais"
        ].abs()
        calcular_metricas_janela(previsoes, impacto_positivo, "janela_001", "modelo")
    with pytest.raises(ValueError, match="métricas negativas"):
        previsoes_positivas = previsoes.copy()
        previsoes_positivas["demanda_prevista"] = previsoes_positivas[
            "demanda_prevista"
        ].abs()
        calcular_metricas_janela(previsoes_positivas, impacto, "janela_001", "modelo")


def test_relatorio_rejeita_decisao_adulterada_janelas_incompativeis_e_candidato_extra() -> (
    None
):
    baseline = _metricas("baseline", [100] * 4)
    candidato = _metricas("modelo", [85] * 4)
    metricas = pd.concat([baseline, candidato], ignore_index=True)
    decisao = avaliar_aprovacao(baseline, candidato)
    janelas = gerar_janelas_backtest(pd.date_range("2024-01-01", periods=393))
    config = ConfiguracaoProtocolo()

    adulterada = dict(decisao)
    adulterada["aprovado"] = False
    with pytest.raises(ValueError, match="não é reconciliável"):
        gerar_relatorio_validacao({}, config, janelas, metricas, adulterada)

    janelas_vazamento = janelas.copy()
    janelas_vazamento.loc[0, "fim_treino"] = janelas_vazamento.loc[
        0, "inicio_avaliacao"
    ]
    with pytest.raises(ValueError, match="vazamento"):
        gerar_relatorio_validacao({}, config, janelas_vazamento, metricas, decisao)

    extra = _metricas("terceiro", [90] * 4)
    with pytest.raises(ValueError, match="apenas baseline"):
        gerar_relatorio_validacao(
            {},
            config,
            janelas,
            pd.concat([metricas, extra], ignore_index=True),
            decisao,
        )


def test_salvamento_canonico_independe_da_ordem_das_entradas(tmp_path) -> None:
    baseline = _metricas("baseline", [100, 120, 90, 110])
    candidato = _metricas("modelo", [85, 100, 75, 90])
    decisao = avaliar_aprovacao(baseline, candidato)
    janelas = gerar_janelas_backtest(pd.date_range("2024-01-01", periods=393))
    metricas = pd.concat([baseline, candidato], ignore_index=True)
    config = ConfiguracaoProtocolo()

    salvar_relatorio_validacao(tmp_path / "a", {}, config, janelas, metricas, decisao)
    salvar_relatorio_validacao(
        tmp_path / "b",
        {},
        config,
        janelas.sample(frac=1, random_state=3),
        metricas.sample(frac=1, random_state=4),
        decisao,
    )
    for nome in ["janelas.csv", "metricas.csv", "RELATORIO_VALIDACAO_OPERACIONAL.md"]:
        assert (tmp_path / "a" / nome).read_bytes() == (
            tmp_path / "b" / nome
        ).read_bytes()


def test_matriz_aleatoria_deterministica_obedece_invariantes_de_aprovacao() -> None:
    rng = np.random.default_rng(7713)
    for _ in range(250):
        quantidade = int(rng.integers(4, 13))
        custos_base = rng.uniform(1, 10_000, quantidade)
        fatores_custo = rng.uniform(0.5, 1.3, quantidade)
        episodios_base = rng.uniform(1, 100, quantidade)
        rupturas_base = rng.uniform(1, 1_000, quantidade)
        vencimentos_base = rng.uniform(1, 500, quantidade)
        fatores_operacionais = rng.uniform(0.7, 1.2, (3, quantidade))
        baseline = _metricas(
            "baseline",
            custos_base.tolist(),
            episodios_base.tolist(),
            rupturas_base.tolist(),
            vencimentos_base.tolist(),
        )
        candidato = _metricas(
            "modelo",
            (custos_base * fatores_custo).tolist(),
            (episodios_base * fatores_operacionais[0]).tolist(),
            (rupturas_base * fatores_operacionais[1]).tolist(),
            (vencimentos_base * fatores_operacionais[2]).tolist(),
        )

        decisao = avaliar_aprovacao(baseline, candidato)

        reducao = (
            1 - candidato["custo_compras_emergenciais_reais"].sum() / custos_base.sum()
        )
        janelas_meta = int((1 - fatores_custo >= 0.10 - 1e-9).sum())
        piora = any(
            candidato[coluna].sum() / baseline[coluna].sum() - 1 > 0.05 + 1e-9
            for coluna in [
                "episodios_ruptura",
                "unidades_em_ruptura",
                "unidades_vencidas",
            ]
        )
        esperado = bool(
            reducao >= 0.10 - 1e-9
            and janelas_meta / quantidade >= 0.75 - 1e-9
            and not piora
        )
        assert decisao["aprovado"] is esperado
        assert (decisao["status"] == "aprovado") is esperado


def test_rejeita_overflow_de_agregacao_e_protocolo_de_uma_janela() -> None:
    baseline = _metricas("baseline", [1e308] * 4)
    candidato = _metricas("modelo", [8e307] * 4)
    decisao = avaliar_aprovacao(baseline, candidato)
    assert decisao["status"] == "dados_insuficientes"
    assert any(
        "não finito após agregação" in motivo for motivo in decisao["motivos_rejeicao"]
    )

    baseline_operacional = _metricas("baseline", [100] * 4, episodios=[1e308] * 4)
    candidato_operacional = _metricas("modelo", [80] * 4, episodios=[8e307] * 4)
    decisao_operacional = avaliar_aprovacao(baseline_operacional, candidato_operacional)
    assert decisao_operacional["status"] == "dados_insuficientes"
    assert any(
        "não finito após agregação" in motivo
        for motivo in decisao_operacional["motivos_rejeicao"]
    )

    with pytest.raises(ValueError, match="múltiplas janelas"):
        ConfiguracaoProtocolo(minimo_janelas=1)
    with pytest.raises(ValueError, match="múltiplas janelas"):
        gerar_janelas_backtest(
            pd.date_range("2024-01-01", periods=370), minimo_janelas=1
        )


@pytest.mark.parametrize(
    "argumento,valor",
    [
        ("versao", ""),
        ("horizonte_dias", 0),
        ("treino_minimo_dias", -1),
        ("reducao_minima_custo", float("inf")),
        ("fracao_minima_janelas_com_meta", 1.1),
        ("aumento_relevante_maximo", True),
        ("tolerancia_empate", -1),
    ],
)
def test_configuracao_invalida_falha_na_criacao(argumento, valor) -> None:
    with pytest.raises((TypeError, ValueError)):
        ConfiguracaoProtocolo(**{argumento: valor})


def test_metricas_da_janela_normalizam_numeros_textuais_sem_misturar_tipos() -> None:
    previsoes = pd.DataFrame(
        {
            "medicamento_id": ["a", "b"],
            "demanda_prevista": ["10", "20"],
            "consumo_unidades": ["8", "25"],
        }
    )
    impacto = pd.DataFrame({coluna: ["1", "2"] for coluna in COLUNAS_OPERACIONAIS})

    resultado = calcular_metricas_janela(
        previsoes, impacto, "janela_001", "modelo"
    ).iloc[0]

    assert resultado["vies_previsao"] == pytest.approx(-1.5)
    assert resultado["custo_compras_emergenciais_reais"] == pytest.approx(3)


def test_relatorio_rejeita_periodos_temporais_incoerentes_e_metadados_invalidos() -> (
    None
):
    baseline = _metricas("baseline", [100] * 4)
    candidato = _metricas("modelo", [85] * 4)
    metricas = pd.concat([baseline, candidato], ignore_index=True)
    decisao = avaliar_aprovacao(baseline, candidato)
    janelas = gerar_janelas_backtest(pd.date_range("2024-01-01", periods=393))
    config = ConfiguracaoProtocolo()

    with pytest.raises(TypeError, match="metadados"):
        gerar_relatorio_validacao([], config, janelas, metricas, decisao)

    treino_invertido = janelas.copy()
    treino_invertido.loc[0, "inicio_treino"] = treino_invertido.loc[0, "fim_treino"]
    treino_invertido.loc[0, "fim_treino"] = "2023-12-31"
    with pytest.raises(ValueError, match="treino invertido"):
        gerar_relatorio_validacao({}, config, treino_invertido, metricas, decisao)

    treino_com_lacuna = janelas.copy()
    treino_com_lacuna.loc[0, "fim_treino"] = (
        (pd.Timestamp(treino_com_lacuna.loc[0, "fim_treino"]) - pd.Timedelta(days=1))
        .date()
        .isoformat()
    )
    with pytest.raises(ValueError, match="véspera"):
        gerar_relatorio_validacao({}, config, treino_com_lacuna, metricas, decisao)
