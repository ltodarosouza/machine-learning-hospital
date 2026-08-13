# Protocolo de validação operacional

Versão do protocolo: **1.0.0** — Issue #77.

## 1. Objetivo

Este protocolo é a fonte única de verdade para aprovar ou rejeitar mudanças em
modelos de previsão ou políticas de estoque. Ele resolve o problema de usar
MAE/MAPE isoladamente como evidência de valor: erro preditivo menor não garante
menos rupturas, vencimentos ou compras emergenciais. O protocolo substitui
comparações ad hoc e interpretações manuais por janelas comuns, métricas
reconciliáveis e uma decisão determinística.

Ele é uma validação retrospectiva simulada. Não autoriza compra automática e
não comprova impacto financeiro real.

## 2. Unidade de comparação

- **Baseline:** política/método de referência vigente, atualmente a média móvel
  implementada em `src/models/baseline.py`.
- **Modelo atual:** candidato aprovado mais recente. Enquanto não houver um,
  deve ser reportado como candidato, nunca presumido como referência.
- **Candidato:** modelo ou política sob avaliação, identificado por nome e
  metadados imutáveis da execução.
- **Política de estoque:** conjunto explícito de regras e parâmetros usados por
  `impacto_simulado.py`. Baseline e candidato usam a mesma política, salvo
  quando a própria política é o objeto avaliado; nesse caso, as previsões e os
  demais dados permanecem idênticos.

A comparação é sempre par-a-par por `janela_id`. Não é permitido comparar
períodos, medicamentos, estoques iniciais ou preços diferentes.

## 3. Janelas temporais de backtest

Uma janela contém `janela_id`, `inicio_treino`, `fim_treino`,
`inicio_avaliacao` e `fim_avaliacao`. O treino é expansivo: começa na primeira
data disponível e termina na véspera da avaliação. A avaliação padrão dura o
horizonte do MVP, sete dias. Janelas de avaliação não se sobrepõem.

Regras:

1. Datas devem ser diárias, contínuas e independentes da data atual.
2. `fim_treino < inicio_avaliacao`; dado futuro nunca entra no treino.
3. A mesma tabela de janelas é reutilizada por todos os candidatos.
4. Janelas finais incompletas são descartadas, nunca completadas artificialmente.
5. A ordenação é determinística por data e `janela_id`.

## 4. Quantidade e tamanho mínimos

O padrão exige pelo menos **quatro janelas completas**, equivalentes a 28 dias
de avaliação no horizonte de sete dias, e **365 dias de treino inicial**. Quatro
janelas permitem exigir consistência em 3/4 delas sem declarar vitória por um
único período favorável. Ainda é uma amostra pequena; por isso, menos de quatro
janelas produz `dados_insuficientes`, não uma aprovação com confiança reduzida.

O treino expansivo preserva todo o histórico disponível. O passo padrão é igual
ao horizonte; passo menor é proibido para evitar overlap. Um passo maior é
permitido quando definido antes de observar resultados.

## 5. Agregação e outliers

Todas as métricas são preservadas por janela. A decisão usa:

- soma para custos, episódios, unidades em ruptura, vencimentos e quantidade
  recomendada;
- MAE/MAPE calculados sobre todas as observações do recorte pelo módulo
  canônico;
- comparação percentual agregada e contagem de janelas que atingem a meta.

Não há remoção ou winsorização de outliers: um surto ou ruptura extrema é
operacionalmente relevante. A tabela detalhada permite auditar qualquer valor.

## 6. Métricas obrigatórias

Por candidato e janela:

- **Preditivas:** MAE, MAPE, viés (`previsão - real`), subestimação acumulada e
  superestimação acumulada.
- **Operacionais:** custo de compras emergenciais, episódios de ruptura,
  unidades em ruptura, unidades vencidas e quantidade total recomendada.

`calcular_metricas` é a fonte canônica para MAE/MAPE. O MAPE exclui somente os
dias com consumo real zero do denominador; esses dias continuam no MAE. Uma
janela sem qualquer consumo positivo não produz MAPE finito e é inválida.
`simular_impacto` é a fonte canônica das métricas operacionais. Nenhuma métrica
ausente, `NaN` ou infinita é descartada silenciosamente.

## 7. Regra objetiva de aprovação

Os defaults ficam centralizados em `ConfiguracaoProtocolo`:

- redução agregada mínima do custo emergencial: **10%** (inclusive);
- consistência: meta de 10% atingida em **pelo menos 75%** das janelas válidas;
- aumento relevante máximo em episódios, unidades em ruptura ou vencimentos:
  **5%** no agregado;
- tolerância numérica de empate: `1e-9`;
- mínimo de quatro janelas.

O candidato só é `aprovado` quando todas as condições são satisfeitas
simultaneamente. MAE menor não participa da aprovação; é diagnóstico.

### Definições formais

- **Consistência:** proporção de janelas cujo custo do candidato é pelo menos
  10% menor que o baseline.
- **Aumento relevante:** variação agregada superior a 5% em qualquer métrica
  operacional de bloqueio. Se o baseline é zero e o candidato é positivo, há
  piora relevante.
- **Janela inválida:** métrica obrigatória ausente/não finita, duplicidade de
  `janela_id`, recortes incompatíveis ou custo baseline zero para comparação
  percentual.
- **Empate operacional:** diferença absoluta menor ou igual a `1e-9`; não conta
  como atingimento da meta, mas também não é piora.
- **Dado insuficiente:** menos de quatro pares válidos, baseline agregado com
  custo zero, conjunto de janelas divergente ou entrada incompleta/inválida.

Estados possíveis: `aprovado`, `rejeitado` e `dados_insuficientes`. Entrada
incompleta nunca é aprovada.

## 8. Bloqueios automáticos

- menos de quatro janelas completas;
- janelas diferentes entre baseline e candidato;
- duplicidade de janela;
- coluna obrigatória ausente;
- valor booleano, não numérico, negativo quando proibido, `NaN` ou infinito;
- custo baseline agregado zero;
- qualquer janela com custo baseline zero, pois sua redução percentual é indefinida;
- piora relevante em episódios, unidades em ruptura ou vencimentos;
- redução agregada ou consistência abaixo dos limites.

## 9. Empates e dados ausentes

Empates usam a tolerância única do protocolo. Não há imputação. Métricas
ausentes ou não finitas tornam a decisão `dados_insuficientes`. Uma janela não
pode ser excluída depois de conhecidos os resultados; qualquer exclusão por
problema de origem deve ser documentada antes da avaliação e exige regenerar a
tabela comum de janelas.

## 10. Relatório e rastreabilidade

Cada execução salva:

- `configuracao.json` — versão e limites;
- `janelas.csv` — recortes exatos;
- `metricas.csv` — valores por candidato e janela;
- `decisao.json` — resultado e motivos;
- `RELATORIO_VALIDACAO_OPERACIONAL.md` — visão humana derivada dos anteriores.

Os metadados seguem a Issue #75: commit, hashes dos dados, versões do ambiente,
hiperparâmetros e identificadores das políticas/modelos. Nenhum total ou status
é digitado manualmente no relatório.

> **Transparência financeira:** Os custos apresentados são estimativas
> produzidas com dados sintéticos e preços unitários de referência. Eles não
> representam economia financeira comprovada em uma operação hospitalar real.

## 11. Hipóteses e limitações

- O simulador simplifica compras, lead time, compras emergenciais e validade.
- O snapshot sintético de lotes não reconstrói o inventário físico histórico.
- Dados e preços do MVP são sintéticos/de referência.
- Quatro janelas detectam inconsistência grosseira, mas não substituem validação
  retrospectiva longa ou piloto hospitalar.
- A decisão deste protocolo é consolidada por janela. A decomposição
  complementar por medicamento, mês e tipo de erro está disponível no
  relatório operacional da Issue #76.

## 12. Extensibilidade e versionamento

Novos candidatos apenas acrescentam linhas em `metricas.csv`, mantendo as
mesmas janelas. Novas métricas devem ser calculadas em seu módulo canônico,
adicionadas ao relatório e cobertas por teste de reconciliação; não podem
alterar retroativamente uma decisão da versão 1.0.0. Mudanças de thresholds,
agregação ou bloqueios exigem nova versão do protocolo e registro no histórico
do contrato antes de observar resultados do candidato.

## 13. Versão 1.1.0-janela-longa (Issue #84) — janela de avaliação estendida

A Issue #78 (previsão assimétrica) descobriu uma limitação da versão 1.0.0:
a janela de avaliação (7 dias, igual ao horizonte de previsão do MVP) é
menor que o prazo de entrega mínimo do MVP (5 dias, ver
`data/processed/medicamentos_ref.csv`). Um pedido feito durante a janela
quase nunca chega a tempo de afetar a própria janela avaliada — a ruptura
observada acaba dominada pelo estoque inicial (idêntico para qualquer
candidato), não pela previsão sendo testada. Quantificado no relatório da
Issue #78 (`docs/avaliacao/RESULTADOS_PREVISAO_ASSIMETRICA.md`): em 0 de 80
pares (janela × medicamento), o custo simulado mudou entre candidato e
modelo em produção.

**O que muda:** só o comprimento da *janela de avaliação* — de 7 para 28
dias (`ConfiguracaoProtocolo.horizonte_dias=28`, `src/evaluation/protocolo_janela_longa.py::configuracao_janela_longa`).
Dentro de cada janela de 28 dias, o modelo continua sendo retreinado a cada
7 dias (o contrato de horizonte de previsão do MVP não muda), mas o estoque
e os lotes só são reconstruídos **uma vez** no início da janela — igual à
abordagem já usada pelo relatório de impacto trimestral (Issue #17) e pelo
relatório por medicamento/mês (Issue #76), aplicada agora também à decisão
formal de aprovação.

**O que não muda:** `gerar_janelas_backtest`, `calcular_metricas_janela` e
`avaliar_aprovacao` são reaproveitados sem nenhuma alteração de código. Os
limites de aprovação (redução mínima de 10%, consistência em 75% das
janelas, aumento relevante máximo de 5%) continuam os mesmos da versão
1.0.0 — esta versão muda a janela, não o critério.

**O que não é substituído:** nenhuma decisão da versão 1.0.0 é reescrita.
Os relatórios gerados sob 1.0.0 (incluindo a rejeição de todos os
candidatos na Issue #78) continuam válidos como estavam — a versão
1.1.0-janela-longa é uma revalidação adicional, não uma correção retroativa.

Uso: `python src/evaluation/protocolo_janela_longa.py`. Gera duas decisões
auditáveis em `docs/avaliacao/revalidacao_janela_longa/` — `vs_baseline/`
(candidato contra a média móvel, vocabulário literal do protocolo) e
`vs_modelo_atual/` (candidato contra o modelo atualmente em produção, com
as métricas do modelo atual ocupando o papel de "baseline" que o protocolo
exige — documentado em `papel_de_baseline_nesta_decisao` nos metadados de
cada relatório, para não confundir com o baseline literal).
