# Resultados da comparação baseline vs. modelo de ML (Issue #13)

Período de teste: 2025-12-04 a 2025-12-31. Nenhum dos dois métodos viu dado desse período durante o treino/cálculo — o baseline usa só a janela móvel anterior a cada corte, o modelo é retreinado do zero a cada janela usando só `data <= corte`.

Dataset de treino/teste: `data/processed/consumo_medicamentos.csv`, período 2022-01-01 a 2025-12-31 (ver `src/utils/config.py`). **Este relatório é gerado do zero a cada execução de `comparar_modelos.py`** — os números não são comparáveis com versões anteriores deste arquivo se o dataset ou os hiperparâmetros do modelo mudaram entre execuções (ver histórico de melhorias em `src/models/README.md`).

## Resultado agregado (todos os 20 medicamentos)

| Método | MAE (unidades/dia) | MAPE (%) |
|---|---|---|
| Baseline (média móvel) | 9.60 | 18.2% |
| Modelo de ML | 9.39 | 17.7% |

**O modelo de ML reduziu o erro (MAE) em 2.1% frente ao baseline.**

## Detalhamento por medicamento

| Medicamento | MAE baseline | MAE modelo | MAPE baseline | MAPE modelo | Modelo venceu? |
|---|---|---|---|---|---|
| adrenalina_inj | 2.02 | 2.16 | 41.9% | 41.2% | Não |
| amoxicilina | 7.60 | 7.69 | 16.0% | 15.5% | Não |
| azitromicina | 6.83 | 7.00 | 14.8% | 14.5% | Não |
| ceftriaxona_inj | 6.63 | 6.11 | 17.4% | 15.4% | Sim |
| diazepam | 3.66 | 3.78 | 23.1% | 24.4% | Não |
| diclofenaco | 11.95 | 11.65 | 21.3% | 21.0% | Sim |
| dipirona | 26.60 | 27.73 | 10.6% | 10.8% | Não |
| hidrocortisona_inj | 6.23 | 5.54 | 28.6% | 26.9% | Sim |
| ibuprofeno | 11.81 | 10.21 | 12.2% | 10.9% | Sim |
| loratadina | 5.15 | 4.82 | 20.1% | 18.8% | Sim |
| metoclopramida | 8.02 | 7.66 | 17.1% | 16.2% | Sim |
| omeprazol_inj | 7.44 | 7.28 | 21.6% | 21.0% | Sim |
| ondansetrona | 5.94 | 5.97 | 17.8% | 18.6% | Não |
| paracetamol | 25.02 | 24.21 | 12.5% | 11.8% | Sim |
| predinisolona | 5.81 | 5.92 | 13.8% | 14.1% | Não |
| salbutamol | 7.33 | 7.35 | 11.7% | 11.8% | Não |
| soro_antitermico_infantil | 8.74 | 8.37 | 17.9% | 17.1% | Sim |
| soro_fisiologico | 19.69 | 18.97 | 13.3% | 12.8% | Sim |
| soro_ringer | 12.03 | 12.18 | 16.3% | 16.1% | Não |
| tramadol | 3.45 | 3.24 | 16.3% | 16.0% | Sim |
