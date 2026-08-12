# Resultados da comparação baseline vs. modelo de ML (Issue #13)

Período de teste: 2025-12-04 a 2025-12-31. Nenhum dos dois métodos viu dado desse período durante o treino/cálculo — o baseline usa só a janela móvel anterior a cada corte, o modelo é retreinado do zero a cada janela usando só `data <= corte`.

Dataset de treino/teste: `data/processed/consumo_medicamentos.csv`, período 2022-01-01 a 2025-12-31 (ver `src/utils/config.py`). **Este relatório é gerado do zero a cada execução de `comparar_modelos.py`** — os números não são comparáveis com versões anteriores deste arquivo se o dataset ou os hiperparâmetros do modelo mudaram entre execuções (ver histórico de melhorias em `src/models/README.md`).

## Resultado agregado (todos os 20 medicamentos)

| Método | MAE (unidades/dia) | MAPE (%) |
|---|---|---|
| Baseline (média móvel) | 9.60 | 18.2% |
| Modelo de ML | 9.43 | 17.9% |

**O modelo de ML reduziu o erro (MAE) em 1.8% frente ao baseline.**

## Detalhamento por medicamento

| Medicamento | MAE baseline | MAE modelo | MAPE baseline | MAPE modelo | Modelo venceu? |
|---|---|---|---|---|---|
| adrenalina_inj | 2.02 | 2.13 | 41.9% | 41.0% | Não |
| amoxicilina | 7.60 | 7.76 | 16.0% | 15.7% | Não |
| azitromicina | 6.83 | 7.14 | 14.8% | 14.9% | Não |
| ceftriaxona_inj | 6.63 | 6.27 | 17.4% | 15.9% | Sim |
| diazepam | 3.66 | 3.74 | 23.1% | 23.6% | Não |
| diclofenaco | 11.95 | 11.92 | 21.3% | 21.6% | Sim |
| dipirona | 26.60 | 26.55 | 10.6% | 10.5% | Sim |
| hidrocortisona_inj | 6.23 | 5.82 | 28.6% | 28.1% | Sim |
| ibuprofeno | 11.81 | 11.17 | 12.2% | 11.9% | Sim |
| loratadina | 5.15 | 4.97 | 20.1% | 19.4% | Sim |
| metoclopramida | 8.02 | 7.66 | 17.1% | 16.2% | Sim |
| omeprazol_inj | 7.44 | 7.48 | 21.6% | 21.5% | Não |
| ondansetrona | 5.94 | 5.96 | 17.8% | 18.4% | Não |
| paracetamol | 25.02 | 24.47 | 12.5% | 12.2% | Sim |
| predinisolona | 5.81 | 6.03 | 13.8% | 14.1% | Não |
| salbutamol | 7.33 | 7.49 | 11.7% | 12.2% | Não |
| soro_antitermico_infantil | 8.74 | 8.36 | 17.9% | 17.0% | Sim |
| soro_fisiologico | 19.69 | 19.00 | 13.3% | 12.9% | Sim |
| soro_ringer | 12.03 | 11.26 | 16.3% | 14.7% | Sim |
| tramadol | 3.45 | 3.31 | 16.3% | 16.3% | Sim |

## Reprodutibilidade

- **Commit:** `636a87f`
- **Período avaliado:** 2025-12-04 a 2025-12-31 (dataset completo: 2022-01-01 a 2025-12-31)
- **Baseline:** média móvel de 14 dias (`src/models/baseline.py::prever_baseline`)
- **Modelo de ML:** XGBoost (`XGBRegressor`, `max_depth=5, learning_rate=0.1, n_estimators=500, subsample=0.8, colsample_bytree=0.8`, `random_state=42`) — ver `src/models/modelo_demanda.py::treinar_modelo`
- **Comando para regenerar este relatório:** `python src/evaluation/comparar_modelos.py`
