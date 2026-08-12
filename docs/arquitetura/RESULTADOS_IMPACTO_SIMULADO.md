# Impacto simulado: baseline vs. modelo de ML (Issue #17)

Período simulado: 2025-12-04 a 2025-12-31.

> **Limitação:** esta é uma simulação sobre dados sintéticos, não um piloto hospitalar real. Compras emergenciais são valoradas pelo preço unitário de referência; vencimentos exigem movimentação de lotes e por isso ainda não são estimados neste cenário.

| Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---:|---:|---:|---:|
| episodios_ruptura | 97.00 | 98.00 | -1.00 | -1.0% |
| unidades_em_ruptura | 2031.09 | 2128.58 | -97.49 | -4.8% |
| compras_emergenciais_unidades | 2031.09 | 2128.58 | -97.49 | -4.8% |
| custo_compras_emergenciais_reais | 8236.29 | 8213.99 | 22.30 | 0.3% |
| unidades_vencidas | 0.00 | 0.00 | 0.00 | — |
