# Relatório de validação operacional

> **Transparência financeira:** Os custos apresentados são estimativas produzidas com dados sintéticos e preços unitários de referência. Eles não representam economia financeira comprovada em uma operação hospitalar real.

## Metadados da execução

- **commit:** `21aac91`
- **hash_codigo_protocolo:** `cd5a0dbc`
- **hash_consumo_diario:** `15afaef5`
- **hash_consumo_medicamentos:** `3043fd82`
- **hash_executor_protocolo:** `d08bd65d`
- **hash_medicamentos_ref:** `b433c7da`
- **hiperparametros_modelo:** `{"colsample_bytree": 0.8, "learning_rate": 0.1, "max_depth": 7, "n_jobs": 1, "subsample": 0.8}`
- **n_estimators:** `500`
- **versoes:** `{"numpy": "2.4.6", "pandas": "3.0.3", "python": "3.14.6", "scikit-learn": "1.8.0", "xgboost": "3.4.0"}`
- **worktree_sujo:** `True`

## Configuração do protocolo

```json
{
  "aumento_relevante_maximo": 0.05,
  "fracao_minima_janelas_com_meta": 0.75,
  "horizonte_dias": 7,
  "minimo_janelas": 4,
  "reducao_minima_custo": 0.1,
  "tolerancia_empate": 1e-09,
  "treino_minimo_dias": 365,
  "versao": "1.0.0"
}
```

## Janelas

| janela_id | inicio_treino | fim_treino | inicio_avaliacao | fim_avaliacao |
|---|---|---|---|---|
| janela_001 | 2022-01-01 | 2025-11-29 | 2025-11-30 | 2025-12-06 |
| janela_002 | 2022-01-01 | 2025-12-06 | 2025-12-07 | 2025-12-13 |
| janela_003 | 2022-01-01 | 2025-12-13 | 2025-12-14 | 2025-12-20 |
| janela_004 | 2022-01-01 | 2025-12-20 | 2025-12-21 | 2025-12-27 |

## Métricas por janela e candidato

| janela_id | candidato | mae | mape | vies_previsao | subestimacao | superestimacao | custo_compras_emergenciais_reais | episodios_ruptura | unidades_em_ruptura | unidades_vencidas | quantidade_total_recomendada |
|---|---|---|---|---|---|---|---|---|---|---|---|
| janela_001 | baseline | 16.436734693877554 | 22.948579839105815 | 0.04999999999999919 | 1147.0714285714287 | 1154.0714285714284 | 5806.539352097712 | 13.0 | 599.9211364843329 | 66.13542219861918 | 4376.842857142858 |
| janela_001 | modelo_atual | 15.119672312055314 | 22.599645946373755 | -8.592233235495431 | 1659.8333883285522 | 456.9207353591919 | 5806.539352097712 | 13.0 | 599.9211364843329 | 66.13542219861918 | 3950.2085296630858 |
| janela_002 | baseline | 15.679081632653064 | 19.448609450175844 | -8.053571428571429 | 1661.2857142857142 | 533.7857142857144 | 3220.528571428572 | 17.0 | 803.6571428571428 | 0.0 | 3039.0999999999995 |
| janela_002 | modelo_atual | 13.7299535376685 | 21.565461089436894 | 3.113622580255781 | 743.1431670188904 | 1179.0503282546997 | 3052.442857142858 | 15.0 | 757.5714285714288 | 0.0 | 3841.9333539690288 |
| janela_003 | baseline | 14.685204081632653 | 17.55074673979822 | -8.289285714285715 | 1608.2142857142858 | 447.71428571428567 | 8357.70714285714 | 23.0 | 1263.0 | 0.0 | 6683.52857142857 |
| janela_003 | modelo_atual | 14.455299200330462 | 18.28028774473983 | -8.642480087280273 | 1616.8445501327515 | 406.8973379135132 | 8357.70714285714 | 23.0 | 1263.0 | 0.0 | 6813.293132237025 |
| janela_004 | baseline | 16.513775510204084 | 29.745837720424497 | 3.4750000000000005 | 912.7142857142858 | 1399.2142857142858 | 3892.921428571431 | 25.0 | 2130.928571428572 | 0.0 | 6185.7 |
| janela_004 | modelo_atual | 16.57107917581286 | 32.885069700942836 | 3.899089653151376 | 887.0392665863037 | 1432.9118180274963 | 3892.921428571431 | 25.0 | 2130.928571428572 | 0.0 | 6632.692431858607 |

## Consolidação final

| candidato | mae | mape | vies_previsao | subestimacao | superestimacao | custo_compras_emergenciais_reais | episodios_ruptura | unidades_em_ruptura | unidades_vencidas | quantidade_total_recomendada |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 15.828698979591838 | 22.423443437376093 | -3.2044642857142858 | 1332.3214285714287 | 883.6964285714286 | 21277.696494954853 | 78.0 | 4797.506850770048 | 66.13542219861918 | 20285.171428571426 |
| modelo_atual | 14.969001056466784 | 23.83261612037333 | -2.5555002723421367 | 1226.7150930166245 | 868.9450548887253 | 21109.61078066914 | 76.0 | 4751.421136484334 | 66.13542219861918 | 21238.127447727747 |

## Decisão final

```json
{
  "aprovado": false,
  "candidato": "modelo_atual",
  "janelas_avaliadas": 4,
  "janelas_com_meta_atingida": 0,
  "motivos_aprovacao": [
    "Sem piora operacional relevante nas métricas de bloqueio."
  ],
  "motivos_rejeicao": [
    "Redução agregada de custo 0.79% abaixo da meta de 10.00%.",
    "Consistência insuficiente: meta atingida em 0/4 janelas."
  ],
  "reducao_custo_emergencial_pct": 0.7899619882517306,
  "status": "rejeitado",
  "variacao_episodios_ruptura_pct": -2.564102564102566,
  "variacao_unidades_ruptura_pct": -0.9606179984571694,
  "variacao_vencimento_pct": 0.0
}
```

## Limitações

- Resultados operacionais dependem das hipóteses do simulador e não substituem piloto real.
- Os dados do MVP são sintéticos; preços são referências para comparação relativa.
- A Issue #76 ainda não está integrada; este relatório não oferece diagnóstico por medicamento e mês.
