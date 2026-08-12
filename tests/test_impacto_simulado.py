import pandas as pd

from src.evaluation.impacto_simulado import comparar_cenarios, simular_impacto


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
