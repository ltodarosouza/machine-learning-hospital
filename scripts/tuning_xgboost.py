"""Grid search de hiperparâmetros do XGBoost, depois de `comparar_algoritmos_modelo.py`
ter escolhido esse algoritmo como o melhor entre os testados.

Reaproveita `avaliar_config` (mesma metodologia de validação temporal sem
vazamento: retreina do zero a cada janela de teste, só usa `data <= corte`).
Resultado documentado em `src/models/README.md`.

Uso:
    python scripts/tuning_xgboost.py
"""

import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO))

from scripts.comparar_algoritmos_modelo import avaliar_config
from src.utils.config import HORIZONTE_PREVISAO_DIAS
from xgboost import XGBRegressor

GRADE_HIPERPARAMETROS = [
    {"max_depth": md, "learning_rate": lr, "n_estimators": n_est}
    for md in (3, 5, 7)
    for lr in (0.03, 0.05, 0.1)
    for n_est in (300, 500)
]


def main() -> None:
    dados_brutos = pd.read_csv(REPO / "data" / "processed" / "consumo_medicamentos.csv")
    ultima_data = pd.to_datetime(dados_brutos["data"]).max()
    data_fim_teste = ultima_data.date().isoformat()
    data_inicio_teste = (ultima_data - pd.Timedelta(days=4 * HORIZONTE_PREVISAO_DIAS - 1)).date().isoformat()

    print(f"Período de teste: {data_inicio_teste} a {data_fim_teste}")
    print(f"{len(GRADE_HIPERPARAMETROS)} combinações de hiperparâmetros\n")

    resultados = []
    for params in GRADE_HIPERPARAMETROS:
        nome = f"max_depth={params['max_depth']} lr={params['learning_rate']} n_estimators={params['n_estimators']}"

        def construir_regressor(params=params):
            return XGBRegressor(
                max_depth=params["max_depth"],
                learning_rate=params["learning_rate"],
                n_estimators=params["n_estimators"],
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
            )

        mae, mape = avaliar_config(
            dados_brutos, data_inicio_teste, data_fim_teste, HORIZONTE_PREVISAO_DIAS, construir_regressor, excluir_ruido=True, nome=nome
        )
        resultados.append({**params, "mae": mae, "mape": mape})

    resultados_df = pd.DataFrame(resultados).sort_values("mae")
    print("\n=== TOP 5 (ordenado por MAE) ===")
    print(resultados_df.head(5).to_string(index=False))

    melhor = resultados_df.iloc[0]
    print(f"\nMelhor configuração: max_depth={int(melhor['max_depth'])}, learning_rate={melhor['learning_rate']}, n_estimators={int(melhor['n_estimators'])}")
    print(f"MAE={melhor['mae']:.3f} MAPE={melhor['mape']:.1f}%")


if __name__ == "__main__":
    main()
