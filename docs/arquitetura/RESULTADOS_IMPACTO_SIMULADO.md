# Impacto simulado: baseline vs. modelo de ML (Issue #17)

Período simulado: 2025-12-04 a 2025-12-31.

> **Limitação:** esta é uma simulação sobre dados sintéticos, não um piloto hospitalar real. Compras emergenciais são valoradas pelo preço unitário de referência; vencimentos exigem movimentação de lotes e por isso ainda não são estimados neste cenário.

| Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---:|---:|---:|---:|
| episodios_ruptura | 74.00 | 72.00 | 2.00 | 2.7% |
| unidades_em_ruptura | 1878.37 | 1907.66 | -29.29 | -1.6% |
| compras_emergenciais_unidades | 1878.37 | 1907.66 | -29.29 | -1.6% |
| custo_compras_emergenciais_reais | 9009.46 | 9693.02 | -683.56 | -7.6% |
| unidades_vencidas | 0.00 | 0.00 | 0.00 | — |
