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

**Objetivo de treino (Issue #86):** regressão quantílica (`objective="reg:quantileerror"`,
`quantile_alpha=QUANTILE_ALPHA_OFICIAL`, atualmente `0.8`), não erro quadrático
médio. `treinar_modelo`/`avaliar_validacao_temporal` usam esse padrão
automaticamente quando `quantile_alpha` não é informado; passe
`quantile_alpha=None` explicitamente para reproduzir o objetivo simétrico
anterior à Issue #86 (histórico, só para comparação — não é mais o padrão de
produção). Motivação e resultado completos na seção "Adoção da previsão
assimétrica" abaixo.

```bash
python src/models/modelo_demanda.py
```

O comando executa uma validação temporal e salva o artefato **de verdade
reproduzível** em `models_output/modelo_demanda.joblib` — reproduzível aqui
quer dizer especificamente que ele carrega em qualquer outro processo
Python, não só no que o treinou (ver `artefato.py` abaixo e o teste
`tests/test_artefato_modelo.py`, que executa esse comando via subprocesso e
carrega o resultado no processo do pytest).

### `artefato.py` (Issue #52) — pronto

Isola a dataclass `ModeloDemanda` e as funções `salvar_modelo`/`carregar_modelo`
num módulo que **nunca** é executado como script. Motivo: `python src/models/modelo_demanda.py`
faz o Python tratar aquele arquivo como o módulo `__main__` — se uma classe
serializável fosse definida ali (como estava antes desta correção), o
pickle grava `__module__ == "__main__"`, e qualquer processo novo que
importe `src.models.modelo_demanda` normalmente falha ao carregar com
`AttributeError: module '__main__' has no attribute 'ModeloDemanda'`. Foi
exatamente esse bug que aconteceu neste projeto. `salvar_modelo`/`carregar_modelo`
continuam acessíveis via `src.models.modelo_demanda` (reexportados) — nenhum
código que já os importava dali precisa mudar.

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

### Rodada de retuning pós #58-#61 (todas as 4 issues de realismo do gerador já prontas)

Depois que #58, #59, #60 e #61 mudaram a estrutura do gerador sintético
(estados latentes de surto, causalidade dos atendimentos, censura de demanda
por ruptura, ruído autocorrelacionado por medicamento), os hiperparâmetros
antigos (`max_depth=5`) ficaram desatualizados — foram escolhidos para um
processo gerador bem mais simples. Retunamos de novo
(`scripts/tuning_xgboost.py`, 18 combinações, mesma metodologia de validação
temporal sem vazamento): melhor config agora é `max_depth=7,
learning_rate=0.1, n_estimators=500` (só a profundidade mudou).

**Resultado de precisão** ([`docs/arquitetura/RESULTADOS_MODELAGEM.md`](../../docs/arquitetura/RESULTADOS_MODELAGEM.md),
gerado por `python scripts/relatorio_final.py`): MAE agregado de **14,15**
unidades/dia, **8,8%** menor que o baseline (15,52), vencendo em **16 dos 20**
medicamentos. O MAE absoluto **não é comparável** ao de antes dessas 4
issues (era ~9-10) — o dataset ficou estruturalmente mais variável (surtos,
demanda censurada), então um MAE maior aqui não é o modelo piorando, é o
problema ficando mais difícil e mais realista.

**Achado da rodada anterior — ainda parcialmente relevante:** com o MAE
melhor, a simulação de impacto operacional
([`docs/arquitetura/RESULTADOS_IMPACTO_SIMULADO.md`](../../docs/arquitetura/RESULTADOS_IMPACTO_SIMULADO.md))
mostra o modelo de ML gerando mais episódios de ruptura que o baseline no
trimestre simulado, embora o custo agregado tenha ficado praticamente
empatado nesta rodada (com dados corrigidos — ver Issue #75 abaixo). Isso é
contraintuitivo (\"o modelo prevê melhor em média, mas causa mais falta na
prática\"), mas tem uma explicação plausível: **MAE mede erro médio ao longo
de todos os dias, mas ruptura é causada especificamente por
subestimar picos** (dias de surto). Um modelo pode ter erro médio menor e
ainda assim errar mais nos poucos dias que realmente importam para o
motor de recomendação (subestimar demanda de surto = estoque insuficiente =
ruptura), porque otimizar MAE não é a mesma coisa que otimizar para não
faltar estoque — esses dois objetivos podem divergir, e aqui parecem estar
divergindo. As Issues #76-#78 (diagnóstico por medicamento/mês, objetivo
operacional formal, treino com perda assimétrica) foram abertas
especificamente para investigar e endereçar isso.

### Adoção da previsão assimétrica (Issue #86)

A Issue #78 testou candidatos de regressão quantílica (`quantile_alpha=0.6`
e `0.8`) contra o modelo simétrico acima, nas janelas oficiais do protocolo
(Issue #77) — nenhum foi aprovado, mas o diagnóstico revelou por quê: a
janela de avaliação de 7 dias é menor que o prazo de entrega mínimo do MVP
(5 dias), então quase nenhum pedido feito durante a janela chega a tempo de
afetar a própria janela avaliada. A Issue #84 estendeu a janela de
avaliação para 28 dias (mantendo o retreino do modelo a cada 7 dias — o
contrato de horizonte do MVP não muda) e revalidou `quantile_alpha=0.8`
formalmente: **aprovado**, com redução de 33% no custo de compra
emergencial e 46% em episódios de ruptura frente ao modelo simétrico, sem
piora de vencimento, consistente em 4 de 4 janelas
(`docs/avaliacao/revalidacao_janela_longa/vs_modelo_atual/decisao.json`).

A Issue #86 promoveu esse resultado a padrão de produção: `modelo_demanda.py::treinar_modelo`
passou a usar `quantile_alpha=QUANTILE_ALPHA_OFICIAL` (`0.8`) por padrão —
todo consumidor que já chamava `treinar_modelo`/`avaliar_validacao_temporal`
sem especificar o objetivo (dashboard, `comparar_modelos.py`,
`impacto_simulado.py`, `relatorio_operacional.py`, `scripts/relatorio_final.py`)
passou a treinar com o novo objetivo automaticamente, sem precisar de
nenhuma outra mudança de código. `quantile_alpha=None` continua disponível
para reproduzir o objetivo simétrico anterior, só para comparação histórica.

## `modelo_demanda_assimetrico.py` (Issue #78) — candidato experimental

**Nota (Issue #86):** `quantile_alpha=0.8` já é o padrão de produção em
`modelo_demanda.py` (seção acima) — este módulo continua existindo para
testar *outros* valores de `quantile_alpha` como candidatos futuros contra
o modelo oficial (agora ele mesmo quantílico), fora do escopo da Issue #86.

Testa a hipótese acima (MAE não é a métrica certa para evitar ruptura,
porque trata subestimar e superestimar igual) treinando com regressão
quantílica do XGBoost (`objective="reg:quantileerror"`, `quantile_alpha`
entre 0.5 e 1.0 exclusive) em vez de erro quadrático médio. `quantile_alpha`
acima de 0.5 desloca a previsão para cima da mediana condicional — reduz a
frequência de subestimar, ao custo de superestimar mais nos dias comuns.

Reaproveita toda a estrutura de `modelo_demanda.py` (preparação de dados,
codificação de medicamento, artefato `ModeloDemanda`, `prever_demanda`) — só
troca a função de perda do `XGBRegressor`. **Nunca** grava
`models_output/modelo_demanda.joblib`; esse artefato continua vindo
exclusivamente do modelo oficial. `src/evaluation/avaliacao_previsao_assimetrica.py`
avalia os candidatos nas mesmas quatro janelas oficiais do protocolo da
Issue #77 e usa a mesma função `avaliar_aprovacao` — contra o baseline
(vocabulário literal do protocolo) e contra o modelo atual (pergunta
operacional: o candidato substituiria o que está em produção?). Resultado
em [`docs/avaliacao/RESULTADOS_PREVISAO_ASSIMETRICA.md`](../../docs/avaliacao/RESULTADOS_PREVISAO_ASSIMETRICA.md).

```bash
python src/evaluation/avaliacao_previsao_assimetrica.py
```

### Reprodutibilidade da avaliação (Issue #75)

Duas execuções da avaliação, no mesmo commit e mesmo ambiente, chegavam a
contar números diferentes de "medicamento vencedor" (uma vez 14, outra 11,
outra 16, dependendo de quem/quando rodava). Causa raiz identificada e
corrigida:

1. **`n_jobs=-1` não é reprodutível entre máquinas.** XGBoost com
   `tree_method="hist"` (o padrão) não é invariante ao número de threads
   mesmo com `random_state` fixo — verificamos empiricamente que treinar o
   mesmo modelo, no mesmo dado, com `n_jobs=-1` vs. `n_jobs=1` produzia
   previsões divergindo em ~60 unidades. Como `n_jobs=-1` usa "todos os
   núcleos disponíveis", máquinas diferentes (números de núcleos diferentes)
   literalmente treinam modelos diferentes. Corrigido: `n_jobs=1` fixo em
   `HIPERPARAMETROS_XGBOOST`. Mais lento (~2x por treino), mas garantidamente
   igual em qualquer máquina — verificamos rodando `scripts/relatorio_final.py`
   duas vezes seguidas e comparando os relatórios gerados: **byte a byte
   idênticos**.
2. **A contagem de "vencedores" era só inferida do texto/tabela por quem
   lia o relatório, nunca calculada e citada automaticamente** — isso é o
   que permitiu a divergência (14 vs. 11 vs. 16) passar despercebida por um
   tempo. Corrigido: `contar_vencedores()` em `comparar_modelos.py` deriva a
   contagem da própria tabela de métricas, e o texto do relatório cita esse
   valor diretamente — nunca mais escrito à mão. Coberto por teste
   (`tests/test_comparar_modelos.py`).
3. **Hiperparâmetros duplicados** entre `modelo_demanda.py` (código) e o
   texto de `comparar_modelos.py` (string solta) — já tinham ficado
   desatualizados 2 vezes neste projeto. Corrigido: `HIPERPARAMETROS_XGBOOST`
   é agora a única fonte, importada por quem precisar descrever os
   hiperparâmetros.
4. O relatório agora também registra **hash SHA256 do dataset avaliado** e
   **versões de Python/pandas/numpy/scikit-learn/xgboost**, para dois
   relatórios só serem comparáveis se vieram do mesmo dado e do mesmo
   ambiente — `requirements.txt` também foi fixado com versões exatas (antes
   estava sem pin, e listava `prophet`, que nunca chegou a ser usado no
   código).

**Comando único para reproduzir os três relatórios de avaliação com o modelo
oficial retreinado:** `python scripts/relatorio_final.py` (ver
[`scripts/relatorio_final.py`](../../scripts/relatorio_final.py) — treina o
modelo, gera os relatórios de precisão, impacto simulado e detalhamento por
medicamento/mês numa execução só; `--regenerar-dados` reconstrói o dataset
antes; `--abrir-dashboard` abre o Streamlit ao final).

**Tamanho do dataset, para contexto:** 1.461 dias (4 anos) × 20 medicamentos =
29.220 linhas brutas; depois do "aquecimento" das médias móveis de 30 dias,
sobram ~1.431 dias por medicamento — o dobro do volume de treino da primeira
versão, mas ainda modesto pelos padrões de ML. Não justifica um modelo com
muito mais parâmetros (ex. rede neural).
