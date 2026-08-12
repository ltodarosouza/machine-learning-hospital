# `src/models/`

Modelos de previsão de demanda. Saída de todos os modelos aqui segue o mesmo contrato ([`docs/arquitetura/CONTRATOS.md`](../../docs/arquitetura/CONTRATOS.md) seção 3): `medicamento_id`, `data_previsao`, `demanda_prevista`, `intervalo_inferior`, `intervalo_superior`.

## `baseline.py` (Issue #11) — pronto

Baseline "sem ML": média móvel simples do consumo dos últimos `JANELA_PADRAO_DIAS` (14) dias, projetada como previsão flat para o horizonte (`HORIZONTE_PREVISAO_DIAS`, 7 dias, de `src/utils/config.py`). Representa como o hospital decide hoje — só olha o passado recente, sem variáveis externas.

```bash
python src/models/baseline.py
```

Funções principais:

- `prever_baseline(historico, data_corte, janela=14, horizonte=7)`: previsão a partir de um único corte de data. É a função que a Issue #12 (modelo de ML) deve "vencer" e que a Issue #15 (motor de recomendação) pode usar como fallback caso o modelo de ML falhe.
- `gerar_previsoes_baseline_periodo(historico, data_inicio, data_fim, ...)`: gera previsões em janelas sucessivas de `horizonte` dias, cobrindo um período de teste inteiro — pensada para a Issue #13 (comparação com o modelo de ML), que precisa avaliar erro em vários pontos do tempo, não só um.
- `validar_saida_baseline(previsao, medicamentos_esperados)`: confere que a saída bate com o contrato (colunas, sem nulos/negativos, intervalo consistente com a previsão pontual).

**Por que média móvel e não ponto de pedido fixo:** o Issue #11 original dava as duas opções. Média móvel foi escolhida por ser mais direta de comparar com o modelo de ML na mesma unidade (`demanda_prevista` em unidades/dia) — "ponto de pedido" é uma regra de decisão de compra, não uma previsão de demanda, e essa parte da lógica já está reservada para o motor de recomendação (Issues #14-16).

## `modelo_demanda.py` (Issue #12) — modelo de ML

O modelo usa `RandomForestRegressor` porque o MVP já possui features de lags,
médias móveis, calendário e variáveis externas; uma floresta captura relações
não lineares entre elas sem pressupor uma forma fixa de sazonalidade. O
medicamento é codificado como categoria e uma feature `horizonte_dias` permite
previsão direta para cada um dos 7 dias, evitando alimentar uma previsão como
entrada da próxima.

O treino nunca embaralha a série. `avaliar_validacao_temporal` cria as features
somente com o histórico até uma data de corte e compara as previsões com os 7
dias seguintes. Os intervalos de saída usam o desvio dos resíduos de treino por
medicamento; são faixas empíricas para comunicação no MVP, não intervalos de
confiança formais.

```bash
python src/models/modelo_demanda.py
```

O comando executa uma validação temporal e salva o artefato reproduzível em
`models_output/modelo_demanda.joblib`.
