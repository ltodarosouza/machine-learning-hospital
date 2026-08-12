# Resultados da comparação baseline vs. modelo de ML (Issue #13)

Período de teste: 2025-12-04 a 2025-12-31. Nenhum dos dois métodos viu dado desse período durante o treino/cálculo — o baseline usa só a janela móvel anterior a cada corte, o modelo é retreinado do zero a cada janela usando só `data <= corte`.

## Metadados da execução

- Commit do código e dos dados avaliados: `66420a4d4073c54bc2d84e361e0995f8b21a9711`
- Dataset: `data/processed/consumo_medicamentos.csv` (2022-01-01 a 2025-12-31; 20 medicamentos, 1.461 dias)
- Avaliação: 4 janelas sucessivas de 7 dias, totalizando 560 previsões por método
- Baseline: média móvel simples dos 14 dias anteriores, projetada de forma flat por 7 dias
- Modelo: `XGBRegressor` compartilhado entre medicamentos e horizontes
- Ambiente: Python 3.14; `xgboost==3.4.0`
- Parâmetros do modelo: `n_estimators=500`, `max_depth=5`, `learning_rate=0.1`, `subsample=0.8`, `colsample_bytree=0.8`, `random_state=42`, `n_jobs=-1`
- Horizonte: 7 dias; `MAPE` calculado somente nos dias com consumo realizado maior que zero

Para regenerar este relatório no estado atual do repositório:

```bash
python src/evaluation/comparar_modelos.py
```

## Resultado agregado (todos os 20 medicamentos)

| Método | MAE (unidades/dia) | MAPE (%) |
|---|---|---|
| Baseline (média móvel) | 9.60 | 18.2% |
| Modelo de ML | 9.47 | 17.8% |

**O modelo de ML reduziu o erro (MAE) em 1.3% frente ao baseline.**

## Detalhamento por medicamento

| Medicamento | MAE baseline | MAE modelo | MAPE baseline | MAPE modelo | Modelo venceu? |
|---|---|---|---|---|---|
| adrenalina_inj | 2.02 | 2.19 | 41.9% | 41.2% | Não |
| amoxicilina | 7.60 | 7.74 | 16.0% | 15.6% | Não |
| azitromicina | 6.83 | 7.15 | 14.8% | 14.9% | Não |
| ceftriaxona_inj | 6.63 | 6.08 | 17.4% | 15.5% | Sim |
| diazepam | 3.66 | 3.72 | 23.1% | 23.3% | Não |
| diclofenaco | 11.95 | 11.77 | 21.3% | 21.2% | Sim |
| dipirona | 26.60 | 27.90 | 10.6% | 11.0% | Não |
| hidrocortisona_inj | 6.23 | 5.78 | 28.6% | 28.0% | Sim |
| ibuprofeno | 11.81 | 11.08 | 12.2% | 11.8% | Sim |
| loratadina | 5.15 | 5.06 | 20.1% | 19.6% | Sim |
| metoclopramida | 8.02 | 7.57 | 17.1% | 16.0% | Sim |
| omeprazol_inj | 7.44 | 7.36 | 21.6% | 21.1% | Sim |
| ondansetrona | 5.94 | 5.89 | 17.8% | 18.2% | Sim |
| paracetamol | 25.02 | 24.62 | 12.5% | 12.1% | Sim |
| predinisolona | 5.81 | 6.10 | 13.8% | 14.2% | Não |
| salbutamol | 7.33 | 7.50 | 11.7% | 12.0% | Não |
| soro_antitermico_infantil | 8.74 | 8.15 | 17.9% | 16.6% | Sim |
| soro_fisiologico | 19.69 | 19.12 | 13.3% | 13.0% | Sim |
| soro_ringer | 12.03 | 11.45 | 16.3% | 14.8% | Sim |
| tramadol | 3.45 | 3.21 | 16.3% | 15.8% | Sim |
