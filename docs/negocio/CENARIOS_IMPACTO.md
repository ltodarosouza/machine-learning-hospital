# Cenários de impacto financeiro

Este documento registra a tabela de cenários da Issue #18 para uso no pitch. A leitura correta é: **ainda não existe piloto real**, então os valores abaixo são hipóteses financeiras explícitas, calculadas sobre um hospital-tipo, e não uma promessa de economia garantida.

## Base da extrapolação

Fórmula usada:

```text
Economia anual potencial = gasto anual com medicamentos x perda evitável x redução da perda pela solução
```

Hospital-tipo usado para o pitch: **R$ 10.000.000 por ano em medicamentos**. Essa escala não vem de dado real do MVP; é uma premissa de apresentação definida na Issue #18 e já usada como exemplo seguro em `docs/negocio/CONTEXTO.md`. Se o time obtiver orçamento real de um hospital, a tabela deve ser recalculada com o valor real.

## Resultado de simulação usado como referência

A simulação da Issue #17 compara baseline de média móvel contra o modelo de ML no período de 2025-12-04 a 2025-12-31, sobre dados sintéticos. O relatório completo está em `docs/arquitetura/RESULTADOS_IMPACTO_SIMULADO.md`.

| Métrica da Issue #17 | Baseline | Modelo ML | Redução | Leitura para a Issue #18 |
|---|---:|---:|---:|---|
| Episódios de ruptura | 86,00 | 93,00 | -8,1% | O modelo ainda não reduziu rupturas nesse recorte. |
| Unidades em ruptura | 2.697,67 | 2.747,92 | -1,9% | A diferença operacional ainda é instável. |
| Compras emergenciais, em unidades | 2.697,67 | 2.747,92 | -1,9% | Não usar como prova de redução de faltas. |
| Custo de compras emergenciais | R$ 6.944,36 | R$ 6.924,01 | R$ 20,36 (0,3%) | Economia positiva, mas pequena e sintética. |
| Unidades vencidas | 0,00 | 0,00 | sem base percentual | Não há evidência de redução de vencimento nesse período. |

Conclusão para o pitch: a Issue #17 serve como evidência de que já existe uma forma reprodutível de medir impacto, mas **não sustenta sozinha** afirmar redução operacional de 20%, 30% ou 40%. Esses percentuais entram na tabela abaixo como cenários de negócio a validar com dado real ou piloto retrospectivo.

## Tabela de cenários

| Cenário | Gasto anual com medicamentos | Perda evitável assumida | Valor anual da perda evitável | Redução assumida pela solução | Economia anual potencial | Fonte dos números |
|---|---:|---:|---:|---:|---:|---|
| Conservador | R$ 10.000.000 | 2% | R$ 200.000 | 20% | R$ 40.000 | Gasto: premissa de hospital-tipo da Issue #18. Perda e redução: premissas conservadoras do time, iguais ao framing de `CONTEXTO.md`. |
| Provável | R$ 10.000.000 | 5% | R$ 500.000 | 30% | R$ 150.000 | Gasto: premissa de hospital-tipo da Issue #18. Perda e redução: cenário central do time, ainda sem piloto real. |
| Otimista | R$ 10.000.000 | 10% | R$ 1.000.000 | 40% | R$ 400.000 | Gasto: premissa de hospital-tipo da Issue #18. Perda e redução: limite superior hipotético do time, exige validação forte antes do pitch. |

## Fonte de cada premissa

| Número ou premissa | Valor | Fonte | Observação |
|---|---:|---|---|
| Gasto anual do hospital-tipo | R$ 10.000.000 | Premissa do time, definida na Issue #18 e já esboçada em `docs/negocio/CONTEXTO.md` | Serve só para extrapolação. Trocar por orçamento real quando existir. |
| Perda evitável conservadora | 2% | Premissa do time | Não apresentar como estatística de mercado. |
| Perda evitável provável | 5% | Premissa do time | Hipótese central para conversa de pitch, não dado observado. |
| Perda evitável otimista | 10% | Premissa do time | Usar apenas como teto hipotético. |
| Redução conservadora pela solução | 20% | Premissa do time | A Issue #17 ainda não comprova esse nível de redução. |
| Redução provável pela solução | 30% | Premissa do time | Depende de validação com dados reais ou piloto retrospectivo. |
| Redução otimista pela solução | 40% | Premissa do time | Requer evidência mais forte antes de ser defendida como caso esperado. |
| Economia simulada em compras emergenciais | R$ 20,36 no recorte de 28 dias | Resultado da Issue #17 em `docs/arquitetura/RESULTADOS_IMPACTO_SIMULADO.md` | Resultado sintético e pequeno; não foi extrapolado diretamente para a tabela anual. |
| Redução simulada de custo emergencial | 0,3% | Resultado da Issue #17 em `docs/arquitetura/RESULTADOS_IMPACTO_SIMULADO.md` | Mostra sinal positivo mínimo, não impacto comercial validado. |

## Como falar na banca

Formulação segura:

> "Ainda não temos piloto real. Por isso, trabalhamos com cenários. Em um hospital que movimenta R$ 10 milhões por ano em medicamentos, se 5% desse valor representar perdas evitáveis e a solução reduzir 30% dessas perdas, o impacto potencial seria de R$ 150 mil por ano."

Evitar:

- "A solução economiza R$ 150 mil por ano."
- "Hospitais perdem 5% do estoque."
- "O modelo já reduz 30% das perdas."

## Perguntas críticas antes do pitch

| Pergunta | Resposta honesta hoje |
|---|---|
| Como sabemos que a perda é causada por erro de previsão? | Ainda não sabemos. A tabela fala em perda evitável associada ao processo de estoque, não em toda perda hospitalar. |
| Por que ML e não média histórica? | A modelagem atual tem ganho modesto de erro e a simulação da #17 ainda não mostra ganho operacional consistente. A tese técnica é que variáveis externas e demanda futura podem melhorar decisões em cenários reais mais ricos, mas isso precisa ser validado. |
| A economia de R$ 150 mil é promessa? | Não. É o cenário provável sob as premissas de 5% de perda evitável e 30% de redução. |
| Como provar sem piloto real? | Próximo passo: validação retrospectiva com dados reais de consumo, estoque, compras emergenciais e vencimentos de um hospital parceiro. |
| O que fazer se questionarem a simulação da #17? | Dizer que ela demonstra a metodologia de medição, mas ainda não é evidência comercial suficiente. |

## Validação pendente com o time

- [ ] Confirmar se R$ 10.000.000/ano é uma escala aceitável para "hospital-tipo" no pitch.
- [ ] Confirmar se os percentuais 2% / 5% / 10% passam como hipóteses defensáveis de perda evitável.
- [ ] Confirmar se os percentuais 20% / 30% / 40% passam como hipóteses defensáveis de redução pela solução.
- [ ] Garantir que o material de pitch usa a formulação de cenário, sem transformar hipótese em promessa.
