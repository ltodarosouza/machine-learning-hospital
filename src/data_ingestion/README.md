# `src/data_ingestion/`

Scripts que geram/baixam os dados usados pelo projeto. Cada script é independente e pode ser rodado sozinho — todos leem o período do projeto (`PERIODO_INICIO`, `PERIODO_FIM`) de [`src/utils/config.py`](../utils/config.py), então nunca hardcode datas dentro de um script novo.

## Scripts

### `ingestao_calendario.py` (Issue #6) — pronto

Gera o calendário de feriados nacionais e estaduais (PB) do período do projeto, usando a biblioteca `holidays` (sem chamada de rede).

```bash
python src/data_ingestion/ingestao_calendario.py
```

Saída: `data/external/calendario.csv` — 1 linha por dia, colunas `data`, `feriado` (bool), `nome_feriado` (string, vazio se não for feriado). Este arquivo é pequeno, público e 100% reprodutível, por isso é commitado no repositório (exceção registrada no `.gitignore`) — quem for trabalhar em features/dashboard pode usá-lo direto, sem rodar o script.

Feriados cobertos: nacionais (ex. Confraternização Universal, Tiradentes, Natal) + estaduais da Paraíba, via `holidays.Brazil(subdiv="PB")`. Não cobre feriados municipais específicos de João Pessoa (a lib não tem esse nível de granularidade) — se o time achar necessário, pode ser adicionado manualmente depois como uma lista fixa.

### `gerar_dataset_sintetico.py` (Issue #3) — pronto

Gera o dataset sintético de consumo dos 20 medicamentos do MVP, calibrado para reagir às variáveis externas reais (clima, dengue, feriados — Issues #4/#5/#6) e para incluir uma política de reposição "ingênua" (a forma como um hospital decide hoje, sem modelo preditivo), que produz de propósito alguns episódios de ruptura e alguns lotes com risco de vencimento — sem isso não haveria nada para o motor de recomendação melhorar depois.

```bash
python src/data_ingestion/gerar_dataset_sintetico.py
```

Saída (todas em `data/processed/`, commitadas — ver `.gitignore`, dado sintético/reprodutível, não é dado real de hospital nenhum):

- `consumo_diario.csv` — contrato 1.1 (29.220 linhas: 20 medicamentos × 1.461 dias, período estendido para 4 anos depois da Issue #13)
- `medicamentos_ref.csv` — contrato 1.3 (cadastro: nome, categoria, prazo de entrega, preço)
- `lotes.csv` — contrato 1.4 (lotes em estoque, com validade)
- `pedidos_pendentes.csv` — contrato 1.5 (pedidos em trânsito no fim do período)

**Demanda e ruptura (Issue #60):** `consumo_unidades` representa a demanda
latente, inclusive quando o estoque não era suficiente para atendê-la. A
simulação registra separadamente `dispensacao_unidades` (o que saiu de fato) e
`demanda_nao_atendida` (a diferença por ruptura). O modelo continua prevendo a
demanda latente; as duas novas colunas são operacionais e não entram como
features preditivas.

**Importante — números de base são premissas do time, não dados reais:** consumo médio diário por medicamento, preços e prazos de entrega em `MEDICAMENTOS_REF` (dentro do script) são estimativas de ordem de grandeza para o MVP fazer sentido, não vieram de nenhum hospital real. Isso é consistente com o framing já adotado no projeto (ver `docs/negocio/CONTEXTO.md`, seção de cuidado com números de impacto) — se questionado na banca, a resposta é "dataset sintético calibrado com padrões plausíveis, não dado real".

**Estados latentes persistentes de surto (Issue #58):** até aqui, a única variação de curto prazo era ruído independente a cada dia — o que faz o previsor "ótimo" ser praticamente a própria média-base, limitando estruturalmente o quanto um modelo de ML consegue melhorar sobre uma média móvel simples (ver discussão que originou a Issue #58, e o resultado modesto documentado em `src/models/README.md`). Agora existem 2 processos de "intensidade de surto" (uma cadeia de Markov de 3 estados: normal/elevado/surto — `gerar_estado_surto`), um compartilhado por todos os medicamentos sensíveis a clima (respiratórios) e outro por todos sensíveis a dengue — porque um surto de verdade afeta vários medicamentos ao mesmo tempo, não um só. Episódios fora do "normal" duram, em média, ~14 dias (mediana 10), dentro da faixa de 1-4 semanas — não é mais um sorteio novo por dia. Isso não elimina o ruído diário, só deixa de ser a única fonte de variação de curto prazo.

**Ordem causal dos sinais internos (Issue #59):** o gerador primeiro calcula os fatores externos e os estados de surto, depois gera `atendimentos_ps` a partir deles e deriva `ocupacao_leitos_pct` dos atendimentos. Só então `gerar_consumo_diario` gera o consumo por medicamento usando o volume de atendimentos como sinal de demanda, combinado com a propensão específica de clima/dengue da categoria. `atendimentos_ps` não é mais calculado a partir do consumo agregado do próprio dia.

**Fora do escopo desta issue** (fica para depois, se o time decidir): re-rodar a comparação de algoritmos/tuning do modelo (`scripts/comparar_algoritmos_modelo.py`, `scripts/tuning_xgboost.py`) com o dataset regenerado, para medir se isso de fato aumenta a margem do ML sobre o baseline.

**Casos propositalmente extremos para a demonstração:** `ceftriaxona_inj` e `hidrocortisona_inj` concentram a maior parte do seu estoque **real** (não inventado) num único lote de validade curta (`gerar_lotes`, calculada a partir do próprio consumo-base do medicamento, não um número fixo) — o suficiente para o motor de recomendação classificar risco de vencimento alto de verdade, sem quebrar a invariante `soma(lotes) == estoque_disponivel` (contrato seção 1.4, Issue #53). `adrenalina_inj` tem estoque cronicamente baixo frente ao consumo (risco de falta, é o item com mais dias de ruptura no período) — esse já surge naturalmente da simulação, sem precisar forçar nada.

### `ingestao_clima.py` (Issue #4) — pronto

Busca temperatura média e chuva diárias na API pública da Open-Meteo (dados de reanálise ERA5), para as coordenadas de João Pessoa.

```bash
python src/data_ingestion/ingestao_clima.py
```

Saída: `data/external/clima.csv` — colunas `data`, `temperatura_media` (°C), `chuva_mm`. Commitado no repositório pelo mesmo motivo do calendário (dado público, pequeno, reprodutível).

**Nota importante:** o plano original (`FONTES_DADOS.md`) era usar o INMET. Na prática, o portal do INMET não respondeu a chamadas automatizadas no ambiente em que essa task foi feita, então a fonte foi trocada para Open-Meteo — mesmo tipo de dado (temperatura/chuva reais), mais fácil de automatizar. Detalhes e como trocar de volta para INMET se o time preferir: ver `docs/arquitetura/FONTES_DADOS.md` seção 1.

### `ingestao_epidemiologia.py` (Issue #5) — pronto

Busca casos semanais de dengue na API pública do InfoDengue (geocódigo IBGE de João Pessoa, confirmado nesta task) e converte para diário (média da semana / 7, repetida nos 7 dias — decisão documentada no código).

```bash
python src/data_ingestion/ingestao_epidemiologia.py
```

Saída: `data/external/epidemiologia.csv` — colunas `data`, `casos_dengue_regiao`. Commitado no repositório pelo mesmo motivo dos outros dados externos.

### `consolidar_dataset.py` (Issue #7) — pronto

Une as saídas de todas as Issues acima. Roda por último, depois de #3, #4, #5 e #6 terem gerado seus arquivos.

```bash
python src/data_ingestion/consolidar_dataset.py
```

Gera:

- `data/external/externos_diarios.csv` — contrato 1.2 (clima + epidemiologia + calendário, unidos por `data`)
- `data/processed/consumo_medicamentos.csv` — **o "dataset de modelagem"**: consumo (1.1) + externos (1.2) unidos por `data`. **É este arquivo que as Issues #8 a #13 (features e modelagem) devem consumir**, não os arquivos individuais.
- `data/processed/sample_consumo_medicamentos.csv` — amostra pequena (90 linhas, 3 medicamentos × 30 dias) para quem for começar features/modelo/dashboard sem rodar o pipeline inteiro.

Todos commitados (mesma lógica dos outros arquivos de dados: sintético/público, pequeno, reprodutível).
