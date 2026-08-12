# `src/features/`

Engenharia de features. Cada arquivo aqui recebe o dataset processado (schema de [`docs/arquitetura/CONTRATOS.md`](../../docs/arquitetura/CONTRATOS.md) seção 1) e devolve o mesmo dataframe com colunas `feat_*` adicionadas. Nenhum arquivo aqui trata dados faltantes/outliers — isso é escopo da Issue #10 (`pipeline.py`, pendente), que junta as saídas de todos.

## `calendario_externas.py` (Issue #9) — pronto

Features de calendário (dia da semana, fim de semana, mês, feriado) e das variáveis externas (lag de dengue, normalização de temperatura/chuva/dengue). Lista completa e detalhada em `CONTRATOS.md` seção 2.

```bash
python src/features/calendario_externas.py
```

## `series_temporais.py` (Issue #8) — pendente

Médias móveis e lags do consumo. Atribuída, aguardando implementação.
