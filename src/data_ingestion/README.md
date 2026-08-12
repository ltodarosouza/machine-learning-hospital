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

### `gerar_dataset_sintetico.py` (Issue #3) — pendente

### `ingestao_clima.py` (Issue #4) — pendente

### `ingestao_epidemiologia.py` (Issue #5) — pendente

### Consolidação (Issue #7) — pendente

Une as saídas acima em `data/processed/consumo_medicamentos.csv`, seguindo o contrato em [`docs/arquitetura/CONTRATOS.md`](../../docs/arquitetura/CONTRATOS.md).
