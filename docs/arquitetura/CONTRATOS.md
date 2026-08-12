# Contratos de interface entre módulos

**Preencher em conjunto na reunião de kickoff, antes de cada pessoa sair para trabalhar sozinha na sua branch.** Este é o documento mais importante para o trabalho em paralelo funcionar: cada pessoa vai codar contra o que está aqui, sem esperar o módulo anterior estar pronto. Quando algo aqui muda depois de combinado, quem muda **avisa o time antes de dar merge**, porque quebra o contrato para os módulos seguintes.

Cadeia de dependência: `data_ingestion → features → models → recommendation → dashboard`. `evaluation` consome `models` e `recommendation`.

Quem pegar uma task trabalha com um **mock/exemplo pequeno** do contrato de entrada enquanto a task anterior da cadeia não está pronta (ex.: quem pegar a Issue do modelo cria um CSV de exemplo com o formato combinado abaixo e desenvolve contra ele, sem esperar a Issue de features terminar). Ver a lista completa de tasks na [aba Issues](../../issues).

---

## 0. Escopo do MVP (fechado na Issue #1, 2026-08-12)

- **Hospital/setor fictício:** Pronto-Socorro / Emergência de um hospital fictício. Escolhido porque tem forte ligação com as variáveis externas do projeto (clima, dengue), o que torna a demonstração do valor do modelo mais clara.
- **Região de referência (para dados externos reais):** João Pessoa – PB. O hospital é fictício, mas o clima e a epidemiologia usados para calibrar o dataset sintético vêm de dados reais dessa cidade (ver Issue #2 / `FONTES_DADOS.md`).
- **Período histórico sintético:** 2 anos de dados diários — **2024-01-01 a 2025-12-31** (731 dias), fechado na Issue #6. Constantes em `src/utils/config.py` (`PERIODO_INICIO`, `PERIODO_FIM`) — todo script de geração/ingestão deve importar de lá, nunca hardcodar as datas de novo.
- **Horizonte de previsão:** 7 dias.
- **Prazo de entrega do fornecedor (lead time):** ~7 dias como padrão, variando por medicamento (alguns itens — ex. controlados/adrenalina — têm prazo maior). Definido por medicamento na tabela de referência (seção 1.3).
- **Lista de medicamentos do MVP (20 itens):**

| `medicamento_id` | Nome | Categoria |
|---|---|---|
| `paracetamol` | Paracetamol | Dor/febre |
| `dipirona` | Dipirona | Dor/febre |
| `ibuprofeno` | Ibuprofeno | Dor/febre |
| `soro_fisiologico` | Soro Fisiológico 0,9% | Suporte/hidratação |
| `soro_ringer` | Soro Ringer Lactato | Suporte/hidratação |
| `salbutamol` | Salbutamol (spray/nebulização) | Respiratório |
| `predinisolona` | Predinisolona | Respiratório |
| `hidrocortisona_inj` | Hidrocortisona injetável | Respiratório/alergia |
| `omeprazol_inj` | Omeprazol injetável | Gastro |
| `ondansetrona` | Ondansetrona | Gastro |
| `metoclopramida` | Metoclopramida | Gastro |
| `amoxicilina` | Amoxicilina | Antibiótico |
| `azitromicina` | Azitromicina | Antibiótico |
| `ceftriaxona_inj` | Ceftriaxona injetável | Antibiótico |
| `diclofenaco` | Diclofenaco | Dor/inflamação |
| `tramadol` | Tramadol | Dor |
| `loratadina` | Loratadina | Alergia |
| `soro_antitermico_infantil` | Soro Antitérmico Infantil | Dor/febre (pediátrico) |
| `adrenalina_inj` | Adrenalina injetável | Emergência/controlado |
| `diazepam` | Diazepam | Emergência/controlado |

Categorias `Respiratório` e itens pediátricos devem reagir a `temperatura_media`/`chuva_mm`; nenhum item aqui tem correlação direta esperada com dengue — se quisermos deixar isso mais explícito na demonstração, considerar adicionar um item tipicamente ligado a arboviroses (ex. solução de reidratação oral) numa iteração futura.

## 1. Schema de dados processados (saída de `data_ingestion`, entrada de `features`)

Definido na Issue #1 (kickoff). O dado é dividido em 5 tabelas — evita repetir informação estática (preço, prazo de fornecedor) em toda linha diária, e separa claramente o que é série temporal do que é cadastro/referência.

### 1.1 `data/processed/consumo_diario.csv` — série temporal principal (granularidade: 1 linha por `medicamento_id` por dia)

| Coluna | Tipo | Descrição |
|---|---|---|
| `data` | date (YYYY-MM-DD) | Data da observação |
| `medicamento_id` | string | Chave do medicamento (ver tabela da seção 0) |
| `consumo_unidades` | float | Unidades consumidas no dia — **variável alvo do modelo** |
| `estoque_disponivel` | float | Estoque disponível ao final do dia |
| `entradas_unidades` | float | Unidades recebidas no dia (reposição) |
| `ocupacao_leitos_pct` | float (0–100) | Ocupação de leitos do setor no dia (dado interno sintético) |
| `atendimentos_ps` | int | Número de atendimentos no Pronto-Socorro no dia (dado interno sintético) |

### 1.2 `data/external/externos_diarios.csv` — variáveis externas (granularidade: 1 linha por dia, não por medicamento — aplicam-se à região toda)

| Coluna | Tipo | Descrição |
|---|---|---|
| `data` | date | Data da observação |
| `temperatura_media` | float | Temperatura média do dia, °C (INMET, João Pessoa) |
| `chuva_mm` | float | Precipitação do dia, mm (INMET, João Pessoa) |
| `casos_dengue_regiao` | float | Casos de dengue estimados no dia (InfoDengue, derivado do dado semanal — ver Issue #5) |
| `feriado` | bool | Se o dia é feriado (nacional ou de João Pessoa/PB) |

### 1.3 `data/processed/medicamentos_ref.csv` — cadastro/referência (estático, 1 linha por medicamento)

| Coluna | Tipo | Descrição |
|---|---|---|
| `medicamento_id` | string | Chave do medicamento |
| `nome` | string | Nome completo |
| `categoria` | string | Categoria (ver tabela da seção 0) |
| `prazo_entrega_dias` | int | Lead time do fornecedor para esse item |
| `preco_unitario_reais` | float | Preço médio por unidade, usado no cálculo de economia (task #17/#18) |

### 1.4 `data/processed/lotes.csv` — lotes em estoque, para risco de vencimento

| Coluna | Tipo | Descrição |
|---|---|---|
| `medicamento_id` | string | |
| `lote_id` | string | Identificador do lote |
| `quantidade_atual` | float | Unidades restantes desse lote |
| `data_entrada` | date | Quando o lote entrou no estoque |
| `data_validade` | date | Validade do lote |

### 1.5 `data/processed/pedidos_pendentes.csv` — pedidos já feitos e ainda não recebidos

| Coluna | Tipo | Descrição |
|---|---|---|
| `medicamento_id` | string | |
| `pedido_id` | string | |
| `quantidade` | float | Unidades pedidas |
| `data_pedido` | date | Quando o pedido foi feito |
| `data_prevista_entrega` | date | Quando o fornecedor promete entregar |

### Dataset de modelagem (consolidado pela Issue #7)

Para features/modelo, `consumo_diario.csv` (1.1) e `externos_diarios.csv` (1.2) são unidos por `data` em `data/processed/consumo_medicamentos.csv` — esse é o arquivo que a Issue #7 gera e que as Issues #8–#13 consomem. As tabelas 1.3, 1.4 e 1.5 são consumidas diretamente pelo motor de recomendação (Issues #14–#16), não entram no pipeline de modelagem.

Formato de arquivo: CSV (trocar para parquet depois se performance for um problema — não é esperado ser, no volume do MVP).

## 2. Contrato de entrada/saída de `features`

- **Entrada:** schema da seção 1.
- **Saída:** dataframe com colunas originais + features derivadas (ex.: médias móveis, lags, variáveis sazonais). Nomear features com prefixo claro (ex.: `feat_media_movel_7d`). Documentar aqui a lista final de features geradas.

**Features de calendário e variáveis externas (Issue #9, `src/features/calendario_externas.py`):**

| Feature | Descrição |
|---|---|
| `feat_dia_semana` | Dia da semana (0=segunda ... 6=domingo) |
| `feat_fim_de_semana` | Booleano: sábado ou domingo |
| `feat_mes` | Mês (1-12), sazonalidade anual |
| `feat_feriado` | Cópia de `feriado`, renomeada para o padrão `feat_*` |
| `feat_casos_dengue_lag7` | Casos de dengue de 7 dias atrás (efeito de dengue na demanda é defasado, não imediato) — nulo nos primeiros 7 dias de cada medicamento, tratado na Issue #10 |
| `feat_temperatura_media_norm` | Temperatura normalizada por z-score causal (somente dias anteriores) |
| `feat_chuva_mm_norm` | Chuva normalizada por z-score causal (somente dias anteriores) |
| `feat_casos_dengue_regiao_norm` | Casos de dengue normalizados por z-score causal (somente dias anteriores) |

As features normalizadas usam exclusivamente média e desvio-padrão de datas anteriores do mesmo medicamento, evitando vazamento temporal mesmo quando o pipeline recebe treino e teste juntos.


### Features de série temporal (Issue #8)

Todas as features abaixo são calculadas separadamente por `medicamento_id`,
ordenadas por `data`, e usam somente valores anteriores à data da linha. Por
isso, as primeiras linhas de cada série têm `NaN` quando não há histórico
suficiente. Esses valores serão tratados pela Issue #10.

| Coluna | Definição | Racional |
|---|---|---|
| `feat_lag_1d` | Consumo de 1 dia antes | Captura a demanda mais recente. |
| `feat_lag_7d` | Consumo de 7 dias antes | Captura padrão semanal. |
| `feat_lag_14d` | Consumo de 14 dias antes | Captura recorrência de duas semanas. |
| `feat_media_movel_7d` | Média dos 7 dias anteriores | Suaviza oscilações recentes. |
| `feat_media_movel_14d` | Média dos 14 dias anteriores | Representa o nível de demanda de curto/médio prazo. |
| `feat_media_movel_30d` | Média dos 30 dias anteriores | Representa a tendência de demanda mais estável. |

## 3. Contrato de entrada/saída de `models`

- **Entrada:** saída de `features`, filtrada por `medicamento_id`.
- **Saída esperada por `recommendation`:**

| Coluna | Tipo | Descrição |
|---|---|---|
| `medicamento_id` | string | |
| `data_previsao` | date | Data para a qual a previsão se refere |
| `demanda_prevista` | float | Unidades previstas |
| `intervalo_inferior` | float | Limite inferior do intervalo de confiança (opcional no MVP) |
| `intervalo_superior` | float | Limite superior (opcional no MVP) |

Horizonte de previsão do MVP: **7 dias** (fechado na Issue #1 — ver seção 0).

## 4. Contrato de entrada/saída de `recommendation`

- **Entrada:** saída de `models` (seção 3) + `estoque_disponivel` (tabela 1.1, dado mais recente) + `pedidos_pendentes.csv` (tabela 1.5) + `prazo_entrega_dias` (tabela 1.3) + `lotes.csv` (tabela 1.4, para risco de vencimento).
- **Fórmula base** (ver [docs/negocio/CONTEXTO.md](../negocio/CONTEXTO.md)):
  ```
  compra_recomendada = demanda_prevista + estoque_seguranca - estoque_disponivel - pedidos_confirmados
  ```
- **Saída esperada por `dashboard` e `evaluation`:**

| Coluna | Tipo | Descrição |
|---|---|---|
| `medicamento_id` | string | |
| `compra_recomendada` | float | Unidades recomendadas |
| `risco_falta` | enum(baixo/médio/alto) ou float | |
| `risco_vencimento` | enum(baixo/médio/alto) ou float | |
| `justificativa` | string | Texto explicando a recomendação |

## 5. Contrato de entrada de `dashboard`

- Consome diretamente a saída de `recommendation` (seção 4) + série histórica de `models` (seção 3) para gráficos.
- Definir aqui o(s) arquivo(s)/função(ões) que o dashboard chama para obter esses dados (ex.: `src/recommendation/gerar_recomendacoes() -> pd.DataFrame`).

## 6. Contrato de `evaluation`

- Consome saída de `models` (comparar `demanda_prevista` vs. `consumo_unidades` real) e saída de `recommendation` (simular economia/redução de ruptura vs. baseline).
- Definir aqui o baseline de comparação (ex.: média móvel simples ou ponto de pedido fixo) — ver Issues de baseline (#11) e avaliação (#13).

---

## Histórico de mudanças no contrato

Registrar aqui sempre que um contrato mudar depois de combinado, com data e quem mudou, para rastreabilidade:

| Data | Quem | O que mudou | Módulos afetados |
|---|---|---|---|
| 2026-08-12 | Kickoff (Issue #1) | Fechado escopo do MVP (seção 0) e schema completo em 5 tabelas (seção 1), horizonte de previsão travado em 7 dias | Todos |
| 2026-08-12 | Issue #8 | Documentadas as features temporais (lags e médias móveis) e a manutenção de `NaN` sem histórico suficiente | Features, models, evaluation |
| 2026-08-12 | Issue #4 | Fonte de clima trocada de INMET para Open-Meteo (mesmo contrato de saída, seção 1.2 não muda) — detalhes em `FONTES_DADOS.md` | data_ingestion |
| 2026-08-12 | Issues #3/#7 | Pipeline de dados completo: `data/processed/consumo_medicamentos.csv` (schema da seção 1, consolidado) pronto e commitado — Issues #8+ já podem consumir dado real (sintético) em vez de mock | features, models |
| 2026-08-12 | Correção de normalização | Features externas passaram a usar estatísticas apenas de datas anteriores, eliminando vazamento temporal | features, models, evaluation |
