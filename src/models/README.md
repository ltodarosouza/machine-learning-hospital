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

O modelo usa `XGBRegressor` (gradient boosting). O medicamento é codificado
como categoria e uma feature `horizonte_dias` permite previsão direta para
cada um dos 7 dias, evitando alimentar uma previsão como entrada da próxima.
As colunas `estoque_disponivel` e `entradas_unidades` são **excluídas** das
features — são efeito de decisões de compra passadas, não causa da demanda
futura, e se mostraram ruído no experimento de comparação abaixo.

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

### Histórico de melhorias (não é a versão original desta Issue)

A primeira versão desta Issue usava `RandomForestRegressor` sobre 2 anos de
dado sintético (2024-2025). Depois da task #13 mostrar uma vantagem pequena e
não unânime do ML sobre o baseline (1.6% de redução de MAE, só 12/20
medicamentos), passamos por três rodadas de melhoria, sempre sob a mesma
metodologia de validação temporal sem vazamento (retreina do zero a cada
janela de teste, só usa `data <= corte`):

**1. Comparação de algoritmos**, ainda com 2 anos de dado — [`scripts/comparar_algoritmos_modelo.py`](../../scripts/comparar_algoritmos_modelo.py):

| Configuração | MAE (unid./dia) | Tempo de treino (4 janelas) |
|---|---|---|
| Random Forest (original desta Issue) | 9.83 | 257s |
| Random Forest sem `estoque_disponivel`/`entradas_unidades` | 9.79 | 238s |
| Random Forest tunado | 9.78 | 421s |
| Gradient Boosting (scikit-learn) | 9.70 | 511s |
| **XGBoost** | **9.64** | **27s** |

XGBoost venceu em precisão **e** foi ~10x mais rápido de treinar — por isso a
troca de algoritmo.

**2. Mais dado histórico + tuning:** estendemos o período sintético de 2 para
4 anos (2022-2025, `src/utils/config.py`) e rodamos um grid search de
hiperparâmetros do XGBoost — [`scripts/tuning_xgboost.py`](../../scripts/tuning_xgboost.py),
18 combinações de `max_depth`/`learning_rate`/`n_estimators`. Melhor
configuração na época: `max_depth=7, learning_rate=0.1, n_estimators=500`
(MAE 9.39 no dataset de 4 anos).

**3. Correção de vazamento na normalização (feito por outra pessoa do time,
em paralelo) mudou os resultados de novo:** `gerar_features_normalizadas`
passou de um z-score global (média/desvio do `df` inteiro recebido) para um
z-score causal por medicamento (só usa observações anteriores à data). Mais
correto — o método antigo não vazava dado *entre treino e teste* na nossa
metodologia de validação (porque sempre chamávamos `gerar_features` só com
`data <= corte`), mas usava uma estatística "global" pouco realista para uso
em produção (ex.: o desvio-padrão da temperatura ao longo de anos, aplicado
igual em qualquer dia). Isso muda os *valores* de 3 features de entrada do
modelo, então precisou de nova comparação de algoritmo e novo tuning:

| Configuração (pós-correção) | MAE (unid./dia) | Tempo de treino |
|---|---|---|
| Random Forest tunado | 9.54 | 1638s |
| XGBoost (hiperparâmetros da rodada 2, não retunados) | 9.56 | 40s |
| **XGBoost retunado** (`max_depth=5, learning_rate=0.1, n_estimators=500`) | **9.43** | **~45s** |

XGBoost retunado continuou a melhor opção — por pouco em precisão frente ao
Random Forest tunado, mas ~35x mais rápido de treinar, o que importa para
quem for iterar mais no modelo depois.

**Atenção ao comparar números entre rodadas 1→2:** estender o período
sintético não é só "adicionar mais linhas no início" — o gerador (Issue #3)
calcula sazonalidade e ruído sobre o array do período inteiro de uma vez, então
mudar o tamanho do array desloca a sequência de números aleatórios e os
valores de consumo **das mesmas datas de calendário mudam** entre a versão de
2 anos e a de 4 anos. Por isso o MAE do baseline também mudou entre rodadas
(9.99 → 9.60) — os percentuais de redução de cada rodada não são comparáveis
entre si, só os valores absolutos de MAE **dentro** da mesma versão de dataset
+ features.

**Resultado final** (dataset de 4 anos, features com normalização causal,
XGBoost retunado), documentado em
[`docs/arquitetura/RESULTADOS_MODELAGEM.md`](../../docs/arquitetura/RESULTADOS_MODELAGEM.md):
MAE agregado de **9.43** unidades/dia, **1.8%** menor que o baseline (9.60),
vencendo em 11 dos 20 medicamentos. É uma vantagem modesta — reportado sem
maquiagem, como todo o resto desta avaliação.

**Por que o ganho é modesto — e o que fazer a respeito:** análise técnica do
time identificou que o gerador sintético atual (`gerar_dataset_sintetico.py`)
não tem fatores latentes persistentes além dos sinais externos diários —
consumo é `média_base(covariáveis) × ruído i.i.d.`, então o previsor
teoricamente ótimo já é a própria média-base, que uma média móvel simples
consegue aproximar quase tão bem quanto um modelo de ML. Mais tuning não
resolve isso; é uma limitação estrutural do dado, não do modelo. Quatro
issues abrem o caminho para corrigir isso, mexendo no gerador (não no
modelo): **#58** (estados latentes de surto com duração), **#59** (corrige
causalidade invertida de `atendimentos_ps`), **#60** (separa demanda
latente de dispensação observada em rupturas) e **#61** (classes de
persistência por medicamento, ruído autocorrelacionado). Depois delas, vale
reabrir esta comparação de algoritmos/tuning para medir o efeito combinado.

**Tamanho do dataset, para contexto:** 1.461 dias (4 anos) × 20 medicamentos =
29.220 linhas brutas; depois do "aquecimento" das médias móveis de 30 dias,
sobram ~1.431 dias por medicamento — o dobro do volume de treino da primeira
versão, mas ainda modesto pelos padrões de ML. Não justifica um modelo com
muito mais parâmetros (ex. rede neural).
