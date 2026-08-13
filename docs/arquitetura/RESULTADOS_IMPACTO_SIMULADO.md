# Impacto simulado: baseline vs. modelo de ML (Issue #17)

Período simulado: outubro a dezembro de 2025, com validação temporal por janelas de 7 dias.

> **Limitação:** simulação sobre dados sintéticos, não piloto hospitalar. Compras emergenciais usam o preço unitário de referência. Vencimentos ainda não são estimados porque a simulação não movimenta lotes individualmente.

## Resultado por mês

| Mês | Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---|---:|---:|---:|---:|
| 10 | episodios_ruptura | 68.00 | 90.00 | -22.00 | -32.4% |
| 10 | unidades_em_ruptura | 2385.74 | 3480.44 | -1094.70 | -45.9% |
| 10 | compras_emergenciais_unidades | 2385.74 | 3480.44 | -1094.70 | -45.9% |
| 10 | custo_compras_emergenciais_reais | 5698.11 | 9601.87 | -3903.75 | -68.5% |
| 10 | unidades_vencidas | 0.00 | 0.00 | 0.00 | — |
| 11 | episodios_ruptura | 118.00 | 149.00 | -31.00 | -26.3% |
| 11 | unidades_em_ruptura | 8935.10 | 9075.75 | -140.65 | -1.6% |
| 11 | compras_emergenciais_unidades | 8935.10 | 9075.75 | -140.65 | -1.6% |
| 11 | custo_compras_emergenciais_reais | 17728.20 | 17911.76 | -183.56 | -1.0% |
| 11 | unidades_vencidas | 0.00 | 0.00 | 0.00 | — |
| 12 | episodios_ruptura | 116.00 | 126.00 | -10.00 | -8.6% |
| 12 | unidades_em_ruptura | 3671.47 | 3856.18 | -184.71 | -5.0% |
| 12 | compras_emergenciais_unidades | 3671.47 | 3856.18 | -184.71 | -5.0% |
| 12 | custo_compras_emergenciais_reais | 18137.86 | 18671.74 | -533.89 | -2.9% |
| 12 | unidades_vencidas | 0.00 | 0.00 | 0.00 | — |

## Consolidado (3 meses)

| Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---:|---:|---:|---:|
| compras_emergenciais_unidades | 14992.31 | 16412.38 | -1420.07 | -9.5% |
| custo_compras_emergenciais_reais | 41564.17 | 46185.37 | -4621.20 | -11.1% |
| episodios_ruptura | 302.00 | 365.00 | -63.00 | -20.9% |
| unidades_em_ruptura | 14992.31 | 16412.38 | -1420.07 | -9.5% |
| unidades_vencidas | 0.00 | 0.00 | 0.00 | — |

## Leitura

No recorte de três meses, o modelo não demonstra ganho operacional consistente frente ao baseline. A comparação deve orientar novos ajustes e validação antes de qualquer uso real.
