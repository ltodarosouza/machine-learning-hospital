# Relatório de validação operacional

> **Transparência financeira:** Os custos apresentados são estimativas produzidas com dados sintéticos e preços unitários de referência. Eles não representam economia financeira comprovada em uma operação hospitalar real.

## Metadados da execução

- **candidato_avaliado:** `quantile_080`
- **commit:** `66eb433`
- **dias_janela_avaliacao:** `28`
- **hash_consumo_diario:** `49e11a5c`
- **hash_consumo_medicamentos:** `9a043b77`
- **hash_medicamentos_ref:** `530958a8`
- **hiperparametros_modelo:** `{"colsample_bytree": 0.8, "learning_rate": 0.1, "max_depth": 7, "n_jobs": 1, "subsample": 0.8}`
- **n_estimators:** `500`
- **papel_de_baseline_nesta_decisao:** `modelo atual (XGBoost simétrico em produção)`
- **passo_retreino_dias:** `7`
- **versoes:** `{"numpy": "2.4.6", "pandas": "3.0.3", "python": "3.14.5", "scikit-learn": "1.8.0", "xgboost": "3.4.0"}`

## Configuração do protocolo

```json
{
  "aumento_relevante_maximo": 0.05,
  "fracao_minima_janelas_com_meta": 0.75,
  "horizonte_dias": 28,
  "minimo_janelas": 4,
  "reducao_minima_custo": 0.1,
  "tolerancia_empate": 1e-09,
  "treino_minimo_dias": 365,
  "versao": "1.1.0-janela-longa"
}
```

## Janelas

| janela_id | inicio_treino | fim_treino | inicio_avaliacao | fim_avaliacao |
|---|---|---|---|---|
| janela_001 | 2022-01-01 | 2025-09-06 | 2025-09-07 | 2025-10-04 |
| janela_002 | 2022-01-01 | 2025-10-04 | 2025-10-05 | 2025-11-01 |
| janela_003 | 2022-01-01 | 2025-11-01 | 2025-11-02 | 2025-11-29 |
| janela_004 | 2022-01-01 | 2025-11-29 | 2025-11-30 | 2025-12-27 |

## Métricas por janela e candidato

| janela_id | candidato | mae | mape | vies_previsao | subestimacao | superestimacao | custo_compras_emergenciais_reais | episodios_ruptura | unidades_em_ruptura | unidades_vencidas | quantidade_total_recomendada |
|---|---|---|---|---|---|---|---|---|---|---|---|
| janela_001 | baseline | 20.93011193914073 | 21.862986291109127 | -10.561304114120347 | 8817.596494913101 | 2903.266191005707 | 25255.209074074653 | 159.0 | 9040.483726757015 | 517.5186038801651 | 43573.18722130912 |
| janela_001 | quantile_080 | 21.546806899990354 | 28.238907966887727 | 1.8707363648074014 | 5509.299749851227 | 6556.912114143372 | 15708.65504667661 | 81.0 | 5729.965408145902 | 517.5186038801651 | 48212.05254004231 |
| janela_002 | baseline | 20.046546881965227 | 30.413511729553363 | 11.62897661115442 | 2356.9196758270264 | 8869.146578073502 | 15571.17735671829 | 93.0 | 3645.8360345693736 | 271.09152797484137 | 35275.72025148826 |
| janela_002 | quantile_080 | 30.199129148891995 | 47.69902701347055 | 27.612663321835655 | 724.2104315757751 | 16187.301891803741 | 10718.689709546115 | 44.0 | 2342.085324623139 | 271.09152797484137 | 37900.67961774554 |
| janela_003 | baseline | 25.7630020486457 | 30.116165856381148 | 3.288159153716905 | 6292.956010580063 | 8134.3251366615295 | 19785.766450860978 | 111.0 | 8303.32509714231 | 371.81451157538095 | 33418.97288044521 |
| janela_003 | quantile_080 | 32.6536127950464 | 42.29808847267128 | 13.86501994899341 | 5260.805996894836 | 13025.217168331146 | 15316.380599038268 | 73.0 | 7104.123946816582 | 371.81451157538095 | 37228.38587159124 |
| janela_004 | baseline | 15.31887588415827 | 22.98313118684038 | -3.9260446071624755 | 5388.577737569809 | 3189.9927575588226 | 16570.90001529918 | 121.0 | 3812.923296256933 | 66.13542219861918 | 31406.77696031843 |
| janela_004 | quantile_080 | 15.51298828125 | 28.78675485867157 | 7.491798915181842 | 2245.9330224990845 | 6441.3404150009155 | 9833.282647058826 | 62.0 | 1821.36977387447 | 66.13542219861918 | 34520.897113255094 |

## Consolidação final

| candidato | mae | mape | vies_previsao | subestimacao | superestimacao | custo_compras_emergenciais_reais | episodios_ruptura | unidades_em_ruptura | unidades_vencidas | quantidade_total_recomendada |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 20.51463418847748 | 26.343948765971007 | 0.10744676089712546 | 5714.0124797225 | 5774.18266582489 | 77183.0528969531 | 484.0 | 24802.56815472563 | 1226.5600656290067 | 143674.657313561 |
| quantile_080 | 24.978134281294686 | 36.75569457792528 | 12.710054637704577 | 3435.0623002052307 | 10552.692897319794 | 51577.00800231982 | 260.0 | 16997.544453460094 | 1226.5600656290067 | 157862.0151426342 |

## Decisão final

```json
{
  "aprovado": true,
  "candidato": "quantile_080",
  "janelas_avaliadas": 4,
  "janelas_com_meta_atingida": 4,
  "motivos_aprovacao": [
    "Meta agregada de redução do custo emergencial atingida.",
    "Meta atingida na fração mínima exigida de janelas.",
    "Sem piora operacional relevante nas métricas de bloqueio."
  ],
  "motivos_rejeicao": [],
  "reducao_custo_emergencial_pct": 33.17573474169239,
  "status": "aprovado",
  "variacao_episodios_ruptura_pct": -46.28099173553719,
  "variacao_unidades_ruptura_pct": -31.468611042919136,
  "variacao_vencimento_pct": 0.0
}
```

## Limitações

- Resultados operacionais dependem das hipóteses do simulador e não substituem piloto real.
- Os dados do MVP são sintéticos; preços são referências para comparação relativa.
- O diagnóstico detalhado por medicamento e mês é complementar e está disponível no relatório operacional da Issue #76.
