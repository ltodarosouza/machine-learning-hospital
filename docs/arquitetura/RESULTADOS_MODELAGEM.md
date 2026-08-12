# Resultados da comparação baseline vs. modelo de ML (Issue #13)

Período de teste: 2025-12-04 a 2025-12-31. Nenhum dos dois métodos viu dado desse período durante o treino/cálculo — o baseline usa só a janela móvel anterior a cada corte, o modelo é retreinado do zero a cada janela usando só `data <= corte`.

## Resultado agregado (todos os 20 medicamentos)

| Método | MAE (unidades/dia) | MAPE (%) |
|---|---|---|
| Baseline (média móvel) | 9.99 | 18.9% |
| Modelo de ML | 9.64 | 18.5% |

**O modelo de ML reduziu o erro (MAE) em 3.6% frente ao baseline.**

## Detalhamento por medicamento

| Medicamento | MAE baseline | MAE modelo | MAPE baseline | MAPE modelo | Modelo venceu? |
|---|---|---|---|---|---|
| adrenalina_inj | 1.69 | 1.60 | 46.2% | 46.5% | Sim |
| amoxicilina | 8.60 | 8.14 | 16.3% | 15.3% | Sim |
| azitromicina | 7.91 | 8.22 | 16.0% | 16.3% | Não |
| ceftriaxona_inj | 8.36 | 8.65 | 21.5% | 21.3% | Não |
| diazepam | 4.45 | 4.35 | 31.1% | 30.4% | Sim |
| diclofenaco | 10.96 | 10.45 | 18.1% | 17.1% | Sim |
| dipirona | 27.44 | 25.84 | 11.9% | 10.9% | Sim |
| hidrocortisona_inj | 5.45 | 5.10 | 18.7% | 17.5% | Sim |
| ibuprofeno | 14.31 | 14.10 | 13.8% | 13.6% | Sim |
| loratadina | 6.14 | 6.01 | 20.0% | 19.8% | Sim |
| metoclopramida | 8.98 | 8.26 | 19.4% | 17.9% | Sim |
| omeprazol_inj | 4.49 | 4.89 | 14.3% | 15.1% | Não |
| ondansetrona | 4.72 | 4.84 | 12.5% | 13.2% | Não |
| paracetamol | 22.99 | 22.27 | 12.4% | 12.0% | Sim |
| predinisolona | 9.44 | 9.46 | 25.1% | 25.4% | Não |
| salbutamol | 11.80 | 11.52 | 19.3% | 19.5% | Sim |
| soro_antitermico_infantil | 9.03 | 9.00 | 17.1% | 16.8% | Sim |
| soro_fisiologico | 20.52 | 18.32 | 14.3% | 12.5% | Sim |
| soro_ringer | 8.69 | 7.76 | 12.1% | 10.8% | Sim |
| tramadol | 3.85 | 3.95 | 17.5% | 17.7% | Não |
