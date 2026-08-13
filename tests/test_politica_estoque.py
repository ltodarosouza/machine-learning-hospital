import pandas as pd
import pytest

from src.evaluation.avaliacao_politica_estoque import consolidar_resultados_continuos
from src.recommendation.politica_estoque import (
    POLITICA_PERFIL_PRAZO_MODERADA,
    classificar_faixa_prazo,
    classificar_perfil_demanda,
)


def test_classifica_perfis_e_faixas_sem_regra_por_medicamento() -> None:
    referencia = pd.DataFrame(
        {
            "medicamento_id": ["a", "b", "c"],
            "categoria": ["Dor/febre", "Gastro", "Emergência/controlado"],
            "prazo_entrega_dias": [5, 7, 12],
        }
    )

    resultado = POLITICA_PERFIL_PRAZO_MODERADA.fatores_por_medicamento(referencia).set_index("medicamento_id")

    assert classificar_perfil_demanda("Dor/febre") == "continuo"
    assert classificar_perfil_demanda("Gastro") == "intermitente"
    assert classificar_perfil_demanda("Emergência/controlado") == "erratico"
    assert classificar_faixa_prazo(6) == "curto"
    assert classificar_faixa_prazo(7) == "longo"
    assert resultado.loc["a", "fator_seguranca"] == 0.10
    assert resultado.loc["b", "fator_seguranca"] == 0.35
    assert resultado.loc["c", "fator_seguranca"] == 0.50


@pytest.mark.parametrize("valor,erro", [(0, ValueError), (True, TypeError), ("7", TypeError)])
def test_rejeita_prazo_invalido(valor: object, erro: type[Exception]) -> None:
    with pytest.raises(erro):
        classificar_faixa_prazo(valor)  # type: ignore[arg-type]


def test_consolidado_continuo_compara_cada_politica_com_a_fixa_do_metodo() -> None:
    comum = {
        "episodios_ruptura": [10.0, 8.0],
        "unidades_em_ruptura": [20.0, 15.0],
        "compras_emergenciais_unidades": [20.0, 15.0],
        "custo_compras_emergenciais_reais": [100.0, 70.0],
        "unidades_vencidas": [0.0, 0.0],
        "quantidade_total_recomendada": [50.0, 55.0],
        "estoque_medio_unidades": [30.0, 40.0],
    }
    mes = pd.DataFrame({"metodo": ["modelo_atual", "modelo_atual"], "politica": ["fixa_020", "perfil_prazo_conservadora"], **comum})

    consolidado = consolidar_resultados_continuos({"10": mes}).set_index("politica")

    assert consolidado.loc["perfil_prazo_conservadora", "variacao_custo_compras_emergenciais_reais_pct"] == pytest.approx(-30.0)
    assert consolidado.loc["perfil_prazo_conservadora", "variacao_estoque_medio_unidades_pct"] == pytest.approx(100 / 3)
