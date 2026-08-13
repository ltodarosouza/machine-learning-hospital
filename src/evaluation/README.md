# `src/evaluation/`

Métricas de avaliação: precisão dos modelos de previsão (`comparar_modelos.py`), impacto simulado do motor de recomendação (`impacto_simulado.py`, Issue #17) e a decomposição desse impacto por medicamento e mês (`relatorio_operacional.py`, Issue #76).

## Protocolo operacional (Issue #77)

`protocolo_validacao_operacional.py` é a fonte única de verdade para aprovação
de candidatos. Ele gera janelas temporais comuns, consolida as métricas
preditivas e operacionais dos módulos existentes e aplica limites objetivos.
O protocolo completo está em
[`docs/avaliacao/PROTOCOLO_VALIDACAO_OPERACIONAL.md`](../../docs/avaliacao/PROTOCOLO_VALIDACAO_OPERACIONAL.md).

**Comando único recomendado**, que treina o modelo oficial e gera os três relatórios abaixo numa execução só: `python scripts/relatorio_final.py` (ver `src/models/README.md` para detalhes e flags).

## `comparar_modelos.py` (Issue #13) — pronto

Roda o baseline (`src/models/baseline.py`, Issue #11) e o modelo de ML (`src/models/modelo_demanda.py`, Issue #12) sobre o mesmo período de teste e calcula MAE e MAPE, por medicamento e agregado. O modelo de ML é retreinado do zero a cada janela de 7 dias, usando só dado anterior ao corte — nunca olha o "futuro" que está sendo avaliado.

```bash
python src/evaluation/comparar_modelos.py
```

Gera [`docs/arquitetura/RESULTADOS_MODELAGEM.md`](../../docs/arquitetura/RESULTADOS_MODELAGEM.md) com o relatório completo, incluindo uma seção "Reprodutibilidade" (commit, hash do dataset, versões do ambiente, hiperparâmetros — derivados de `src/models/modelo_demanda.py::HIPERPARAMETROS_XGBOOST`, nunca escritos à mão) — regenerar sempre que o dataset ou o modelo mudarem, para o relatório nunca ficar defasado em relação ao código (Issue #54).

**Reprodutibilidade determinística (Issue #75):** o treino usa `n_jobs=1` de propósito — verificamos que `n_jobs=-1` faz o XGBoost produzir modelos diferentes dependendo do número de núcleos da máquina (mesmo com `random_state` fixo), o que causava contagens de "medicamento vencedor" diferentes entre ambientes. Com `n_jobs=1`, duas execuções no mesmo ambiente produzem o relatório byte a byte idêntico (verificado rodando `scripts/relatorio_final.py` duas vezes seguidas). A contagem de vencedores também deixou de ser escrita à mão: `contar_vencedores()` deriva sempre da própria tabela do relatório, coberto por teste em `tests/test_comparar_modelos.py`.

**Resultado atual** (modelo oficial treinado com `quantile_alpha=0.8` desde a Issue #86 — ver abaixo): o modelo de ML reduz o MAE agregado em só **1,8%** frente ao baseline (15,24 vs. 15,52 unidades/dia) e o MAPE piora (28,9% vs. 22,7%), vencendo em **9 dos 20** medicamentos. **Reportado sem maquiagem — e a piora de MAE/MAPE é esperada, não um bug:** o objetivo de treino deixou de ser "acertar em média" (o que MAE mede) e passou a ser "não subestimar os picos" (regressão quantílica), de propósito — são objetivos diferentes, e otimizar um piora ligeiramente o outro. O número que importa para decidir isso é o impacto operacional, não o MAE — ver `impacto_simulado.py` logo abaixo.

**Trade-off documentado, não escondido:** um modelo com MAE pior pode ainda assim ser melhor operacionalmente, porque MAE trata subestimar e superestimar como erros equivalentes, mas só subestimar causa ruptura. Esse foi exatamente o achado da Issue #76 (diagnóstico por medicamento/mês) que motivou a Issue #78 (testar previsão assimétrica) — ver `src/models/README.md` para a cadeia completa de decisões (#76 → #78 → #84 → #86).

Histórico completo das rodadas de melhoria (troca de algoritmo, extensão do dataset, correção de vazamento de normalização, adição de realismo no gerador, retuning, reprodutibilidade): ver [`src/models/README.md`](../models/README.md).

**Por que só 4 janelas (28 dias) de teste:** o modelo de ML é retreinado do zero a cada janela (é o jeito correto de simular "o que o modelo saberia prever, sem olhar o futuro"), o que fica lento com muitas janelas. 28 dias foi uma escolha de custo-benefício para essa task — se o time achar pouco, `avaliar_modelo_periodo` aceita qualquer intervalo de datas.

## `impacto_simulado.py` (Issue #17) — pronto

Simula, dia a dia, uma política de reposição orientada pela previsão de demanda (baseline ou modelo de ML): pede o necessário para cobrir o lead time do fornecedor mais um estoque de segurança, e contabiliza rupturas, compras emergenciais e o custo delas ao preço unitário de referência. Compara os dois métodos mês a mês e no consolidado.

```bash
python src/evaluation/impacto_simulado.py
```

Gera [`docs/arquitetura/RESULTADOS_IMPACTO_SIMULADO.md`](../../docs/arquitetura/RESULTADOS_IMPACTO_SIMULADO.md). **Limitação explícita no próprio relatório:** é simulação sobre dado sintético, não piloto real. O consumo segue FEFO; como o MVP não possui histórico completo de movimentações por lote, ele reconstrói em cada corte um snapshot sintético e determinístico de lotes, cuja quantidade bate com o saldo agregado naquela data e cujas entradas e validades são temporalmente compatíveis com ela. Compras simuladas recebem validade de 365 dias.

**Resultado atual** (modelo `quantile_alpha=0.8`, Issue #86): redução de **31,5%** no custo de compra emergencial e **40,1%** em episódios de ruptura frente ao baseline, no consolidado dos 3 meses simulados — a leitura final do relatório é derivada da própria tabela (`_leitura_trimestral`), nunca escrita à mão, para não ficar contradizendo os números depois que o modelo mudar de novo.

## `relatorio_operacional.py` (Issue #76) — pronto

Os dois relatórios acima só mostram totais agregados — suficiente para saber *que* o modelo de ML piora ruptura/custo em algum lugar, mas não *onde*. Este módulo decompõe as mesmas métricas (MAE, MAPE, viés, subestimação, superestimação, episódios de ruptura, unidades em ruptura, custo de compra emergencial, unidades vencidas) até **medicamento × mês**, calculando previsão e impacto sobre exatamente o mesmo corte temporal (pré-requisito: reprodutibilidade da Issue #75).

```bash
python src/evaluation/relatorio_operacional.py
```

Gera [`docs/arquitetura/RESULTADOS_OPERACIONAL_POR_MEDICAMENTO.md`](../../docs/arquitetura/RESULTADOS_OPERACIONAL_POR_MEDICAMENTO.md), com uma tabela detalhada por mês/medicamento e um destaque separado dos medicamentos que mais pioram e mais melhoram no consolidado (soma da diferença ML − baseline em custo de compra emergencial, episódios de ruptura e unidades vencidas) — para transformar "o agregado piorou" em "estes N medicamentos, nestes meses, respondem pela piora", que é o que orienta a Issue #79 (calibração de política de estoque).

`vies` é o erro médio com sinal (previsto − real): negativo indica subestimação sistemática (o tipo de erro que causa ruptura), positivo indica superestimação sistemática (o tipo que causa compra/vencimento em excesso). `unidades_subestimadas` e `unidades_superestimadas` decompõem o erro absoluto total na direção em que ele ocorreu — um MAE parecido entre baseline e modelo pode esconder uma mudança de direção do erro, por isso as duas colunas nunca são resumidas só no MAE agregado.

## `avaliacao_previsao_assimetrica.py` (Issue #78) — pronto

Testa se penalizar mais a subestimação de demanda (regressão quantílica do XGBoost, `src/models/modelo_demanda_assimetrico.py`, `quantile_alpha > 0.5`) reduz rupturas nos picos, mantendo a política de estoque/compra inalterada. Roda baseline, modelo atual e os candidatos quantílicos nas mesmas quatro janelas oficiais do protocolo da Issue #77 (`gerar_janelas_backtest`) e usa a mesma função `avaliar_aprovacao` para decidir — sem inventar critério novo.

```bash
python src/evaluation/avaliacao_previsao_assimetrica.py
```

Gera [`docs/avaliacao/RESULTADOS_PREVISAO_ASSIMETRICA.md`](../../docs/avaliacao/RESULTADOS_PREVISAO_ASSIMETRICA.md), com métricas por janela e candidato, decomposição de ganhos/perdas por medicamento (sem esconder onde o candidato perde) e duas decisões por candidato: **vs. baseline** (vocabulário literal do protocolo) e **vs. modelo atual** (pergunta operacional — só ela decide se algum candidato substituiria o XGBoost simétrico em produção). Se nenhum candidato for aprovado contra o modelo atual, o relatório recomenda explicitamente mantê-lo (critério de aceite da Issue #78).

Achado da Issue #78: a decisão formal rejeitou os dois candidatos, mas o diagnóstico mostrou que as janelas de 7 dias do protocolo são quase insensíveis a mudança de previsão (prazo de entrega mínimo de 5 dias não dá tempo do pedido chegar dentro da própria janela). Uma simulação contínua complementar (sem reset semanal de estoque) sugeriu forte economia com `quantile_080` — sinal investigado formalmente por `protocolo_janela_longa.py`, abaixo.

## `protocolo_janela_longa.py` (Issue #84) — pronto

Revalida `quantile_080` (o achado promissor da Issue #78) sob uma janela de avaliação de **28 dias** em vez de 7 — dá tempo real do prazo de entrega (5-12 dias) atuar dentro da própria janela, ao contrário da versão 1.0.0 do protocolo. Reaproveita `gerar_janelas_backtest`, `calcular_metricas_janela` e `avaliar_aprovacao` **sem nenhuma alteração de código** — só muda `horizonte_dias` na configuração (versão `1.1.0-janela-longa`, documentada em [`docs/avaliacao/PROTOCOLO_VALIDACAO_OPERACIONAL.md`](../../docs/avaliacao/PROTOCOLO_VALIDACAO_OPERACIONAL.md), seção 13). O modelo continua sendo retreinado a cada 7 dias dentro da janela de 28 (contrato de horizonte do MVP inalterado); só o estoque/lotes deixam de ser resetados a cada semana.

```bash
python src/evaluation/protocolo_janela_longa.py
```

Gera duas decisões auditáveis completas (`janelas.csv`, `metricas.csv`, `configuracao.json`, `decisao.json`, `RELATORIO_VALIDACAO_OPERACIONAL.md`, via `salvar_relatorio_validacao`) em `docs/avaliacao/revalidacao_janela_longa/`: `vs_baseline/` (candidato contra a média móvel) e `vs_modelo_atual/` (candidato contra o modelo em produção — a pergunta operacional real desta issue, com as métricas do modelo atual ocupando o papel de "baseline" que o protocolo exige, documentado nos metadados de cada relatório para não confundir com o baseline literal). Nenhuma decisão da versão 1.0.0 do protocolo é reescrita.

## `avaliacao_politica_estoque.py` (Issue #79) — pronto

Mantém a previsão fixa e testa somente a regra de reposição. Em vez de configurar cada medicamento, aplica buffers compartilhados por **perfil de demanda** (contínuo, intermitente, errático) e **faixa de prazo** (curto/longo). A política conservadora reduziu custo e rupturas na simulação contínua trimestral, para baseline e modelo atual, ao custo de aproximadamente 10% a mais de estoque médio; vencimentos não aumentaram. A política moderada foi descartada porque aumentou unidades em ruptura.

```bash
python -m src.evaluation.avaliacao_politica_estoque
```

Gera [`docs/avaliacao/RESULTADOS_POLITICA_ESTOQUE.md`](../../docs/avaliacao/RESULTADOS_POLITICA_ESTOQUE.md), com grupos, buffers e a validação formal na janela longa v1.1.0. A política ainda não é conectada ao dashboard nem ao motor de recomendação: a aprovação só decide se ela pode seguir para essa discussão de adoção.
