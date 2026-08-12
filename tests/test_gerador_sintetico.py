"""Testes do gerador sintético (Issues #53, #58, #59, #60 e #61)."""

import inspect
import numpy as np
import pandas as pd
import pytest

from src.data_ingestion.gerar_dataset_sintetico import (
    CATEGORIAS_PERFIL_CONTINUO,
    CATEGORIAS_PERFIL_ERRATICO,
    ESTADOS_SURTO,
    MULTIPLICADOR_SURTO,
    PERFIS_PERSISTENCIA,
    TOLERANCIA_INVENTARIO_UNIDADES,
    _distribuir_quantidade_inteira,
    _perfil_persistencia_por_categoria,
    fator_surto,
    gerar_consumo_diario,
    gerar_estado_surto,
    gerar_ruido_ar1,
    gerar_sinais_internos,
    montar_medicamentos_ref,
    simular_estoque,
    validar_consumo_diario,
    validar_lotes,
)


def _medicamentos_ref() -> pd.DataFrame:
    return pd.DataFrame({"medicamento_id": ["med_a", "med_b"]})


def _consumo_diario(estoque_final_a: float, estoque_final_b: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "medicamento_id": ["med_a", "med_a", "med_b", "med_b"],
            "data": ["2025-12-30", "2025-12-31", "2025-12-30", "2025-12-31"],
            "estoque_disponivel": [estoque_final_a + 5, estoque_final_a, estoque_final_b + 5, estoque_final_b],
        }
    )


def _externos(n_dias: int = 90) -> pd.DataFrame:
    datas = pd.date_range("2025-01-01", periods=n_dias, freq="D")
    return pd.DataFrame(
        {
            "data": datas,
            "temperatura_media": np.linspace(24, 29, n_dias),
            "chuva_mm": np.tile([0.0, 4.0, 12.0], n_dias // 3),
            "casos_dengue_regiao": np.linspace(10, 40, n_dias),
            "feriado": np.zeros(n_dias, dtype=bool),
        }
    )


def test_atendimentos_sao_gerados_sem_consumo_como_entrada() -> None:
    assert "consumo_diario" not in inspect.signature(gerar_sinais_internos).parameters

    externos = _externos()
    sinais_1 = gerar_sinais_internos(externos, np.random.default_rng(42))
    sinais_2 = gerar_sinais_internos(externos, np.random.default_rng(42))

    pd.testing.assert_frame_equal(sinais_1, sinais_2)
    assert list(sinais_1.columns) == ["data", "atendimentos_ps", "ocupacao_leitos_pct"]
    assert (sinais_1["atendimentos_ps"] >= 30).all()
    assert sinais_1["ocupacao_leitos_pct"].between(20, 100).all()


def test_consumo_usa_atendimentos_gerados_antes_dele() -> None:
    externos = _externos()
    medicamentos = montar_medicamentos_ref().query("medicamento_id == 'ibuprofeno'").copy()
    sinais = gerar_sinais_internos(externos, np.random.default_rng(42))
    sinais_altos = sinais.copy()
    sinais_altos["atendimentos_ps"] *= 2

    consumo_normal = gerar_consumo_diario(externos, medicamentos, np.random.default_rng(7), sinais)
    consumo_alto = gerar_consumo_diario(externos, medicamentos, np.random.default_rng(7), sinais_altos)

    assert consumo_alto["consumo_unidades"].mean() > consumo_normal["consumo_unidades"].mean() * 1.5


def test_validar_lotes_aceita_soma_igual_ao_estoque() -> None:
    lotes = pd.DataFrame(
        {
            "medicamento_id": ["med_a", "med_a", "med_b"],
            "quantidade_atual": [60.0, 40.0, 30.0],
            "data_entrada": ["2025-11-01"] * 3,
            "data_validade": ["2026-06-01"] * 3,
        }
    )
    # não deve levantar exceção: soma de med_a = 100 (bate), soma de med_b = 30 (bate)
    validar_lotes(lotes, _medicamentos_ref(), _consumo_diario(100.0, 30.0))


def test_validar_lotes_rejeita_divergencia_alem_da_tolerancia() -> None:
    lotes = pd.DataFrame(
        {
            "medicamento_id": ["med_a"],
            "quantidade_atual": [500.0],  # bem acima do estoque real (100)
            "data_entrada": ["2025-11-01"],
            "data_validade": ["2026-06-01"],
        }
    )
    with pytest.raises(ValueError, match="diverge de estoque_disponivel"):
        validar_lotes(lotes, _medicamentos_ref(), _consumo_diario(100.0, 30.0))


def test_validar_lotes_aceita_divergencia_dentro_da_tolerancia_de_arredondamento() -> None:
    lotes = pd.DataFrame(
        {
            "medicamento_id": ["med_a"],
            "quantidade_atual": [100.0 + TOLERANCIA_INVENTARIO_UNIDADES],
            "data_entrada": ["2025-11-01"],
            "data_validade": ["2026-06-01"],
        }
    )
    validar_lotes(lotes, pd.DataFrame({"medicamento_id": ["med_a"]}), _consumo_diario(100.0, 0.0))


@pytest.mark.parametrize(
    "total,pesos",
    [
        (100.0, np.array([0.5, 0.3, 0.2])),
        (101.0, np.array([1 / 3, 1 / 3, 1 / 3])),
        (0.0, np.array([0.5, 0.5])),
        (7.0, np.array([0.9, 0.1])),
    ],
)
def test_distribuir_quantidade_inteira_preserva_a_soma_exata(total: float, pesos: np.ndarray) -> None:
    quantidades = _distribuir_quantidade_inteira(total, pesos)
    assert quantidades.sum() == round(total)
    assert (quantidades >= 0).all()


def test_estado_surto_tem_duracao_de_dias_nao_de_um_dia() -> None:
    """Prova que o estado latente tem memória: episódios fora do 'normal' duram
    tipicamente de 1 a 4 semanas (7-28 dias), não são só ruído independente
    a cada dia (essa era a limitação que motivou a Issue #58)."""
    rng = np.random.default_rng(123)
    estados = gerar_estado_surto(1461 * 5, rng)  # amostra grande para estatística estável

    fora_do_normal = estados != 0
    mudancas = np.diff(np.concatenate(([0], fora_do_normal.astype(int), [0])))
    inicios = np.where(mudancas == 1)[0]
    fins = np.where(mudancas == -1)[0]
    duracoes = fins - inicios

    assert len(duracoes) > 10, "poucos episódios gerados para uma amostra dessa dimensão."
    assert 7 <= duracoes.mean() <= 28, f"duração média do episódio ({duracoes.mean():.1f}d) fora da faixa de 1 a 4 semanas."
    # se fosse ruído i.i.d., quase todo episódio duraria exatamente 1 dia — não é o caso aqui.
    assert (duracoes > 1).mean() > 0.5, "maioria dos episódios durou só 1 dia — isso seria ruído, não memória."


def test_gerar_estado_surto_e_reprodutivel_com_a_mesma_seed() -> None:
    estados_1 = gerar_estado_surto(200, np.random.default_rng(42))
    estados_2 = gerar_estado_surto(200, np.random.default_rng(42))
    assert (estados_1 == estados_2).all()


def test_fator_surto_mapeia_estado_para_multiplicador_correto() -> None:
    estados = np.array([0, 1, 2, 0, 2])
    fatores = fator_surto(estados)
    esperado = np.array(
        [MULTIPLICADOR_SURTO[ESTADOS_SURTO[e]] for e in estados]
    )
    assert (fatores == esperado).all()
    assert fatores[0] == 1.0  # normal não altera a média-base
    assert fatores[4] > fatores[1] > fatores[0]  # surto > elevado > normal


def _autocorrelacao_lag1(serie: np.ndarray) -> float:
    log_serie = np.log(serie)
    return float(np.corrcoef(log_serie[:-1], log_serie[1:])[0, 1])


@pytest.mark.parametrize("perfil", ["continuo", "intermitente", "erratico"])
def test_ruido_ar1_tem_autocorrelacao_proxima_do_phi_alvo(perfil: str) -> None:
    params = PERFIS_PERSISTENCIA[perfil]
    ruido = gerar_ruido_ar1(3000, params["phi"], params["sigma_estacionario"], np.random.default_rng(7))
    autocorrelacao = _autocorrelacao_lag1(ruido)
    assert abs(autocorrelacao - params["phi"]) < 0.05, (
        f"autocorrelação empírica ({autocorrelacao:.3f}) longe do phi alvo ({params['phi']})."
    )


def test_perfis_de_persistencia_tem_memoria_em_ordem_crescente() -> None:
    """Critério de aceite explícito da Issue #61: contínuo e intermitente
    devem ter mais memória de curto prazo que errático."""
    autocorrelacoes = {}
    for perfil, params in PERFIS_PERSISTENCIA.items():
        ruido = gerar_ruido_ar1(3000, params["phi"], params["sigma_estacionario"], np.random.default_rng(7))
        autocorrelacoes[perfil] = _autocorrelacao_lag1(ruido)

    assert autocorrelacoes["continuo"] > autocorrelacoes["intermitente"] > autocorrelacoes["erratico"]
    assert autocorrelacoes["erratico"] < 0.15  # praticamente sem memória, equivalente ao i.i.d. anterior


def test_ruido_ar1_e_reprodutivel_e_sempre_positivo() -> None:
    ruido_1 = gerar_ruido_ar1(500, 0.7, 0.12, np.random.default_rng(11))
    ruido_2 = gerar_ruido_ar1(500, 0.7, 0.12, np.random.default_rng(11))
    assert (ruido_1 == ruido_2).all()
    assert (ruido_1 > 0).all()


@pytest.mark.parametrize(
    "categoria,perfil_esperado",
    [
        ("Dor/febre", "continuo"),
        ("Suporte/hidratação", "continuo"),
        ("Emergência/controlado", "erratico"),
        ("Respiratório", "intermitente"),
        ("Gastro", "intermitente"),
        ("Categoria inexistente", "intermitente"),  # default seguro
    ],
)
def test_perfil_persistencia_por_categoria(categoria: str, perfil_esperado: str) -> None:
    assert _perfil_persistencia_por_categoria(categoria) == perfil_esperado


def test_medicamentos_ref_tem_perfil_de_persistencia_para_todos() -> None:
    ref = montar_medicamentos_ref()
    assert set(ref["_perfil_persistencia"]) <= set(PERFIS_PERSISTENCIA)
    assert ref["_perfil_persistencia"].notna().all()

    # categorias explicitamente mapeadas para continuo/erratico devem aparecer com esse perfil
    for categoria in CATEGORIAS_PERFIL_CONTINUO:
        if categoria in set(ref["categoria"]):
            assert (ref.loc[ref["categoria"] == categoria, "_perfil_persistencia"] == "continuo").all()
    for categoria in CATEGORIAS_PERFIL_ERRATICO:
        if categoria in set(ref["categoria"]):
            assert (ref.loc[ref["categoria"] == categoria, "_perfil_persistencia"] == "erratico").all()


def test_ruptura_censura_dispensacao_mas_preserva_demanda_latente() -> None:
    """A demanda existe mesmo sem saldo, mas não pode ser dispensada fisicamente."""
    demanda = pd.DataFrame(
        {
            "data": pd.date_range("2025-01-01", periods=5, freq="D").astype(str),
            "medicamento_id": ["med_a"] * 5,
            "consumo_unidades": [0.0, 10.0, 10.0, 10.0, 10.0],
        }
    )
    referencia = pd.DataFrame(
        {"medicamento_id": ["med_a"], "prazo_entrega_dias": [3]}
    )

    resultado = simular_estoque(demanda, referencia, np.random.default_rng(7))

    assert (resultado["dispensacao_unidades"] <= resultado["consumo_unidades"]).all()
    assert np.allclose(
        resultado["consumo_unidades"],
        resultado["dispensacao_unidades"] + resultado["demanda_nao_atendida"],
    )
    assert (resultado["demanda_nao_atendida"] > 0).any()
    assert (
        resultado.loc[resultado["demanda_nao_atendida"] > 0, "dispensacao_unidades"]
        == 0
    ).all()


def test_validar_consumo_diario_rejeita_balanco_de_demanda_invalido() -> None:
    datas = pd.date_range("2022-01-01", "2025-12-31", freq="D")
    consumo = pd.DataFrame(
        {
            "data": datas.astype(str),
            "medicamento_id": ["med_a"] * len(datas),
            "consumo_unidades": [10.0] * len(datas),
            "dispensacao_unidades": [7.0] * len(datas),
            "demanda_nao_atendida": [1.0] * len(datas),
            "entradas_unidades": [0.0] * len(datas),
            "estoque_disponivel": [0.0] * len(datas),
        }
    )
    referencia = pd.DataFrame({"medicamento_id": ["med_a"]})

    with pytest.raises(ValueError, match="dispensacao_unidades mais demanda_nao_atendida"):
        validar_consumo_diario(consumo, referencia)
