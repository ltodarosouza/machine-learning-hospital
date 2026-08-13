# Resultados da comparação baseline vs. modelo de ML (Issue #13)

Período de teste: 2025-12-04 a 2025-12-31. Nenhum dos dois métodos viu dado desse período durante o treino/cálculo — o baseline usa só a janela móvel anterior a cada corte, o modelo é retreinado do zero a cada janela usando só `data <= corte`.

Dataset de treino/teste: `data/processed/consumo_medicamentos.csv`, período 2022-01-01 a 2025-12-31 (ver `src/utils/config.py`). **Este relatório é gerado do zero a cada execução de `comparar_modelos.py`** — os números não são comparáveis com versões anteriores deste arquivo se o dataset ou os hiperparâmetros do modelo mudaram entre execuções (ver histórico de melhorias em `src/models/README.md`).

## Resultado agregado (todos os 20 medicamentos)

| Método | MAE (unidades/dia) | MAPE (%) |
|---|---|---|
| Baseline (média móvel) | 15.52 | 22.7% |
| Modelo de ML | 14.22 | 23.2% |

**O modelo de ML reduziu o erro (MAE) em 8.4% frente ao baseline.**

## Detalhamento por medicamento

| Medicamento | MAE baseline | MAE modelo | MAPE baseline | MAPE modelo | Modelo venceu? |
|---|---|---|---|---|---|
| adrenalina_inj | 2.16 | 3.15 | 51.9% | 100.9% | Não |
| amoxicilina | 13.06 | 12.22 | 19.3% | 16.9% | Sim |
| azitromicina | 9.21 | 9.10 | 17.4% | 16.4% | Sim |
| ceftriaxona_inj | 10.18 | 7.15 | 21.3% | 14.5% | Sim |
| diazepam | 4.06 | 4.64 | 23.8% | 26.8% | Não |
| diclofenaco | 8.85 | 6.76 | 11.6% | 8.8% | Sim |
| dipirona | 51.11 | 42.34 | 15.5% | 13.1% | Sim |
| hidrocortisona_inj | 9.04 | 8.23 | 25.5% | 22.3% | Sim |
| ibuprofeno | 14.09 | 13.96 | 11.9% | 11.8% | Sim |
| loratadina | 13.53 | 11.42 | 36.0% | 25.2% | Sim |
| metoclopramida | 8.68 | 10.15 | 16.9% | 19.4% | Não |
| omeprazol_inj | 8.23 | 7.96 | 18.7% | 17.2% | Sim |
| ondansetrona | 7.06 | 7.98 | 20.1% | 23.3% | Não |
| paracetamol | 43.80 | 41.54 | 19.7% | 17.8% | Sim |
| predinisolona | 16.16 | 15.52 | 26.8% | 23.8% | Sim |
| salbutamol | 24.02 | 21.19 | 25.6% | 21.0% | Sim |
| soro_antitermico_infantil | 23.01 | 22.05 | 33.0% | 29.8% | Sim |
| soro_fisiologico | 21.44 | 19.32 | 13.2% | 11.9% | Sim |
| soro_ringer | 16.11 | 13.71 | 21.1% | 18.6% | Sim |
| tramadol | 6.63 | 5.92 | 25.1% | 24.6% | Sim |

## Reprodutibilidade

- **Commit:** `5b7f206`
- **Período avaliado:** 2025-12-04 a 2025-12-31 (dataset completo: 2022-01-01 a 2025-12-31)
- **Baseline:** média móvel de 14 dias (`src/models/baseline.py::prever_baseline`)
- **Modelo de ML:** XGBoost (`XGBRegressor`, `max_depth=7, learning_rate=0.1, n_estimators=500, subsample=0.8, colsample_bytree=0.8`, `random_state=42`) — ver `src/models/modelo_demanda.py::treinar_modelo`
- **Comando para regenerar este relatório:** `python src/evaluation/comparar_modelos.py`
