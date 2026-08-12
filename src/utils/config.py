"""Constantes de escopo do MVP, fechadas na Issue #1 (kickoff).

Todo script de ingestão/geração de dados deve importar o período daqui,
em vez de hardcodar datas, para garantir que todas as tabelas (consumo,
externos, calendário) cubram exatamente o mesmo intervalo.
"""

PERIODO_INICIO = "2024-01-01"
PERIODO_FIM = "2025-12-31"

REGIAO_NOME = "João Pessoa"
REGIAO_UF = "PB"
REGIAO_GEOCODIGO_IBGE = 2507507  # a confirmar na Issue #5 (InfoDengue)

HORIZONTE_PREVISAO_DIAS = 7
