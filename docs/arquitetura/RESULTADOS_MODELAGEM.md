# Resultados da comparação baseline vs. modelo de ML (Issue #13)

Período de teste: 2025-12-04 a 2025-12-31. Nenhum dos dois métodos viu dado desse período durante o treino/cálculo — o baseline usa só a janela móvel anterior a cada corte, o modelo é retreinado do zero a cada janela usando só `data <= corte`.

Dataset de treino/teste: `data/processed/consumo_medicamentos.csv`, período 2022-01-01 a 2025-12-31 (ver `src/utils/config.py`). **Este relatório é gerado do zero a cada execução de `comparar_modelos.py`** — os números não são comparáveis com versões anteriores deste arquivo se o dataset ou os hiperparâmetros do modelo mudaram entre execuções (ver histórico de melhorias em `src/models/README.md`).

## Resultado agregado (todos os 20 medicamentos)

| Método | MAE (unidades/dia) | MAPE (%) |
|---|---|---|
| Baseline (média móvel) | 10.62 | 19.2% |
| Modelo de ML | 10.42 | 19.1% |

**O modelo de ML reduziu o erro (MAE) em 1.9% frente ao baseline.**

## Detalhamento por medicamento

| Medicamento | MAE baseline | MAE modelo | MAPE baseline | MAPE modelo | Modelo venceu? |
|---|---|---|---|---|---|
| adrenalina_inj | 2.02 | 2.27 | 41.9% | 45.6% | Não |
| amoxicilina | 7.60 | 7.88 | 16.0% | 16.0% | Não |
| azitromicina | 6.83 | 7.00 | 14.8% | 14.8% | Não |
| ceftriaxona_inj | 6.63 | 6.30 | 17.4% | 16.0% | Sim |
| diazepam | 3.66 | 3.74 | 23.1% | 23.6% | Não |
| diclofenaco | 11.95 | 11.80 | 21.3% | 21.2% | Sim |
| dipirona | 27.54 | 25.01 | 11.1% | 10.1% | Sim |
| hidrocortisona_inj | 5.72 | 5.41 | 19.3% | 18.4% | Sim |
| ibuprofeno | 11.81 | 12.12 | 12.2% | 12.7% | Não |
| loratadina | 8.09 | 7.71 | 23.7% | 21.4% | Sim |
| metoclopramida | 7.84 | 7.89 | 17.7% | 18.2% | Não |
| omeprazol_inj | 7.44 | 7.36 | 21.6% | 21.5% | Sim |
| ondansetrona | 6.86 | 7.55 | 19.5% | 22.9% | Não |
| paracetamol | 24.95 | 23.66 | 13.1% | 12.4% | Sim |
| predinisolona | 10.69 | 9.66 | 21.8% | 18.7% | Sim |
| salbutamol | 16.27 | 16.16 | 22.1% | 21.4% | Sim |
| soro_antitermico_infantil | 15.70 | 13.33 | 26.0% | 21.4% | Sim |
| soro_fisiologico | 18.35 | 19.98 | 12.8% | 14.6% | Não |
| soro_ringer | 9.06 | 9.97 | 12.6% | 13.8% | Não |
| tramadol | 3.45 | 3.51 | 16.3% | 17.1% | Não |

## Reprodutibilidade

- **Commit:** `d893bf3`
- **Período avaliado:** 2025-12-04 a 2025-12-31 (dataset completo: 2022-01-01 a 2025-12-31)
- **Baseline:** média móvel de 14 dias (`src/models/baseline.py::prever_baseline`)
- **Modelo de ML:** XGBoost (`XGBRegressor`, `max_depth=5, learning_rate=0.1, n_estimators=500, subsample=0.8, colsample_bytree=0.8`, `random_state=42`) — ver `src/models/modelo_demanda.py::treinar_modelo`
- **Comando para regenerar este relatório:** `python src/evaluation/comparar_modelos.py`
