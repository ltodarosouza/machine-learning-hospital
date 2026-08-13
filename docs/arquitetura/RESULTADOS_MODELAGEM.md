# Resultados da comparação baseline vs. modelo de ML (Issue #13)

Período de teste: 2025-12-04 a 2025-12-31. Nenhum dos dois métodos viu dado desse período durante o treino/cálculo — o baseline usa só a janela móvel anterior a cada corte, o modelo é retreinado do zero a cada janela usando só `data <= corte`.

Dataset de treino/teste: `data/processed/consumo_medicamentos.csv`, período 2022-01-01 a 2025-12-31 (ver `src/utils/config.py`). **Este relatório é gerado do zero a cada execução de `comparar_modelos.py`** — os números não são comparáveis com versões anteriores deste arquivo se o dataset ou os hiperparâmetros do modelo mudaram entre execuções (ver histórico de melhorias em `src/models/README.md`).

## Resultado agregado (todos os 20 medicamentos)

| Método | MAE (unidades/dia) | MAPE (%) |
|---|---|---|
| Baseline (média móvel) | 15.52 | 22.7% |
| Modelo de ML | 14.69 | 23.3% |

**O modelo de ML reduziu o erro (MAE) em 5.3% frente ao baseline.**

## Detalhamento por medicamento

| Medicamento | MAE baseline | MAE modelo | MAPE baseline | MAPE modelo | Modelo venceu? |
|---|---|---|---|---|---|
| adrenalina_inj | 2.16 | 2.98 | 51.9% | 79.8% | Não |
| amoxicilina | 13.06 | 10.67 | 19.3% | 14.6% | Sim |
| azitromicina | 9.21 | 10.43 | 17.4% | 19.6% | Não |
| ceftriaxona_inj | 10.18 | 8.21 | 21.3% | 17.3% | Sim |
| diazepam | 4.06 | 4.65 | 23.8% | 28.3% | Não |
| diclofenaco | 8.85 | 7.84 | 11.6% | 9.7% | Sim |
| dipirona | 51.11 | 51.31 | 15.5% | 15.3% | Não |
| hidrocortisona_inj | 9.04 | 8.96 | 25.5% | 25.3% | Sim |
| ibuprofeno | 14.09 | 13.80 | 11.9% | 11.9% | Sim |
| loratadina | 13.53 | 12.37 | 36.0% | 28.4% | Sim |
| metoclopramida | 8.68 | 9.73 | 16.9% | 18.7% | Não |
| omeprazol_inj | 8.23 | 7.76 | 18.7% | 17.3% | Sim |
| ondansetrona | 7.06 | 8.86 | 20.1% | 26.8% | Não |
| paracetamol | 43.80 | 35.91 | 19.7% | 15.0% | Sim |
| predinisolona | 16.16 | 16.28 | 26.8% | 26.1% | Não |
| salbutamol | 24.02 | 23.12 | 25.6% | 23.3% | Sim |
| soro_antitermico_infantil | 23.01 | 24.90 | 33.0% | 33.8% | Não |
| soro_fisiologico | 21.44 | 16.36 | 13.2% | 10.4% | Sim |
| soro_ringer | 16.11 | 12.95 | 21.1% | 17.1% | Sim |
| tramadol | 6.63 | 6.78 | 25.1% | 27.9% | Não |

## Reprodutibilidade

- **Commit:** `a1658c1`
- **Período avaliado:** 2025-12-04 a 2025-12-31 (dataset completo: 2022-01-01 a 2025-12-31)
- **Baseline:** média móvel de 14 dias (`src/models/baseline.py::prever_baseline`)
- **Modelo de ML:** XGBoost (`XGBRegressor`, `max_depth=7, learning_rate=0.1, n_estimators=500, subsample=0.8, colsample_bytree=0.8`, `random_state=42`) — ver `src/models/modelo_demanda.py::treinar_modelo`
- **Comando para regenerar este relatório:** `python src/evaluation/comparar_modelos.py`
