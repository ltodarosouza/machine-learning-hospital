# Avaliação de previsão assimétrica (Issue #78)

> **Transparência financeira:** os custos apresentados são estimativas produzidas com dados sintéticos e preços unitários de referência. Não representam economia financeira comprovada em uma operação hospitalar real.

Testa se penalizar mais a subestimação de demanda (regressão quantílica do XGBoost, `quantile_alpha > 0.5`) reduz rupturas nos picos, mantendo a política de estoque/compra inalterada. Usa as mesmas janelas oficiais e a mesma função de aprovação do protocolo da [Issue #77](../avaliacao/PROTOCOLO_VALIDACAO_OPERACIONAL.md).

## Candidatos avaliados

- `quantile_060`: `quantile_alpha=0.6` (XGBoost, `objective=reg:quantileerror`).
- `quantile_080`: `quantile_alpha=0.8` (XGBoost, `objective=reg:quantileerror`).

## Janelas (mesmas do protocolo oficial da Issue #77)

| janela_id | inicio_treino | fim_treino | inicio_avaliacao | fim_avaliacao |
|---|---|---|---|---|
| janela_001 | 2022-01-01 | 2025-11-29 | 2025-11-30 | 2025-12-06 |
| janela_002 | 2022-01-01 | 2025-12-06 | 2025-12-07 | 2025-12-13 |
| janela_003 | 2022-01-01 | 2025-12-13 | 2025-12-14 | 2025-12-20 |
| janela_004 | 2022-01-01 | 2025-12-20 | 2025-12-21 | 2025-12-27 |

## Métricas por candidato e janela

| janela_id | candidato | mae | mape | vies_previsao | subestimacao | superestimacao | custo_compras_emergenciais_reais | episodios_ruptura | unidades_em_ruptura | unidades_vencidas | quantidade_total_recomendada |
|---|---|---|---|---|---|---|---|---|---|---|---|
| janela_001 | baseline | 16.44 | 22.9 | +0.05 | 1147.1 | 1154.1 | 5806.54 | 13 | 599.9 | 66.1 | 4376.8 |
| janela_001 | modelo_atual | 15.38 | 21.9 | -10.20 | 1790.1 | 362.6 | 5806.54 | 13 | 599.9 | 66.1 | 3893.8 |
| janela_001 | quantile_060 | 15.24 | 22.3 | -9.83 | 1754.6 | 379.0 | 5806.54 | 13 | 599.9 | 66.1 | 3753.8 |
| janela_001 | quantile_080 | 13.88 | 24.3 | +0.55 | 933.2 | 1010.0 | 5806.54 | 13 | 599.9 | 66.1 | 4535.7 |
| janela_002 | baseline | 15.68 | 19.4 | -8.05 | 1661.3 | 533.8 | 3220.53 | 17 | 803.7 | 0.0 | 3039.1 |
| janela_002 | modelo_atual | 14.54 | 19.7 | +1.31 | 926.1 | 1109.8 | 3052.44 | 15 | 757.6 | 0.0 | 3409.8 |
| janela_002 | quantile_060 | 13.30 | 21.1 | +2.81 | 734.6 | 1127.7 | 3052.44 | 15 | 757.6 | 0.0 | 3887.7 |
| janela_002 | quantile_080 | 17.09 | 28.0 | +12.79 | 300.5 | 2091.6 | 3052.44 | 15 | 757.6 | 0.0 | 4501.4 |
| janela_003 | baseline | 14.69 | 17.6 | -8.29 | 1608.2 | 447.7 | 8357.71 | 23 | 1263.0 | 0.0 | 6683.5 |
| janela_003 | modelo_atual | 14.95 | 18.9 | -9.78 | 1730.6 | 361.9 | 8357.71 | 23 | 1263.0 | 0.0 | 6517.8 |
| janela_003 | quantile_060 | 14.55 | 18.2 | -7.22 | 1524.0 | 513.1 | 8357.71 | 23 | 1263.0 | 0.0 | 6790.1 |
| janela_003 | quantile_080 | 11.51 | 20.8 | +3.06 | 591.2 | 1019.9 | 8357.71 | 23 | 1263.0 | 0.0 | 8051.2 |
| janela_004 | baseline | 16.51 | 29.7 | +3.48 | 912.7 | 1399.2 | 3892.92 | 25 | 2130.9 | 0.0 | 6185.7 |
| janela_004 | modelo_atual | 16.41 | 31.4 | +2.96 | 941.8 | 1355.8 | 3892.92 | 25 | 2130.9 | 0.0 | 6535.9 |
| janela_004 | quantile_060 | 16.59 | 33.6 | +8.32 | 578.9 | 1744.2 | 3892.92 | 25 | 2130.9 | 0.0 | 6657.5 |
| janela_004 | quantile_080 | 19.58 | 42.0 | +13.56 | 421.1 | 2319.9 | 3892.92 | 25 | 2130.9 | 0.0 | 7375.5 |

## Consolidação (soma dos custos/rupturas, média do MAE/MAPE/viés)

| candidato | mae | mape | vies_previsao | custo_compras_emergenciais_reais | episodios_ruptura | unidades_em_ruptura | unidades_vencidas |
|---|---|---|---|---|---|---|---|
| baseline | 15.83 | 22.4 | -3.20 | 21277.70 | 78 | 4797.5 | 66.1 |
| modelo_atual | 15.32 | 23.0 | -3.93 | 21109.61 | 76 | 4751.4 | 66.1 |
| quantile_060 | 14.92 | 23.8 | -1.48 | 21109.61 | 76 | 4751.4 | 66.1 |
| quantile_080 | 15.51 | 28.8 | +7.49 | 21109.61 | 76 | 4751.4 | 66.1 |

## Decisões (protocolo da Issue #77, `avaliar_aprovacao`)

`vs_baseline` é o vocabulário literal do protocolo (candidato contra a média móvel). `vs_modelo_atual` é a pergunta operacional — só ela decide se o candidato substituiria o XGBoost simétrico em uso hoje.

### quantile_060

**vs. baseline**
- **quantile_060:** [rejeitado] — redução de custo emergencial: 0.8%, meta atingida em 0/4 janelas.
  - rejeição: Redução agregada de custo 0.79% abaixo da meta de 10.00%.
  - rejeição: Consistência insuficiente: meta atingida em 0/4 janelas.
  - aprovação: Sem piora operacional relevante nas métricas de bloqueio.

**vs. modelo atual**
- **quantile_060:** [rejeitado] — redução de custo emergencial: 0.0%, meta atingida em 0/4 janelas.
  - rejeição: Redução agregada de custo 0.00% abaixo da meta de 10.00%.
  - rejeição: Consistência insuficiente: meta atingida em 0/4 janelas.
  - aprovação: Sem piora operacional relevante nas métricas de bloqueio.

### quantile_080

**vs. baseline**
- **quantile_080:** [rejeitado] — redução de custo emergencial: 0.8%, meta atingida em 0/4 janelas.
  - rejeição: Redução agregada de custo 0.79% abaixo da meta de 10.00%.
  - rejeição: Consistência insuficiente: meta atingida em 0/4 janelas.
  - aprovação: Sem piora operacional relevante nas métricas de bloqueio.

**vs. modelo atual**
- **quantile_080:** [rejeitado] — redução de custo emergencial: 0.0%, meta atingida em 0/4 janelas.
  - rejeição: Redução agregada de custo 0.00% abaixo da meta de 10.00%.
  - rejeição: Consistência insuficiente: meta atingida em 0/4 janelas.
  - aprovação: Sem piora operacional relevante nas métricas de bloqueio.

## Recomendação

**Nenhum candidato atingiu o critério de aprovação da Issue #77 contra o modelo atual. O modelo atual é mantido** (critério de aceite da Issue #78: sem aprovação, não há adoção). Essa rejeição é honesta em relação ao protocolo, mas ver a seção **Sensibilidade da janela de 7 dias**, abaixo: nas janelas oficiais, o custo simulado é quase insensível à previsão testada, então a rejeição não deve ser lida como "a previsão assimétrica não ajuda" — só como "não passou neste teste específico", que tem pouco poder para detectar diferença nesta configuração.


Na **simulação contínua** (seção abaixo, que dá tempo real do pedido chegar), **quantile_080** reduziu o custo de compra emergencial em pelo menos 10% em todos os meses simulados frente ao modelo atual — sinal forte o bastante para justificar revalidar formalmente com o protocolo #77 numa configuração de janela mais longa (ex.: janelas mensais em vez de semanais), antes de descartar o candidato só pela rejeição acima.

## Sensibilidade da janela de 7 dias ao pedido

O prazo de entrega mínimo do MVP (5 dias) é próximo do horizonte de avaliação (7 dias): um pedido feito durante a janela raramente chega a tempo de afetar a própria janela, então a ruptura observada é dominada pelo estoque inicial (idêntico para todo candidato), não pela previsão. Por isso a comparação de custo abaixo pode ter pouca sensibilidade à previsão testada — reportado explicitamente, calculado a cada execução.

| Candidato | Pares (janela, medicamento) com custo diferente do modelo atual | Total de pares |
|---|---:|---:|
| quantile_060 | 0 | 80 |
| quantile_080 | 0 | 80 |

## Simulação contínua complementar (estoque não reseta a cada semana)

Estoque inicial único no começo de cada mês, sem reset semanal — o pedido de uma semana pode chegar e afetar semanas seguintes do mesmo mês (mesma abordagem do relatório de impacto trimestral, Issue #17, e do relatório por medicamento/mês, Issue #76). **Não substitui a decisão formal do protocolo #77** — é evidência complementar sobre se a previsão assimétrica economiza de verdade, quando o pedido tem tempo de fazer efeito.

### quantile_060 vs. modelo atual

| Mês | Métrica | Modelo atual | Candidato | Redução | Redução (%) |
|---|---|---:|---:|---:|---:|
| 10 | episodios_ruptura | 93.00 | 82.00 | 11.00 | 11.8% |
| 10 | unidades_em_ruptura | 3513.91 | 2954.85 | 559.05 | 15.9% |
| 10 | custo_compras_emergenciais_reais | 11179.09 | 10773.02 | 406.06 | 3.6% |
| 10 | unidades_vencidas | 173.77 | 173.77 | 0.00 | 0.0% |
| 11 | episodios_ruptura | 158.00 | 143.00 | 15.00 | 9.5% |
| 11 | unidades_em_ruptura | 9223.27 | 8932.86 | 290.41 | 3.1% |
| 11 | custo_compras_emergenciais_reais | 21402.28 | 20495.87 | 906.41 | 4.2% |
| 11 | unidades_vencidas | 421.81 | 421.81 | 0.00 | 0.0% |
| 12 | episodios_ruptura | 114.00 | 101.00 | 13.00 | 11.4% |
| 12 | unidades_em_ruptura | 3328.26 | 2914.71 | 413.55 | 12.4% |
| 12 | custo_compras_emergenciais_reais | 15111.57 | 15556.33 | -444.77 | -2.9% |
| 12 | unidades_vencidas | 69.14 | 69.14 | 0.00 | 0.0% |

**Consolidado (todos os meses):**

| Métrica | Modelo atual | Candidato | Redução | Redução (%) |
|---|---:|---:|---:|---:|
| episodios_ruptura | 365.00 | 326.00 | 39.00 | 10.7% |
| unidades_em_ruptura | 16065.44 | 14802.43 | 1263.01 | 7.9% |
| custo_compras_emergenciais_reais | 47692.93 | 46825.22 | 867.71 | 1.8% |
| unidades_vencidas | 664.72 | 664.72 | 0.00 | 0.0% |

### quantile_080 vs. modelo atual

| Mês | Métrica | Modelo atual | Candidato | Redução | Redução (%) |
|---|---|---:|---:|---:|---:|
| 10 | episodios_ruptura | 93.00 | 41.00 | 52.00 | 55.9% |
| 10 | unidades_em_ruptura | 3513.91 | 1820.88 | 1693.03 | 48.2% |
| 10 | custo_compras_emergenciais_reais | 11179.09 | 6817.93 | 4361.16 | 39.0% |
| 10 | unidades_vencidas | 173.77 | 173.77 | 0.00 | 0.0% |
| 11 | episodios_ruptura | 158.00 | 77.00 | 81.00 | 51.3% |
| 11 | unidades_em_ruptura | 9223.27 | 7060.19 | 2163.08 | 23.5% |
| 11 | custo_compras_emergenciais_reais | 21402.28 | 14784.40 | 6617.88 | 30.9% |
| 11 | unidades_vencidas | 421.81 | 421.81 | 0.00 | 0.0% |
| 12 | episodios_ruptura | 114.00 | 70.00 | 44.00 | 38.6% |
| 12 | unidades_em_ruptura | 3328.26 | 1916.60 | 1411.66 | 42.4% |
| 12 | custo_compras_emergenciais_reais | 15111.57 | 11334.05 | 3777.51 | 25.0% |
| 12 | unidades_vencidas | 69.14 | 69.14 | 0.00 | 0.0% |

**Consolidado (todos os meses):**

| Métrica | Modelo atual | Candidato | Redução | Redução (%) |
|---|---:|---:|---:|---:|
| episodios_ruptura | 365.00 | 188.00 | 177.00 | 48.5% |
| unidades_em_ruptura | 16065.44 | 10797.67 | 5267.77 | 32.8% |
| custo_compras_emergenciais_reais | 47692.93 | 32936.38 | 14756.55 | 30.9% |
| unidades_vencidas | 664.72 | 664.72 | 0.00 | 0.0% |


## Ganhos e perdas por medicamento (simulação contínua, custo de compra emergencial)

Reportado por completo — inclui os medicamentos onde o candidato perde, não só onde ganha. Vem da simulação contínua (estoque não reseta a cada semana), não das janelas oficiais de 7 dias — é a decomposição que tem sinal real, dada a insensibilidade descrita na seção acima.

### quantile_060 - modelo atual (R$, positivo = candidato mais caro)

| medicamento_id | diferenca_custo_reais |
|---|---|
| soro_antitermico_infantil | +1763.13 |
| salbutamol | +1171.03 |
| paracetamol | +34.12 |
| diazepam | -8.59 |
| metoclopramida | -15.53 |
| predinisolona | -25.95 |
| diclofenaco | -40.57 |
| ibuprofeno | -42.17 |
| loratadina | -50.35 |
| adrenalina_inj | -60.37 |
| tramadol | -80.56 |
| dipirona | -90.88 |
| amoxicilina | -99.85 |
| ondansetrona | -198.28 |
| soro_ringer | -399.82 |
| azitromicina | -424.32 |
| omeprazol_inj | -490.23 |
| soro_fisiologico | -559.23 |
| hidrocortisona_inj | -613.98 |
| ceftriaxona_inj | -635.32 |

### quantile_080 - modelo atual (R$, positivo = candidato mais caro)

| medicamento_id | diferenca_custo_reais |
|---|---|
| diazepam | -8.59 |
| metoclopramida | -50.35 |
| paracetamol | -51.30 |
| loratadina | -103.99 |
| ibuprofeno | -152.01 |
| tramadol | -159.86 |
| diclofenaco | -177.06 |
| dipirona | -199.61 |
| amoxicilina | -208.34 |
| predinisolona | -230.69 |
| adrenalina_inj | -293.82 |
| ondansetrona | -390.50 |
| azitromicina | -657.51 |
| omeprazol_inj | -849.77 |
| soro_ringer | -1213.05 |
| soro_fisiologico | -1308.37 |
| hidrocortisona_inj | -1501.77 |
| ceftriaxona_inj | -1873.17 |
| soro_antitermico_infantil | -1997.32 |
| salbutamol | -3329.47 |


## Ganhos e perdas por medicamento (janelas oficiais de 7 dias, custo de compra emergencial)

Reportado por completo — inclui os medicamentos onde o candidato perde, não só onde ganha. **Atenção:** vem das janelas isoladas do protocolo #77; a seção "Sensibilidade da janela de 7 dias" mostra que essa comparação tem pouco sinal aqui — use a decomposição da simulação contínua acima para decidir algo.

### quantile_060 - modelo atual (R$, positivo = candidato mais caro)

| medicamento_id | diferenca_custo_reais |
|---|---|
| adrenalina_inj | +0.00 |
| amoxicilina | +0.00 |
| azitromicina | +0.00 |
| ceftriaxona_inj | +0.00 |
| diazepam | +0.00 |
| diclofenaco | +0.00 |
| dipirona | +0.00 |
| hidrocortisona_inj | +0.00 |
| ibuprofeno | +0.00 |
| loratadina | +0.00 |
| metoclopramida | +0.00 |
| omeprazol_inj | +0.00 |
| ondansetrona | +0.00 |
| paracetamol | +0.00 |
| predinisolona | +0.00 |
| salbutamol | +0.00 |
| soro_antitermico_infantil | +0.00 |
| soro_fisiologico | +0.00 |
| soro_ringer | +0.00 |
| tramadol | +0.00 |

### quantile_080 - modelo atual (R$, positivo = candidato mais caro)

| medicamento_id | diferenca_custo_reais |
|---|---|
| adrenalina_inj | +0.00 |
| amoxicilina | +0.00 |
| azitromicina | +0.00 |
| ceftriaxona_inj | +0.00 |
| diazepam | +0.00 |
| diclofenaco | +0.00 |
| dipirona | +0.00 |
| hidrocortisona_inj | +0.00 |
| ibuprofeno | +0.00 |
| loratadina | +0.00 |
| metoclopramida | +0.00 |
| omeprazol_inj | +0.00 |
| ondansetrona | +0.00 |
| paracetamol | +0.00 |
| predinisolona | +0.00 |
| salbutamol | +0.00 |
| soro_antitermico_infantil | +0.00 |
| soro_fisiologico | +0.00 |
| soro_ringer | +0.00 |
| tramadol | +0.00 |

## Reprodutibilidade

- **Protocolo:** versão `1.0.0` (Issue #77), `avaliar_aprovacao` sem alteração de limiares.
- **Commit:** `cc87e0a`
- **Hash do dataset avaliado:** `9a043b77`
- **Ambiente:** `{"numpy": "2.4.6", "pandas": "3.0.3", "python": "3.14.5", "scikit-learn": "1.8.0", "xgboost": "3.4.0"}`
- **Hiperparâmetros compartilhados (herdados de `modelo_demanda.py::HIPERPARAMETROS_XGBOOST`):** colsample_bytree=0.8, learning_rate=0.1, max_depth=7, n_jobs=1, subsample=0.8
- **n_estimators:** 500
- **Comando para regenerar:** `python src/evaluation/avaliacao_previsao_assimetrica.py`

## Limitações

- Herda todas as limitações do simulador de impacto (Issue #17): dados sintéticos, preços de referência, snapshot de lotes reconstruído.
- A política de estoque/compra (`fator_seguranca`) foi mantida idêntica à do modelo atual de propósito, para isolar o efeito da previsão — calibrar a política por perfil de medicamento é escopo da Issue #79, não desta avaliação.
- Quatro janelas detectam inconsistência grosseira, não substituem validação retrospectiva longa ou piloto hospitalar.
