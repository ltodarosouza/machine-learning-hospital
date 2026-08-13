# Contratos de interface entre módulos

**Preencher em conjunto na reunião de kickoff, antes de cada pessoa sair para trabalhar sozinha na sua branch.** Este é o documento mais importante para o trabalho em paralelo funcionar: cada pessoa vai codar contra o que está aqui, sem esperar o módulo anterior estar pronto. Quando algo aqui muda depois de combinado, quem muda **avisa o time antes de dar merge**, porque quebra o contrato para os módulos seguintes.

Cadeia de dependência: `data_ingestion → features → models → recommendation → dashboard`. `evaluation` consome `models` e `recommendation`.

Quem pegar uma task trabalha com um **mock/exemplo pequeno** do contrato de entrada enquanto a task anterior da cadeia não está pronta (ex.: quem pegar a Issue do modelo cria um CSV de exemplo com o formato combinado abaixo e desenvolve contra ele, sem esperar a Issue de features terminar). Ver a lista completa de tasks na [aba Issues](../../issues).

---

## 0. Escopo do MVP (fechado na Issue #1, 2026-08-12)

- **Hospital/setor fictício:** Pronto-Socorro / Emergência de um hospital fictício. Escolhido porque tem forte ligação com as variáveis externas do projeto (clima, dengue), o que torna a demonstração do valor do modelo mais clara.
- **Região de referência (para dados externos reais):** João Pessoa – PB. O hospital é fictício, mas o clima e a epidemiologia usados para calibrar o dataset sintético vêm de dados reais dessa cidade (ver Issue #2 / `FONTES_DADOS.md`).
- **Período histórico sintético:** 4 anos de dados diários — **2022-01-01 a 2025-12-31** (1.461 dias). Fechado inicialmente em 2 anos na Issue #6, estendido para 4 anos depois da Issue #13 mostrar uma vantagem pequena do modelo de ML sobre o baseline (mais histórico = mais ciclos sazonais para o modelo aprender). Constantes em `src/utils/config.py` (`PERIODO_INICIO`, `PERIODO_FIM`) — todo script de geração/ingestão deve importar de lá, nunca hardcodar as datas de novo.
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
| `consumo_unidades` | float | Demanda latente no dia: unidades que seriam consumidas se houvesse estoque suficiente — **variável alvo do modelo** |
| `dispensacao_unidades` | float | Unidades efetivamente dispensadas no dia; nunca supera `consumo_unidades` nem o saldo disponível antes da saída. |
| `demanda_nao_atendida` | float | Parte da demanda latente não dispensada por ruptura. Vale `consumo_unidades - dispensacao_unidades`. |
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

**Invariante de inventário (Issue #53):** para cada `medicamento_id`, a soma de `quantidade_atual` em `lotes.csv` deve ser igual a `estoque_disponivel` do último dia em `consumo_diario.csv` (tabela 1.1), a menos de uma tolerância de arredondamento de **no máximo 1 unidade** (`TOLERANCIA_INVENTARIO_UNIDADES` em `gerar_dataset_sintetico.py`) — os dois representam o mesmo estoque físico, só que quebrado por lote de um lado e agregado do outro. `validar_lotes()` verifica isso automaticamente sempre que o dataset é gerado. Antes desta correção, essa invariante não era garantida: dois medicamentos tinham a quantidade dos lotes sobrescrita para criar exemplos "dramáticos" de risco (ver histórico de mudanças no fim deste arquivo).

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

**Semântica de ruptura (Issue #60):** o modelo prevê `consumo_unidades`, isto é, a demanda que o hospital precisa atender, e não a dispensação observada que pode estar censurada por falta de estoque. `dispensacao_unidades` e `demanda_nao_atendida` são sinais operacionais para auditoria de ruptura e para a avaliação de impacto; não são features preditivas do modelo atual.

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
- A `demanda_prevista` diária é somada por medicamento no horizonte de 7 dias antes do cálculo da recomendação.
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

### Classificação canônica de `risco_falta`

O risco usa a cobertura do estoque disponível, sem somar pedidos pendentes:

```
demanda_diaria = demanda_prevista_no_horizonte / dias_do_horizonte
cobertura_dias = estoque_disponivel / demanda_diaria
```

| Nível | Regra |
|---|---|
| `alto` | `cobertura_dias <= prazo_entrega_dias` |
| `médio` | `prazo_entrega_dias < cobertura_dias <= 1,5 × prazo_entrega_dias` |
| `baixo` | `cobertura_dias > 1,5 × prazo_entrega_dias` |

Demanda diária zero sempre resulta em risco `baixo`. Quando o prazo não é
fornecido, o fallback temporário é `alto` se há compra recomendada e `baixo`
caso contrário; nesse cenário não há informação suficiente para classificar
o nível intermediário.

## 5. Contrato de entrada de `dashboard`

- Consome a saída de `recommendation` (seção 4) + série histórica de `models` (seção 3) para gráficos.
- A aplicação carrega o artefato oficial salvo em `models_output/modelo_demanda.joblib`; não treina uma segunda configuração do modelo ao iniciar. O artefato é produzido e validado por `scripts/rodar_pipeline_completo.py`.
- Para apresentar o resultado, o dashboard enriquece a saída do motor com `nome` e `categoria` de `medicamentos_ref.csv`. Esses dois campos pertencem ao cadastro, não à saída de `recommendation`.
- Função do motor: `src/recommendation/motor_recomendacao.py::gerar_recomendacoes(previsoes, estoque_atual, estoque_seguranca, pedidos_pendentes, medicamentos_referencia, lotes) -> pd.DataFrame`.

## 6. Contrato de `evaluation`

- Consome saída de `models` (comparar `demanda_prevista` vs. `consumo_unidades` real) e saída de `recommendation` (simular economia/redução de ruptura vs. baseline).
- Definir aqui o baseline de comparação (ex.: média móvel simples ou ponto de pedido fixo) — ver Issues de baseline (#11) e avaliação (#13).
- O protocolo de aprovação da Issue #77 é implementado em
  `src/evaluation/protocolo_validacao_operacional.py`. Baseline e candidato
  devem fornecer uma linha por `janela_id`, nas mesmas janelas, com MAE, MAPE,
  viés, subestimação, superestimação, custo emergencial, episódios/unidades em
  ruptura, unidades vencidas e quantidade recomendada. A decisão retorna
  `aprovado`, `rejeitado` ou `dados_insuficientes`; entradas incompletas nunca
  são aprovadas. A especificação versionada está em
  `docs/avaliacao/PROTOCOLO_VALIDACAO_OPERACIONAL.md`.

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
| 2026-08-12 | Issues #15/#24 | Definida a agregação da demanda prevista no horizonte e publicada a função base do motor de recomendação | recommendation, dashboard, evaluation |
| 2026-08-12 | Issue #20 | Dashboard passou a executar o pipeline real; `nome` e `categoria` foram formalizados como enriquecimento de apresentação via cadastro | dashboard, recommendation |
| 2026-08-12 | Issue #50 | Consolidada a suíte canônica do motor e documentadas as fronteiras de `risco_falta` em três níveis | recommendation, dashboard |
| 2026-08-12 | Melhoria pós-#13 | Período histórico estendido de 2 para 4 anos (2022-01-01 a 2025-12-31, 1.461 dias) — mais ciclos sazonais para o modelo aprender. Todos os dados externos/sintéticos regenerados (`data/external/*`, `data/processed/*`). Quem já tinha o dataset antigo localmente deve rodar `git pull` e conferir os arquivos em `data/` de novo | Todos |
| 2026-08-12 | Issue #53 | Formalizada a invariante soma(lotes) == estoque_disponivel (tabela 1.4); risco de vencimento não depende mais de `prazo_entrega_dias`, compara cada lote ao consumo esperado até sua validade. `lotes.csv` regenerado — quem tinha o dataset local deve rodar `git pull` de novo | data_ingestion, recommendation, dashboard |
| 2026-08-12 | Issue #58 | Adicionados estados latentes persistentes de surto (cadeia de Markov, 2 processos compartilhados por categoria sensível) na geração de `consumo_unidades` — episódios de dias/semanas em vez de só ruído i.i.d. Schema não muda, mas os valores de `consumo_diario.csv`/`consumo_medicamentos.csv`/`lotes.csv`/`pedidos_pendentes.csv` mudam (mesma seed, lógica diferente) — quem tinha o dataset local deve rodar `git pull` de novo. Comparação de algoritmos/tuning do modelo NÃO foi re-executada (fora do escopo desta issue) | data_ingestion, models, evaluation |
| 2026-08-12 | Issue #59 | `atendimentos_ps`/`ocupacao_leitos_pct` passaram a ser gerados antes do consumo (a partir de clima/dengue/surto), e o consumo por medicamento passou a depender dos atendimentos — corrige a causalidade invertida que existia antes | data_ingestion, models, evaluation |
| 2026-08-12 | Issue #60 | `consumo_unidades` foi formalizado como demanda latente. Adicionadas `dispensacao_unidades` e `demanda_nao_atendida` para tornar rupturas auditáveis, sem censurar o alvo do modelo | data_ingestion, models, evaluation |
| 2026-08-12 | Issue #61 | Cada medicamento passou a ter um "perfil de persistência" (contínuo/intermitente/errático, derivado da categoria) que controla a memória do ruído de curto prazo (AR(1) em vez de log-normal i.i.d.). Schema não muda (`_perfil_persistencia` é interno ao gerador, não vai para `medicamentos_ref.csv`), mas os valores de `consumo_diario.csv`/`consumo_medicamentos.csv`/`lotes.csv`/`pedidos_pendentes.csv` mudam de novo (mesma seed, lógica diferente) — `git pull` de novo para quem tinha o dataset local | data_ingestion, models, evaluation |
| 2026-08-12 | Issue #25 | Formalizado o pipeline fim a fim: o dashboard passa a consumir o mesmo artefato serializado que foi treinado e validado pelo pipeline, eliminando o retreino implícito com outra configuração | models, recommendation, dashboard |
| 2026-08-12 | Retuning pós #58-#61 | Hiperparâmetros do XGBoost retunados (`max_depth` 5→7) depois que as 4 issues de realismo do gerador mudaram a estrutura do dataset. Adicionado `scripts/relatorio_final.py`, comando único que retreina o modelo e gera os relatórios de precisão (`RESULTADOS_MODELAGEM.md`) e de impacto simulado (`RESULTADOS_IMPACTO_SIMULADO.md`) juntos, para eles nunca mais ficarem dessincronizados entre si ou do código | models, evaluation |
| 2026-08-12 | Issue #75 | Avaliação tornada determinística: `n_jobs=1` fixo (era `-1`, causava resultados diferentes por número de núcleos da máquina), hiperparâmetros centralizados em `HIPERPARAMETROS_XGBOOST` (fonte única), contagem de "medicamento vencedor" calculada automaticamente (nunca mais escrita à mão), relatório passa a registrar hash do dataset e versões do ambiente, `requirements.txt` fixado com versões exatas (removido `prophet`, nunca usado) | models, evaluation |
| 2026-08-13 | Issue #77 | Formalizado o protocolo operacional versionado: janelas comuns sem overlap, métricas preditivas e operacionais obrigatórias, limites objetivos de aprovação e artefatos auditáveis CSV/JSON/Markdown | evaluation |
| 2026-08-13 | Coerência temporal da simulação | `lotes.csv` é uma fotografia do fim do dataset; para cada corte, a simulação gera um snapshot sintético, determinístico e temporalmente compatível com o `estoque_disponivel` daquela data. Lotes futuros não vazam para a avaliação contrafactual; como não há histórico completo por lote, o snapshot não representa os lotes físicos reais do corte. | evaluation |
| 2026-08-13 | Issue #86 | Objetivo de treino do modelo oficial trocado de erro quadrático médio para regressão quantílica (`quantile_alpha=0.8`), aprovado formalmente pela Issue #84 (protocolo v1.1.0-janela-longa): -33% de custo de compra emergencial, -46% de episódios de ruptura frente ao modelo simétrico anterior, consistente em 4 de 4 janelas. Contrato de saída (`COLUNAS_SAIDA`, horizonte de 7 dias) não muda; `treinar_modelo`/`avaliar_validacao_temporal` aceitam `quantile_alpha=None` para reproduzir o objetivo simétrico anterior, só para comparação histórica | models, evaluation, dashboard, recommendation |
