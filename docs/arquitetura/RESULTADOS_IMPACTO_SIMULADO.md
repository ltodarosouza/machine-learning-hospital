# Impacto simulado: baseline vs. modelo de ML (Issue #17)

Período simulado: 2025-12-04 a 2025-12-31.

> **Limitação:** esta é uma simulação sobre dados sintéticos, não um piloto hospitalar real. Compras emergenciais são valoradas pelo preço unitário de referência. O consumo segue FEFO (primeiro a vencer, primeiro a sair); reposições simuladas recebem validade de 365 dias.

| Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---:|---:|---:|---:|
| episodios_ruptura | 86.00 | 93.00 | -7.00 | -8.1% |
| unidades_em_ruptura | 2697.67 | 2747.92 | -50.24 | -1.9% |
| compras_emergenciais_unidades | 2697.67 | 2747.92 | -50.24 | -1.9% |
| custo_compras_emergenciais_reais | 6944.36 | 6924.01 | 20.36 | 0.3% |
| unidades_vencidas | 0.00 | 0.00 | 0.00 | — |
