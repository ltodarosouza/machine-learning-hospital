"""Testes da invariante de inventário entre lotes e estoque (Issue #53),
dos estados latentes persistentes de surto (Issue #58) e das classes de
persistência por medicamento (Issue #61)."""

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
    gerar_estado_surto,
    gerar_ruido_ar1,
    montar_medicamentos_ref,
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
