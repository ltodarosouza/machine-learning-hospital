"""Testes da invariante de inventário entre lotes e estoque (Issue #53)
e dos estados latentes persistentes de surto (Issue #58)."""

import numpy as np
import pandas as pd
import pytest

from src.data_ingestion.gerar_dataset_sintetico import (
    ESTADOS_SURTO,
    MULTIPLICADOR_SURTO,
    TOLERANCIA_INVENTARIO_UNIDADES,
    _distribuir_quantidade_inteira,
    fator_surto,
    gerar_estado_surto,
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
