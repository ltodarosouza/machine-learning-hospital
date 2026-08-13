# Resultados da comparação baseline vs. modelo de ML (Issue #13)

Período de teste: 2025-12-04 a 2025-12-31. Nenhum dos dois métodos viu dado desse período durante o treino/cálculo — o baseline usa só a janela móvel anterior a cada corte, o modelo é retreinado do zero a cada janela usando só `data <= corte`.

Dataset de treino/teste: `data/processed/consumo_medicamentos.csv`, período 2022-01-01 a 2025-12-31 (ver `src/utils/config.py`). **Este relatório é gerado do zero a cada execução de `comparar_modelos.py`** — os números não são comparáveis com versões anteriores deste arquivo se o dataset ou os hiperparâmetros do modelo mudaram entre execuções (ver histórico de melhorias em `src/models/README.md`).

## Resultado agregado (todos os 20 medicamentos)

| Método | MAE (unidades/dia) | MAPE (%) |
|---|---|---|
| Baseline (média móvel) | 15.52 | 22.7% |
| Modelo de ML | 15.24 | 28.9% |

**O modelo de ML reduziu o erro (MAE) em 1.8% frente ao baseline, vencendo em 9 de 20 medicamentos** (contagem derivada automaticamente da tabela abaixo, não escrita à mão).

## Detalhamento por medicamento

| Medicamento | MAE baseline | MAE modelo | MAPE baseline | MAPE modelo | Modelo venceu? |
|---|---|---|---|---|---|
| adrenalina_inj | 2.16 | 3.54 | 51.9% | 109.7% | Não |
| amoxicilina | 13.06 | 11.90 | 19.3% | 19.4% | Sim |
| azitromicina | 9.21 | 9.19 | 17.4% | 19.0% | Sim |
| ceftriaxona_inj | 10.18 | 8.12 | 21.3% | 18.6% | Sim |
| diazepam | 4.06 | 6.16 | 23.8% | 39.9% | Não |
| diclofenaco | 8.85 | 10.37 | 11.6% | 14.4% | Não |
| dipirona | 51.11 | 32.45 | 15.5% | 10.6% | Sim |
| hidrocortisona_inj | 9.04 | 9.90 | 25.5% | 31.6% | Não |
| ibuprofeno | 14.09 | 14.54 | 11.9% | 13.5% | Não |
| loratadina | 13.53 | 10.70 | 36.0% | 29.4% | Sim |
| metoclopramida | 8.68 | 16.37 | 16.9% | 32.7% | Não |
| omeprazol_inj | 8.23 | 6.01 | 18.7% | 15.0% | Sim |
| ondansetrona | 7.06 | 12.47 | 20.1% | 36.4% | Não |
| paracetamol | 43.80 | 40.03 | 19.7% | 18.6% | Sim |
| predinisolona | 16.16 | 14.17 | 26.8% | 25.6% | Sim |
| salbutamol | 24.02 | 26.66 | 25.6% | 30.2% | Não |
| soro_antitermico_infantil | 23.01 | 19.34 | 33.0% | 30.4% | Sim |
| soro_fisiologico | 21.44 | 23.83 | 13.2% | 15.6% | Não |
| soro_ringer | 16.11 | 20.69 | 21.1% | 29.2% | Não |
| tramadol | 6.63 | 8.33 | 25.1% | 38.9% | Não |

## Reprodutibilidade

- **Commit:** `f86b3c5`
- **Hash do dataset avaliado:** `9a043b77` (`data/processed/consumo_medicamentos.csv`, SHA256 truncado — dataset regenerado muda esse hash mesmo com o mesmo commit de código)
- **Período avaliado:** 2025-12-04 a 2025-12-31 (dataset completo: 2022-01-01 a 2025-12-31)
- **Ambiente:** Python 3.14.5, pandas 3.0.3, numpy 2.4.6, scikit-learn 1.8.0, xgboost 3.4.0 (ver `requirements.txt` para as versões fixadas)
- **Baseline:** média móvel de 14 dias (`src/models/baseline.py::prever_baseline`)
- **Modelo de ML:** XGBoost (`XGBRegressor`, `n_estimators=500`, `random_state=42`, `objective=reg:quantileerror`, `quantile_alpha=0.8`, `max_depth=7, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8, n_jobs=1`) — objetivo aprovado pela Issue #84, demais hiperparâmetros vêm de `src/models/modelo_demanda.py::HIPERPARAMETROS_XGBOOST`, fonte única (este texto nunca é editado à mão)
- **Medicamentos onde o modelo venceu:** 9 de 20 (derivado da tabela acima, coberto por teste — ver `tests/test_comparar_modelos.py`)
- **Comando para regenerar este relatório:** `python src/evaluation/comparar_modelos.py`

`n_jobs=1` é deliberado (não é o mais rápido): XGBoost com `tree_method="hist"` não é invariante ao número de threads mesmo com `random_state` fixo — rodar com `n_jobs=-1` em máquinas com números de núcleos diferentes pode produzir modelos (e relatórios) diferentes. Duas execuções nas mesmas condições acima devem produzir exatamente o mesmo relatório.
