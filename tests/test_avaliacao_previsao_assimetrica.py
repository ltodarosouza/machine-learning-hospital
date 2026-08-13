"""Testes da avaliação de candidatos de previsão assimétrica (Issue #78).

Não treina modelos de verdade (caro) — cobre a composição das métricas do
protocolo em decisões, a montagem de janelas oficiais e a lógica do
relatório (recomendação, ganhos/perdas por medicamento), com métricas
sintéticas no mesmo formato produzido por `coletar_resultados`.
"""

from __future__ import annotations

import pandas as pd

from src.evaluation.avaliacao_previsao_assimetrica import (
    CANDIDATOS_QUANTILICOS,
    _candidatos_promissores_na_simulacao_continua,
    _secao_sensibilidade,
    _secao_simulacao_continua,
    _tabela_markdown,
    calcular_decisoes,
    gerar_janelas_oficiais,
    gerar_relatorio_markdown,
)
from src.evaluation.protocolo_validacao_operacional import ConfiguracaoProtocolo


def _metricas_candidato(candidato: str, custos: list[float], mae: float = 10.0) -> pd.DataFrame:
    n = len(custos)
    return pd.DataFrame(
        {
            "janela_id": [f"janela_{i + 1:03d}" for i in range(n)],
            "candidato": [candidato] * n,
            "mae": [mae] * n,
            "mape": [10.0] * n,
            "vies_previsao": [0.0] * n,
            "subestimacao": [5.0] * n,
            "superestimacao": [5.0] * n,
            "custo_compras_emergenciais_reais": custos,
            "episodios_ruptura": [10.0] * n,
            "unidades_em_ruptura": [20.0] * n,
            "unidades_vencidas": [5.0] * n,
            "quantidade_total_recomendada": [100.0] * n,
        }
    )


def _metricas_protocolo_sinteticas() -> pd.DataFrame:
    """Um candidato claramente melhor (`quantile_060`) e um pior (`quantile_080`)."""
    custos_baseline = [100.0, 100.0, 100.0, 100.0]
    custos_modelo_atual = [90.0, 90.0, 90.0, 90.0]
    partes = [
        _metricas_candidato("baseline", custos_baseline),
        _metricas_candidato("modelo_atual", custos_modelo_atual),
        _metricas_candidato("quantile_060", [70.0, 70.0, 70.0, 70.0]),  # bate baseline e modelo atual
        _metricas_candidato("quantile_080", [95.0, 95.0, 95.0, 95.0]),  # melhora pouco, não bate meta de 10%
    ]
    return pd.concat(partes, ignore_index=True)


def test_gerar_janelas_oficiais_usa_a_configuracao_do_protocolo() -> None:
    configuracao = ConfiguracaoProtocolo(treino_minimo_dias=10, minimo_janelas=4, horizonte_dias=2)
    dados = pd.DataFrame({"data": pd.date_range("2024-01-01", periods=30, freq="D")})

    janelas = gerar_janelas_oficiais(dados, configuracao)

    assert len(janelas) == 4
    assert list(janelas["janela_id"]) == [f"janela_{i + 1:03d}" for i in range(4)]


def test_calcular_decisoes_cobre_vs_baseline_e_vs_modelo_atual_para_cada_candidato() -> None:
    configuracao = ConfiguracaoProtocolo()
    decisoes = calcular_decisoes(_metricas_protocolo_sinteticas(), configuracao)

    assert set(decisoes) == set(CANDIDATOS_QUANTILICOS)
    for decisao in decisoes.values():
        assert {"vs_baseline", "vs_modelo_atual"} <= set(decisao)


def test_candidato_que_bate_modelo_atual_e_aprovado_na_comparacao_operacional() -> None:
    configuracao = ConfiguracaoProtocolo()
    decisoes = calcular_decisoes(_metricas_protocolo_sinteticas(), configuracao)

    # 70 vs. 90 (modelo atual) é redução de 22.2%, acima da meta de 10%.
    assert decisoes["quantile_060"]["vs_modelo_atual"]["aprovado"] is True
    # 95 vs. 90 é piora, não redução.
    assert decisoes["quantile_080"]["vs_modelo_atual"]["aprovado"] is False


def test_relatorio_recomenda_manter_modelo_atual_quando_nenhum_candidato_e_aprovado() -> None:
    metricas = pd.concat(
        [
            _metricas_candidato("baseline", [100.0] * 4),
            _metricas_candidato("modelo_atual", [90.0] * 4),
            _metricas_candidato("quantile_060", [95.0] * 4),
            _metricas_candidato("quantile_080", [99.0] * 4),
        ],
        ignore_index=True,
    )
    configuracao = ConfiguracaoProtocolo()
    decisoes = calcular_decisoes(metricas, configuracao)
    janelas = pd.DataFrame(
        {
            "janela_id": ["janela_001", "janela_002", "janela_003", "janela_004"],
            "inicio_treino": ["2024-01-01"] * 4,
            "fim_treino": ["2024-12-30"] * 4,
            "inicio_avaliacao": ["2024-12-31"] * 4,
            "fim_avaliacao": ["2025-01-06"] * 4,
        }
    )
    detalhamento = pd.concat(
        [
            pd.DataFrame(
                {
                    "janela_id": ["janela_001", "janela_001"],
                    "candidato": [nome] * 2,
                    "medicamento_id": ["med_a", "med_b"],
                    "custo_compras_emergenciais_reais": [10.0, 20.0],
                }
            )
            for nome in ["modelo_atual", "quantile_060", "quantile_080"]
        ],
        ignore_index=True,
    )
    metadados = {
        "commit": "abc1234",
        "hash_consumo_medicamentos": "deadbeef",
        "versoes": "{}",
        "hiperparametros_modelo": "{}",
        "n_estimators": 500,
    }

    relatorio = gerar_relatorio_markdown(janelas, metricas, detalhamento, decisoes, configuracao, metadados)

    assert "modelo atual é mantido" in relatorio
    assert "quantile_060" in relatorio and "quantile_080" in relatorio


def test_relatorio_recomenda_candidato_aprovado_vs_modelo_atual() -> None:
    metricas = _metricas_protocolo_sinteticas()
    configuracao = ConfiguracaoProtocolo()
    decisoes = calcular_decisoes(metricas, configuracao)
    janelas = pd.DataFrame(
        {
            "janela_id": ["janela_001", "janela_002", "janela_003", "janela_004"],
            "inicio_treino": ["2024-01-01"] * 4,
            "fim_treino": ["2024-12-30"] * 4,
            "inicio_avaliacao": ["2024-12-31"] * 4,
            "fim_avaliacao": ["2025-01-06"] * 4,
        }
    )
    detalhamento = pd.concat(
        [
            pd.DataFrame(
                {
                    "janela_id": ["janela_001", "janela_001"],
                    "candidato": [nome] * 2,
                    "medicamento_id": ["med_a", "med_b"],
                    "custo_compras_emergenciais_reais": [10.0, 20.0],
                }
            )
            for nome in ["modelo_atual", "quantile_060", "quantile_080"]
        ],
        ignore_index=True,
    )
    metadados = {
        "commit": "abc1234",
        "hash_consumo_medicamentos": "deadbeef",
        "versoes": "{}",
        "hiperparametros_modelo": "{}",
        "n_estimators": 500,
    }

    relatorio = gerar_relatorio_markdown(janelas, metricas, detalhamento, decisoes, configuracao, metadados)

    assert "quantile_060" in relatorio
    assert "atende(m) ao critério de aprovação" in relatorio


def test_secao_sensibilidade_conta_pares_com_custo_diferente_do_modelo_atual() -> None:
    detalhamento = pd.concat(
        [
            pd.DataFrame(
                {
                    "janela_id": ["janela_001", "janela_002"],
                    "medicamento_id": ["med_a", "med_a"],
                    "candidato": ["modelo_atual"] * 2,
                    "custo_compras_emergenciais_reais": [10.0, 20.0],
                }
            ),
            pd.DataFrame(
                {
                    "janela_id": ["janela_001", "janela_002"],
                    "medicamento_id": ["med_a", "med_a"],
                    "candidato": ["quantile_060"] * 2,
                    # janela_001 igual (nao mudou), janela_002 diferente (mudou).
                    "custo_compras_emergenciais_reais": [10.0, 5.0],
                }
            ),
            pd.DataFrame(
                {
                    "janela_id": ["janela_001", "janela_002"],
                    "medicamento_id": ["med_a", "med_a"],
                    "candidato": ["quantile_080"] * 2,
                    "custo_compras_emergenciais_reais": [10.0, 20.0],
                }
            ),
        ],
        ignore_index=True,
    )

    texto = "\n".join(_secao_sensibilidade(detalhamento))

    assert "| quantile_060 | 1 | 2 |" in texto
    assert "| quantile_080 | 0 | 2 |" in texto


def test_tabela_markdown_formata_numeros_com_o_padrao_informado() -> None:
    df = pd.DataFrame({"medicamento_id": ["med_a"], "diferenca_custo_reais": [12.345]})
    tabela = _tabela_markdown(df, formato={"diferenca_custo_reais": "+.2f"})

    assert "+12.35" in tabela


def _impacto_mes(candidato: str, custo: float, episodios: float = 5.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "candidato": [candidato],
            "medicamento_id": ["med_a"],
            "episodios_ruptura": [episodios],
            "unidades_em_ruptura": [10.0],
            "custo_compras_emergenciais_reais": [custo],
            "unidades_vencidas": [0.0],
        }
    )


def test_secao_simulacao_continua_mostra_reducao_real_quando_candidato_economiza() -> None:
    resultados_mensais = {
        "10": pd.concat(
            [
                _impacto_mes("modelo_atual", custo=100.0),
                _impacto_mes("quantile_060", custo=80.0),  # 20% de reducao
                _impacto_mes("quantile_080", custo=100.0),  # sem mudanca
            ],
            ignore_index=True,
        ),
    }

    texto = "\n".join(_secao_simulacao_continua(resultados_mensais))

    assert "quantile_060 vs. modelo atual" in texto
    assert "20.0%" in texto
    assert "Não substitui a decisão formal do protocolo #77" in texto


def test_relatorio_inclui_simulacao_continua_quando_fornecida() -> None:
    metricas = _metricas_protocolo_sinteticas()
    configuracao = ConfiguracaoProtocolo()
    decisoes = calcular_decisoes(metricas, configuracao)
    janelas = pd.DataFrame(
        {
            "janela_id": ["janela_001", "janela_002", "janela_003", "janela_004"],
            "inicio_treino": ["2024-01-01"] * 4,
            "fim_treino": ["2024-12-30"] * 4,
            "inicio_avaliacao": ["2024-12-31"] * 4,
            "fim_avaliacao": ["2025-01-06"] * 4,
        }
    )
    detalhamento = pd.concat(
        [
            pd.DataFrame(
                {
                    "janela_id": ["janela_001", "janela_001"],
                    "candidato": [nome] * 2,
                    "medicamento_id": ["med_a", "med_b"],
                    "custo_compras_emergenciais_reais": [10.0, 20.0],
                }
            )
            for nome in ["modelo_atual", "quantile_060", "quantile_080"]
        ],
        ignore_index=True,
    )
    metadados = {
        "commit": "abc1234",
        "hash_consumo_medicamentos": "deadbeef",
        "versoes": "{}",
        "hiperparametros_modelo": "{}",
        "n_estimators": 500,
    }
    resultados_mensais = {"10": pd.concat([_impacto_mes("modelo_atual", 100.0), _impacto_mes("quantile_060", 80.0), _impacto_mes("quantile_080", 100.0)], ignore_index=True)}

    relatorio_sem = gerar_relatorio_markdown(janelas, metricas, detalhamento, decisoes, configuracao, metadados)
    relatorio_com = gerar_relatorio_markdown(
        janelas, metricas, detalhamento, decisoes, configuracao, metadados, resultados_mensais
    )

    assert "Simulação contínua complementar" not in relatorio_sem
    assert "Simulação contínua complementar" in relatorio_com


def test_candidatos_promissores_exige_reducao_minima_em_todos_os_meses() -> None:
    resultados_mensais = {
        "10": pd.concat(
            [_impacto_mes("modelo_atual", 100.0), _impacto_mes("quantile_060", 85.0), _impacto_mes("quantile_080", 60.0)],
            ignore_index=True,
        ),
        "11": pd.concat(
            [_impacto_mes("modelo_atual", 100.0), _impacto_mes("quantile_060", 60.0), _impacto_mes("quantile_080", 65.0)],
            ignore_index=True,
        ),
    }

    promissores = _candidatos_promissores_na_simulacao_continua(resultados_mensais)

    # quantile_060: 15% no mes 10 (abaixo dos 10%? nao, 15%>=10% ok), 40% no mes 11 -> promissor
    # quantile_080: 40% no mes 10, 35% no mes 11 -> promissor tambem
    assert set(promissores) == {"quantile_060", "quantile_080"}


def test_candidatos_promissores_exclui_quem_falha_em_um_unico_mes() -> None:
    resultados_mensais = {
        "10": pd.concat(
            [_impacto_mes("modelo_atual", 100.0), _impacto_mes("quantile_060", 60.0), _impacto_mes("quantile_080", 60.0)],
            ignore_index=True,
        ),
        "11": pd.concat(
            [_impacto_mes("modelo_atual", 100.0), _impacto_mes("quantile_060", 95.0), _impacto_mes("quantile_080", 60.0)],
            ignore_index=True,
        ),
    }

    promissores = _candidatos_promissores_na_simulacao_continua(resultados_mensais)

    assert promissores == ["quantile_080"]


def test_relatorio_recomendacao_cita_candidato_promissor_na_simulacao_continua() -> None:
    metricas = pd.concat(
        [
            _metricas_candidato("baseline", [100.0] * 4),
            _metricas_candidato("modelo_atual", [90.0] * 4),
            _metricas_candidato("quantile_060", [95.0] * 4),
            _metricas_candidato("quantile_080", [88.0] * 4),
        ],
        ignore_index=True,
    )
    configuracao = ConfiguracaoProtocolo()
    decisoes = calcular_decisoes(metricas, configuracao)
    janelas = pd.DataFrame(
        {
            "janela_id": ["janela_001", "janela_002", "janela_003", "janela_004"],
            "inicio_treino": ["2024-01-01"] * 4,
            "fim_treino": ["2024-12-30"] * 4,
            "inicio_avaliacao": ["2024-12-31"] * 4,
            "fim_avaliacao": ["2025-01-06"] * 4,
        }
    )
    detalhamento = pd.concat(
        [
            pd.DataFrame(
                {
                    "janela_id": ["janela_001", "janela_001"],
                    "candidato": [nome] * 2,
                    "medicamento_id": ["med_a", "med_b"],
                    "custo_compras_emergenciais_reais": [10.0, 20.0],
                }
            )
            for nome in ["modelo_atual", "quantile_060", "quantile_080"]
        ],
        ignore_index=True,
    )
    metadados = {
        "commit": "abc1234",
        "hash_consumo_medicamentos": "deadbeef",
        "versoes": "{}",
        "hiperparametros_modelo": "{}",
        "n_estimators": 500,
    }
    # Ambas as decisoes formais (vs baseline e vs modelo atual) rejeitam --
    # nenhum candidato bate os 90/95/88 exigidos -- entao a recomendacao usa
    # o ramo "nenhum aprovado", que deve citar o achado da simulacao continua.
    resultados_mensais = {
        "10": pd.concat(
            [_impacto_mes("modelo_atual", 100.0), _impacto_mes("quantile_060", 95.0), _impacto_mes("quantile_080", 60.0)],
            ignore_index=True,
        ),
    }

    relatorio = gerar_relatorio_markdown(
        janelas, metricas, detalhamento, decisoes, configuracao, metadados, resultados_mensais
    )

    assert "quantile_080" in relatorio
    assert "revalidar formalmente com o protocolo #77" in relatorio
