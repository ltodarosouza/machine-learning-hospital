"""Testes da fonte de dados da visualização de previsão da Issue #21."""

import pandas as pd

from dashboard.app import carregar_dados_previsao


def test_carregar_dados_previsao_retorna_series_e_metricas(monkeypatch) -> None:
    """O dashboard combina as três séries e preserva os métodos das métricas."""
    import src.evaluation.comparar_modelos as avaliacao
    import src.models.modelo_demanda as modelo_demanda

    datas = pd.date_range("2025-01-01", periods=7, freq="D").date.astype(str)

    def prever_baseline_falso(*args, **kwargs) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "medicamento_id": "med_a",
                "data_previsao": datas,
                "demanda_prevista": [8.0] * 7,
                "consumo_unidades": [10.0] * 7,
                "metodo": "baseline",
            }
        )

    argumentos_modelo = {}

    def prever_modelo_falso(*args, **kwargs) -> pd.DataFrame:
        argumentos_modelo.update(kwargs)
        return pd.DataFrame(
            {
                "medicamento_id": "med_a",
                "data_previsao": datas,
                "demanda_prevista": [9.0] * 7,
                "consumo_unidades": [10.0] * 7,
            }
        )

    monkeypatch.setattr(avaliacao, "avaliar_baseline_periodo", prever_baseline_falso)
    monkeypatch.setattr(modelo_demanda, "avaliar_validacao_temporal", prever_modelo_falso)
    carregar_dados_previsao.clear()
    grafico, metricas = carregar_dados_previsao()

    assert {"Consumo real", "Baseline", "Modelo ML"} == set(grafico["serie"])
    assert set(grafico["medicamento_id"]) == {"med_a"}
    assert set(metricas["metodo"]) == {"baseline", "modelo_ml"}
    assert (metricas["mae"] >= 0).all()
    assert "n_estimators" not in argumentos_modelo
