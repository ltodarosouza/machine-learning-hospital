"""Testes da invariante de inventário entre lotes e estoque (Issue #53)."""

import numpy as np
import pandas as pd
import pytest

from src.data_ingestion.gerar_dataset_sintetico import (
    TOLERANCIA_INVENTARIO_UNIDADES,
    _distribuir_quantidade_inteira,
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
