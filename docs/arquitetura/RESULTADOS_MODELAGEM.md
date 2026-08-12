# Resultados da comparação baseline vs. modelo de ML (Issue #13)

Período de teste: 2025-12-04 a 2025-12-31. Nenhum dos dois métodos viu dado desse período durante o treino/cálculo — o baseline usa só a janela móvel anterior a cada corte, o modelo é retreinado do zero a cada janela usando só `data <= corte`.

## Resultado agregado (todos os 20 medicamentos)

| Método | MAE (unidades/dia) | MAPE (%) |
|---|---|---|
| Baseline (média móvel) | 9.99 | 18.9% |
| Modelo de ML | 9.83 | 18.5% |

**O modelo de ML reduziu o erro (MAE) em 1.6% frente ao baseline.**

## Detalhamento por medicamento

| Medicamento | MAE baseline | MAE modelo | MAPE baseline | MAPE modelo | Modelo venceu? |
|---|---|---|---|---|---|
| adrenalina_inj | 1.69 | 1.59 | 46.2% | 42.2% | Sim |
| amoxicilina | 8.60 | 9.02 | 16.3% | 17.5% | Não |
| azitromicina | 7.91 | 7.74 | 16.0% | 15.2% | Sim |
| ceftriaxona_inj | 8.36 | 8.65 | 21.5% | 20.3% | Não |
| diazepam | 4.45 | 4.36 | 31.1% | 29.7% | Sim |
| diclofenaco | 10.96 | 10.33 | 18.1% | 16.3% | Sim |
| dipirona | 27.44 | 26.28 | 11.9% | 11.3% | Sim |
| hidrocortisona_inj | 5.45 | 4.75 | 18.7% | 15.7% | Sim |
| ibuprofeno | 14.31 | 14.33 | 13.8% | 14.0% | Não |
| loratadina | 6.14 | 6.03 | 20.0% | 20.0% | Sim |
| metoclopramida | 8.98 | 8.01 | 19.4% | 17.4% | Sim |
| omeprazol_inj | 4.49 | 4.68 | 14.3% | 14.4% | Não |
| ondansetrona | 4.72 | 4.94 | 12.5% | 13.5% | Não |
| paracetamol | 22.99 | 23.82 | 12.4% | 12.7% | Não |
| predinisolona | 9.44 | 9.22 | 25.1% | 26.1% | Sim |
| salbutamol | 11.80 | 11.30 | 19.3% | 19.5% | Sim |
| soro_antitermico_infantil | 9.03 | 10.07 | 17.1% | 19.4% | Não |
| soro_fisiologico | 20.52 | 18.69 | 14.3% | 12.5% | Sim |
| soro_ringer | 8.69 | 8.61 | 12.1% | 12.2% | Sim |
| tramadol | 3.85 | 4.27 | 17.5% | 19.6% | Não |
