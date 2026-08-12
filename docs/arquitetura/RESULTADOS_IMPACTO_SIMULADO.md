# Impacto simulado: baseline vs. modelo de ML (Issue #17)

Período simulado: outubro a dezembro de 2025, com validação temporal por janelas de 7 dias.

> **Limitação:** simulação sobre dados sintéticos, não piloto hospitalar. Compras emergenciais usam o preço unitário de referência. Vencimentos ainda não são estimados porque a simulação não movimenta lotes individualmente.

## Resultado por mês

| Mês | Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---|---:|---:|---:|---:|
| 10 | episodios_ruptura | 68.00 | 84.00 | -16.00 | -23.5% |
| 10 | unidades_em_ruptura | 2385.74 | 3021.35 | -635.60 | -26.6% |
| 10 | compras_emergenciais_unidades | 2385.74 | 3021.35 | -635.60 | -26.6% |
| 10 | custo_compras_emergenciais_reais | 5698.11 | 8761.04 | -3062.92 | -53.8% |
| 10 | unidades_vencidas | 0.00 | 0.00 | 0.00 | — |
| 11 | episodios_ruptura | 117.00 | 124.00 | -7.00 | -6.0% |
| 11 | unidades_em_ruptura | 8935.10 | 8403.17 | 531.93 | 6.0% |
| 11 | compras_emergenciais_unidades | 8935.10 | 8403.17 | 531.93 | 6.0% |
| 11 | custo_compras_emergenciais_reais | 17728.20 | 14312.24 | 3415.97 | 19.3% |
| 11 | unidades_vencidas | 0.00 | 0.00 | 0.00 | — |
| 12 | episodios_ruptura | 116.00 | 118.00 | -2.00 | -1.7% |
| 12 | unidades_em_ruptura | 3671.47 | 3755.95 | -84.48 | -2.3% |
| 12 | compras_emergenciais_unidades | 3671.47 | 3755.95 | -84.48 | -2.3% |
| 12 | custo_compras_emergenciais_reais | 18137.86 | 15845.40 | 2292.45 | 12.6% |
| 12 | unidades_vencidas | 0.00 | 0.00 | 0.00 | — |

## Consolidado (3 meses)

| Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---:|---:|---:|---:|
| compras_emergenciais_unidades | 14992.31 | 15180.46 | -188.15 | -1.3% |
| custo_compras_emergenciais_reais | 41564.17 | 38918.67 | 2645.50 | 6.4% |
| episodios_ruptura | 301.00 | 326.00 | -25.00 | -8.3% |
| unidades_em_ruptura | 14992.31 | 15180.46 | -188.15 | -1.3% |
| unidades_vencidas | 0.00 | 0.00 | 0.00 | — |

## Leitura

No recorte de três meses, o modelo não demonstra ganho operacional consistente frente ao baseline. A comparação deve orientar novos ajustes e validação antes de qualquer uso real.
