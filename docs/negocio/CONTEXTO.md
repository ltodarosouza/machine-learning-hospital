# Contexto do problema

## Origem

O projeto nasceu de uma conversa com uma médica recém-formada, que relata uma dor recorrente nos hospitais: ao mesmo tempo em que existem situações de **falta de medicamentos**, também existem medicamentos que **vencem e são desperdiçados**. Isso não é um problema local — pode existir em hospitais públicos e privados em todo o Brasil.

## Problema

**Hospitais tomam decisões de estoque olhando principalmente para o passado, enquanto a demanda acontece no futuro.**

O hospital precisa decidir quanto comprar, quando comprar e quanto manter em estoque. A demanda muda por causa de surtos, sazonalidade, clima, dengue, doenças respiratórias, ocupação de leitos, feriados, eventos regionais, perfil dos pacientes.

- Compra demais → medicamento parado → vencimento → desperdício financeiro.
- Compra de menos → demanda inesperada → falta → compra emergencial / desabastecimento.

**Importante:** os hospitais já possuem sistemas (Tasy, SOUL MV, AGHU/AGHUx) que registram o que aconteceu. O que falta é uma camada que transforme esses dados em previsão do que provavelmente vai acontecer. Não estamos substituindo a infraestrutura hospitalar — estamos adicionando inteligência sobre ela.

## Quem é afetado

- **Gestor/farmacêutico** (usuário principal): decide quanto comprar sem saber a demanda futura exata.
- **Hospital**: perde dinheiro com vencimentos, estoque excessivo, compras emergenciais, capital parado.
- **Médico**: pode ter dificuldade de tratar o paciente como planejado se o medicamento faltar.
- **Paciente**: sofre as consequências do desabastecimento.
- **Comprador da solução**: provavelmente uma camada mais alta da administração hospitalar.

## Solução

Fluxo: **Dados → previsão de demanda → análise do estoque → recomendação → decisão do gestor.**

O modelo não deve apenas dizer "a demanda vai aumentar" — deve virar algo acionável:
> "A demanda provavelmente aumentará. Considerando estoque atual, validade e prazo do fornecedor, recomendamos comprar X unidades até tal data."

**Decisão de produto:** a IA recomenda, o profissional decide (aceitar, alterar ou rejeitar). Não há compra automática.

### Fórmula simplificada de recomendação de compra

```
Compra recomendada = demanda prevista + estoque de segurança − estoque disponível − pedidos confirmados
```

## Dados

**Internos:** histórico de consumo, dispensações, estoque atual, entradas/saídas, validade, lotes, internações, atendimentos, diagnósticos, ocupação de leitos, compras, pedidos em andamento, prazo dos fornecedores.

**Externos:** temperatura, chuvas, sazonalidade, incidência de doenças, surtos epidemiológicos, feriados, grandes eventos, tendências regionais.

**Ponto técnico:** o modelo deve prever diretamente o **consumo de medicamentos**. Variáveis externas (dengue, clima, etc.) entram como variáveis explicativas, não como alvo.

**Fontes públicas candidatas para simular/enriquecer dados no MVP:** DATASUS/OpenDataSUS (internações, epidemiologia), INMET (clima), InfoDengue (arboviroses), calendário de feriados. Dados hospitalares reais provavelmente não estarão disponíveis — o MVP deve assumir dados sintéticos/públicos calibrados para serem realistas, deixando isso explícito.

## MVP

`1 hospital → 1 setor → 10–30 medicamentos → previsão de 7–14 dias`, comparando método atual (ex.: média histórica / ponto de pedido fixo) vs. previsão do modelo.

## Métricas de validação

- **Precisão:** previsão vs. consumo real (ex.: MAE, MAPE).
- **Redução de vencimentos:** menos medicamento vencido.
- **Redução de faltas:** menos episódios de ruptura.
- **Compras emergenciais evitadas.**
- **Economia estimada (R$).**

## Cuidado com números de impacto

Evitar afirmações genéricas não verificáveis como "hospitais perdem 10% do estoque" ou "R$ 1 bilhão perdido por vencimento". Tratar como **cenários hipotéticos**, com fonte e escopo explícitos. Exemplo de framing seguro:

Tabela detalhada com premissas, fontes e validação pendente: [`CENARIOS_IMPACTO.md`](CENARIOS_IMPACTO.md).

| Cenário | Perda evitável | Redução pela solução | Economia (hospital com R$10mi/ano em medicamentos) |
|---|---|---|---|
| Conservador | 2% | 20% | R$ 40 mil |
| Provável | 5% | 30% | R$ 150 mil |
| Otimista | 10% | 40% | R$ 400 mil |

> "Ainda não temos um piloto, então trabalhamos com cenários. Em um hospital que movimenta R$ 10 milhões em medicamentos, se 5% representar perdas evitáveis e reduzirmos apenas 30% delas, o impacto potencial seria de R$ 150 mil por ano."

## Perguntas que a equipe precisa saber responder (banca)

1. Como sabemos que o desperdício é causado principalmente por erro de previsão?
2. Por que machine learning e não uma média histórica ou regra de estoque simples?
3. Hospitais já têm sistemas de gestão — por que precisam de nós?
4. Como conseguiremos os dados (reais vs. sintéticos)?
5. O modelo prevê doenças ou medicamentos? (Resposta: medicamentos; doenças/clima são variáveis explicativas.)
6. E se a IA errar e faltar medicamento? (Resposta: recomendação, não decisão automática; estoque de segurança.)
7. Quem paga pela solução?
8. Como provaremos que funciona, sem piloto real?
9. O que impede Tasy/MV/etc. de fazerem isso internamente?
10. Quanto dinheiro conseguimos realmente economizar para um hospital?

## Tese em uma frase

> Hospitais tomam decisões de estoque olhando para o passado; nossa plataforma usa dados internos e externos para prever a demanda futura e recomendar quando e quanto comprar, reduzindo simultaneamente falta e desperdício de medicamentos.
