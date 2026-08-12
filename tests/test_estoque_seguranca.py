import pandas as pd
import pytest

from src.recommendation.estoque_seguranca import calcular_estoque_seguranca


def test_calcula_estoque_por_variabilidade_e_prazo_de_entrega():
    consumo = pd.DataFrame(
        {
            "medicamento_id": ["paracetamol", "paracetamol", "paracetamol", "adrenalina"],
            "consumo_unidades": [10, 20, 30, 50],
        }
    )
    referencias = pd.DataFrame(
        {
            "medicamento_id": ["paracetamol", "adrenalina"],
            "prazo_entrega_dias": [4, 7],
        }
    )

    resultado = calcular_estoque_seguranca(consumo, referencias, fator_seguranca=1)

    paracetamol = resultado.set_index("medicamento_id").loc["paracetamol"]
    adrenalina = resultado.set_index("medicamento_id").loc["adrenalina"]
    assert paracetamol["desvio_padrao_consumo"] == pytest.approx(8.1649658)
    assert paracetamol["estoque_seguranca"] == 17
    assert adrenalina["desvio_padrao_consumo"] == 0
    assert adrenalina["estoque_seguranca"] == 0


def test_rejeita_consumo_negativo_e_prazo_invalido():
    consumo = pd.DataFrame({"medicamento_id": ["a"], "consumo_unidades": [-1]})
    referencias = pd.DataFrame({"medicamento_id": ["a"], "prazo_entrega_dias": [1]})
    with pytest.raises(ValueError, match="consumo_unidades"):
        calcular_estoque_seguranca(consumo, referencias)

    consumo.loc[0, "consumo_unidades"] = 1
    referencias.loc[0, "prazo_entrega_dias"] = -1
    with pytest.raises(ValueError, match="prazo_entrega_dias"):
        calcular_estoque_seguranca(consumo, referencias)
