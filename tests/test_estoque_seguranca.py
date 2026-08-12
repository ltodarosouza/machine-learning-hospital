import math

import numpy as np
import pandas as pd
import pytest

from src.recommendation.estoque_seguranca import calcular_estoque_seguranca


def test_calcula_estoque_por_variabilidade_e_prazo_de_entrega():
    consumo = pd.DataFrame(
        {
            "medicamento_id": [
                "paracetamol",
                "paracetamol",
                "paracetamol",
                "adrenalina",
            ],
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


@pytest.mark.parametrize(
    "coluna,valor",
    [
        ("consumo_unidades", float("nan")),
        ("consumo_unidades", float("inf")),
        ("consumo_unidades", float("-inf")),
        ("consumo_unidades", "invalido"),
        ("consumo_unidades", True),
        ("prazo_entrega_dias", float("nan")),
        ("prazo_entrega_dias", float("inf")),
        ("prazo_entrega_dias", float("-inf")),
        ("prazo_entrega_dias", "invalido"),
        ("prazo_entrega_dias", True),
    ],
)
def test_rejeita_campos_numericos_invalidos(coluna, valor):
    consumo = pd.DataFrame({"medicamento_id": ["a"], "consumo_unidades": [1]})
    referencias = pd.DataFrame({"medicamento_id": ["a"], "prazo_entrega_dias": [1]})
    alvo = consumo if coluna == "consumo_unidades" else referencias
    alvo[coluna] = pd.Series([valor], dtype=object)

    erro = TypeError if valor is True else ValueError
    with pytest.raises(erro, match=coluna):
        calcular_estoque_seguranca(consumo, referencias)


@pytest.mark.parametrize(
    "valor,erro",
    [
        (None, TypeError),
        (float("inf"), ValueError),
        (float("-inf"), ValueError),
        (-1, ValueError),
        (True, TypeError),
        ("1.65", TypeError),
    ],
)
def test_rejeita_fator_seguranca_invalido(valor, erro):
    consumo = pd.DataFrame({"medicamento_id": ["a"], "consumo_unidades": [1]})
    referencias = pd.DataFrame({"medicamento_id": ["a"], "prazo_entrega_dias": [1]})

    with pytest.raises(erro, match="fator_seguranca"):
        calcular_estoque_seguranca(consumo, referencias, fator_seguranca=valor)


def test_rejeita_entradas_que_nao_sao_dataframes():
    df = pd.DataFrame({"medicamento_id": ["a"], "consumo_unidades": [1]})
    referencia = pd.DataFrame({"medicamento_id": ["a"], "prazo_entrega_dias": [1]})
    with pytest.raises(TypeError, match="consumo_historico"):
        calcular_estoque_seguranca([], referencia)
    with pytest.raises(TypeError, match="medicamentos_referencia"):
        calcular_estoque_seguranca(df, {})


@pytest.mark.parametrize("valor", [None, "", "   "])
def test_rejeita_identificador_ausente_ou_vazio(valor):
    consumo = pd.DataFrame({"medicamento_id": [valor], "consumo_unidades": [1]})
    referencias = pd.DataFrame({"medicamento_id": ["a"], "prazo_entrega_dias": [1]})

    with pytest.raises(ValueError, match="medicamento_id"):
        calcular_estoque_seguranca(consumo, referencias)


def test_rejeita_referencia_sem_historico_e_historico_sem_referencia():
    consumo = pd.DataFrame({"medicamento_id": ["a"], "consumo_unidades": [1]})
    referencias = pd.DataFrame(
        {"medicamento_id": ["a", "b"], "prazo_entrega_dias": [1, 1]}
    )
    with pytest.raises(ValueError, match="sem histórico"):
        calcular_estoque_seguranca(consumo, referencias)

    consumo_extra = pd.concat(
        [consumo, pd.DataFrame({"medicamento_id": ["b"], "consumo_unidades": [2]})]
    )
    with pytest.raises(ValueError, match="sem medicamento na referência"):
        calcular_estoque_seguranca(consumo_extra, referencias.iloc[[0]])


def test_rejeita_referencia_duplicada_e_preserva_entradas():
    consumo = pd.DataFrame({"medicamento_id": ["a", "a"], "consumo_unidades": [1, 2]})
    referencias = pd.DataFrame(
        {"medicamento_id": ["a", "a"], "prazo_entrega_dias": [1, 2]}
    )
    with pytest.raises(ValueError, match="um prazo por medicamento"):
        calcular_estoque_seguranca(consumo, referencias)

    referencias = referencias.iloc[[0]].copy()
    copia_consumo = consumo.copy(deep=True)
    copia_referencias = referencias.copy(deep=True)
    calcular_estoque_seguranca(consumo, referencias)
    pd.testing.assert_frame_equal(consumo, copia_consumo)
    pd.testing.assert_frame_equal(referencias, copia_referencias)


@pytest.mark.parametrize("tabela", ["consumo", "referencia"])
@pytest.mark.parametrize("identificador", [1, True, " a", "a "])
def test_rejeita_identificador_fora_do_contrato(tabela, identificador):
    consumo = pd.DataFrame({"medicamento_id": ["a"], "consumo_unidades": [1]})
    referencias = pd.DataFrame({"medicamento_id": ["a"], "prazo_entrega_dias": [1]})
    (consumo if tabela == "consumo" else referencias)["medicamento_id"] = [
        identificador
    ]

    with pytest.raises((TypeError, ValueError), match="medicamento_id"):
        calcular_estoque_seguranca(consumo, referencias)


def test_rejeita_overflow_no_calculo_do_estoque_seguranca():
    consumo = pd.DataFrame(
        {"medicamento_id": ["a", "a"], "consumo_unidades": [0, 1e308]}
    )
    referencias = pd.DataFrame({"medicamento_id": ["a"], "prazo_entrega_dias": [1e308]})

    with pytest.raises(ValueError, match="valor não finito"):
        calcular_estoque_seguranca(consumo, referencias, fator_seguranca=1e308)


def test_calculo_em_escala_confere_com_formula_independente():
    rng = np.random.default_rng(20260812)
    medicamentos = [f"med_{indice:02d}" for indice in range(20)]
    linhas_consumo = []
    linhas_referencia = []
    esperados = {}
    fator = 1.65

    for medicamento in medicamentos:
        consumos = rng.uniform(0, 100, size=60)
        prazo = int(rng.integers(0, 15))
        linhas_consumo.extend((medicamento, valor) for valor in consumos)
        linhas_referencia.append((medicamento, prazo))
        esperados[medicamento] = math.ceil(
            np.std(consumos, ddof=0) * fator * math.sqrt(prazo)
        )

    consumo = pd.DataFrame(
        linhas_consumo, columns=["medicamento_id", "consumo_unidades"]
    )
    referencias = pd.DataFrame(
        linhas_referencia, columns=["medicamento_id", "prazo_entrega_dias"]
    )

    resultado = calcular_estoque_seguranca(consumo, referencias, fator).set_index(
        "medicamento_id"
    )

    assert resultado["estoque_seguranca"].to_dict() == esperados
