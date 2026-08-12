# Resultados da comparação baseline vs. modelo de ML (Issue #13)

Período de teste: 2025-12-04 a 2025-12-31. Nenhum dos dois métodos viu dado desse período durante o treino/cálculo — o baseline usa só a janela móvel anterior a cada corte, o modelo é retreinado do zero a cada janela usando só `data <= corte`.

## Metadados da execução

- Commit do código e dos dados avaliados: `236673a0509edff95773fdcc4d41ed3819582012`
- Dataset: `data/processed/consumo_medicamentos.csv` (20 medicamentos, 731 dias)
- Avaliação: 4 janelas sucessivas de 7 dias, totalizando 560 previsões por método
- Baseline: média móvel simples dos 14 dias anteriores, projetada de forma flat por 7 dias
- Modelo: `RandomForestRegressor` compartilhado entre medicamentos e horizontes
- Parâmetros do modelo: `n_estimators=100`, `min_samples_leaf=3`, `random_state=42`, `n_jobs=-1`
- Horizonte: 7 dias; `MAPE` calculado somente nos dias com consumo realizado maior que zero

Para regenerar este relatório no estado atual do repositório:

```bash
python src/evaluation/comparar_modelos.py
```

## Resultado agregado (todos os 20 medicamentos)

| Método | MAE (unidades/dia) | MAPE (%) |
|---|---|---|
| Baseline (média móvel) | 9.99 | 18.9% |
| Modelo de ML | 9.79 | 18.4% |

**O modelo de ML reduziu o erro (MAE) em 2.0% frente ao baseline.**

## Detalhamento por medicamento

| Medicamento | MAE baseline | MAE modelo | MAPE baseline | MAPE modelo | Modelo venceu? |
|---|---|---|---|---|---|
| adrenalina_inj | 1.69 | 1.53 | 46.2% | 41.8% | Sim |
| amoxicilina | 8.60 | 8.94 | 16.3% | 17.3% | Não |
| azitromicina | 7.91 | 7.86 | 16.0% | 15.3% | Sim |
| ceftriaxona_inj | 8.36 | 8.54 | 21.5% | 20.0% | Não |
| diazepam | 4.45 | 4.38 | 31.1% | 30.2% | Sim |
| diclofenaco | 10.96 | 10.38 | 18.1% | 16.3% | Sim |
| dipirona | 27.44 | 26.99 | 11.9% | 11.6% | Sim |
| hidrocortisona_inj | 5.45 | 4.71 | 18.7% | 15.6% | Sim |
| ibuprofeno | 14.31 | 14.37 | 13.8% | 14.2% | Não |
| loratadina | 6.14 | 6.13 | 20.0% | 20.3% | Sim |
| metoclopramida | 8.98 | 7.65 | 19.4% | 16.6% | Sim |
| omeprazol_inj | 4.49 | 4.73 | 14.3% | 14.6% | Não |
| ondansetrona | 4.72 | 4.88 | 12.5% | 13.4% | Não |
| paracetamol | 22.99 | 23.75 | 12.4% | 12.7% | Não |
| predinisolona | 9.44 | 9.15 | 25.1% | 26.1% | Sim |
| salbutamol | 11.80 | 11.62 | 19.3% | 19.8% | Sim |
| soro_antitermico_infantil | 9.03 | 8.92 | 17.1% | 17.1% | Sim |
| soro_fisiologico | 20.52 | 18.50 | 14.3% | 12.4% | Sim |
| soro_ringer | 8.69 | 8.48 | 12.1% | 12.0% | Sim |
| tramadol | 3.85 | 4.32 | 17.5% | 19.8% | Não |
