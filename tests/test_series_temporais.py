"""Testes das features temporais implementadas na Issue #8."""

import pandas as pd

from src.features.series_temporais import gerar_features_series_temporais


def test_gera_lags_e_medias_moveis_por_medicamento_sem_vazamento() -> None:
    """Features usam apenas histórico do próprio medicamento."""
    linhas = []
    for medicamento, base in (("med_a", 0), ("med_b", 100)):
        for dia in range(1, 32):
            linhas.append(
                {
                    "data": pd.Timestamp("2025-01-01") + pd.Timedelta(days=dia - 1),
                    "medicamento_id": medicamento,
                    "consumo_unidades": float(base + dia),
                }
            )

    saida = gerar_features_series_temporais(
        pd.DataFrame(linhas).sample(frac=1, random_state=42)
    )
    med_a = saida[saida["medicamento_id"] == "med_a"].reset_index(drop=True)
    med_b = saida[saida["medicamento_id"] == "med_b"].reset_index(drop=True)

    assert pd.isna(med_a.loc[0, "feat_lag_1d"])
    assert med_a.loc[1, "feat_lag_1d"] == 1.0
    assert med_a.loc[7, "feat_lag_7d"] == 1.0
    assert med_a.loc[7, "feat_media_movel_7d"] == 4.0
    assert med_a.loc[30, "feat_media_movel_30d"] == 15.5
    assert med_b.loc[1, "feat_lag_1d"] == 101.0
