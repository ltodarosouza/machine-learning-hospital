# Impacto simulado: baseline vs. modelo de ML (Issue #17)

Período simulado: outubro a dezembro de 2025, com validação temporal por janelas de 7 dias.

> **Limitação:** simulação sobre dados sintéticos, não piloto hospitalar. Compras emergenciais usam o preço unitário de referência. Vencimentos ainda não são estimados porque a simulação não movimenta lotes individualmente.

## Resultado por mês

| Mês | Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---|---:|---:|---:|---:|
| 10 | episodios_ruptura | 84.00 | 82.00 | 2.00 | 2.4% |
| 10 | unidades_em_ruptura | 1860.40 | 2087.86 | -227.46 | -12.2% |
| 10 | compras_emergenciais_unidades | 1860.40 | 2087.86 | -227.46 | -12.2% |
| 10 | custo_compras_emergenciais_reais | 3868.67 | 3882.22 | -13.55 | -0.4% |
| 10 | unidades_vencidas | 0.00 | 0.00 | 0.00 | — |
| 11 | episodios_ruptura | 81.00 | 92.00 | -11.00 | -13.6% |
| 11 | unidades_em_ruptura | 1458.60 | 2005.36 | -546.76 | -37.5% |
| 11 | compras_emergenciais_unidades | 1458.60 | 2005.36 | -546.76 | -37.5% |
| 11 | custo_compras_emergenciais_reais | 3088.26 | 3362.05 | -273.78 | -8.9% |
| 11 | unidades_vencidas | 0.00 | 0.00 | 0.00 | — |
| 12 | episodios_ruptura | 101.00 | 102.00 | -1.00 | -1.0% |
| 12 | unidades_em_ruptura | 1898.39 | 2329.21 | -430.83 | -22.7% |
| 12 | compras_emergenciais_unidades | 1898.39 | 2329.21 | -430.83 | -22.7% |
| 12 | custo_compras_emergenciais_reais | 5738.56 | 6316.85 | -578.29 | -10.1% |
| 12 | unidades_vencidas | 0.00 | 0.00 | 0.00 | — |

## Consolidado (3 meses)

| Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---:|---:|---:|---:|
| compras_emergenciais_unidades | 5217.39 | 6422.44 | -1205.05 | -23.1% |
| custo_compras_emergenciais_reais | 12695.50 | 13561.12 | -865.63 | -6.8% |
| episodios_ruptura | 266.00 | 276.00 | -10.00 | -3.8% |
| unidades_em_ruptura | 5217.39 | 6422.44 | -1205.05 | -23.1% |
| unidades_vencidas | 0.00 | 0.00 | 0.00 | — |

## Leitura

No recorte de três meses, o modelo não demonstra ganho operacional consistente frente ao baseline. A comparação deve orientar novos ajustes e validação antes de qualquer uso real.
