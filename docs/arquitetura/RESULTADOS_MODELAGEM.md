# Resultados da comparação baseline vs. modelo de ML (Issue #13)

Período de teste: 2025-12-04 a 2025-12-31. Nenhum dos dois métodos viu dado desse período durante o treino/cálculo — o baseline usa só a janela móvel anterior a cada corte, o modelo é retreinado do zero a cada janela usando só `data <= corte`.

Dataset de treino/teste: `data/processed/consumo_medicamentos.csv`, período 2022-01-01 a 2025-12-31 (ver `src/utils/config.py`). **Este relatório é gerado do zero a cada execução de `comparar_modelos.py`** — os números não são comparáveis com versões anteriores deste arquivo se o dataset ou os hiperparâmetros do modelo mudaram entre execuções (ver histórico de melhorias em `src/models/README.md`).

## Resultado agregado (todos os 20 medicamentos)

| Método | MAE (unidades/dia) | MAPE (%) |
|---|---|---|
| Baseline (média móvel) | 15.52 | 22.7% |
| Modelo de ML | 14.15 | 22.6% |

**O modelo de ML reduziu o erro (MAE) em 8.8% frente ao baseline, vencendo em 16 de 20 medicamentos** (contagem derivada automaticamente da tabela abaixo, não escrita à mão).

## Detalhamento por medicamento

| Medicamento | MAE baseline | MAE modelo | MAPE baseline | MAPE modelo | Modelo venceu? |
|---|---|---|---|---|---|
| adrenalina_inj | 2.16 | 2.88 | 51.9% | 82.3% | Não |
| amoxicilina | 13.06 | 11.29 | 19.3% | 16.1% | Sim |
| azitromicina | 9.21 | 8.73 | 17.4% | 15.8% | Sim |
| ceftriaxona_inj | 10.18 | 7.14 | 21.3% | 14.8% | Sim |
| diazepam | 4.06 | 4.82 | 23.8% | 29.1% | Não |
| diclofenaco | 8.85 | 7.88 | 11.6% | 10.3% | Sim |
| dipirona | 51.11 | 45.90 | 15.5% | 14.0% | Sim |
| hidrocortisona_inj | 9.04 | 8.24 | 25.5% | 23.5% | Sim |
| ibuprofeno | 14.09 | 13.76 | 11.9% | 11.7% | Sim |
| loratadina | 13.53 | 11.08 | 36.0% | 26.4% | Sim |
| metoclopramida | 8.68 | 10.43 | 16.9% | 20.4% | Não |
| omeprazol_inj | 8.23 | 6.58 | 18.7% | 14.7% | Sim |
| ondansetrona | 7.06 | 8.42 | 20.1% | 24.8% | Não |
| paracetamol | 43.80 | 37.53 | 19.7% | 15.9% | Sim |
| predinisolona | 16.16 | 15.56 | 26.8% | 24.3% | Sim |
| salbutamol | 24.02 | 21.02 | 25.6% | 20.8% | Sim |
| soro_antitermico_infantil | 23.01 | 22.95 | 33.0% | 30.4% | Sim |
| soro_fisiologico | 21.44 | 19.00 | 13.2% | 12.0% | Sim |
| soro_ringer | 16.11 | 13.73 | 21.1% | 18.3% | Sim |
| tramadol | 6.63 | 6.08 | 25.1% | 26.0% | Sim |

## Reprodutibilidade

- **Commit:** `8eb7d4a`
- **Hash do dataset avaliado:** `9a043b77` (`data/processed/consumo_medicamentos.csv`, SHA256 truncado — dataset regenerado muda esse hash mesmo com o mesmo commit de código)
- **Período avaliado:** 2025-12-04 a 2025-12-31 (dataset completo: 2022-01-01 a 2025-12-31)
- **Ambiente:** Python 3.14.5, pandas 3.0.3, numpy 2.4.6, scikit-learn 1.8.0, xgboost 3.4.0 (ver `requirements.txt` para as versões fixadas)
- **Baseline:** média móvel de 14 dias (`src/models/baseline.py::prever_baseline`)
- **Modelo de ML:** XGBoost (`XGBRegressor`, `n_estimators=500`, `random_state=42`, `max_depth=7, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8, n_jobs=1`) — hiperparâmetros vêm de `src/models/modelo_demanda.py::HIPERPARAMETROS_XGBOOST`, fonte única (este texto nunca é editado à mão)
- **Medicamentos onde o modelo venceu:** 16 de 20 (derivado da tabela acima, coberto por teste — ver `tests/test_comparar_modelos.py`)
- **Comando para regenerar este relatório:** `python src/evaluation/comparar_modelos.py`

`n_jobs=1` é deliberado (não é o mais rápido): XGBoost com `tree_method="hist"` não é invariante ao número de threads mesmo com `random_state` fixo — rodar com `n_jobs=-1` em máquinas com números de núcleos diferentes pode produzir modelos (e relatórios) diferentes. Duas execuções nas mesmas condições acima devem produzir exatamente o mesmo relatório.
