# Impacto simulado: baseline vs. modelo de ML (Issue #17)

Período simulado: outubro a dezembro de 2025, com validação temporal por janelas de 7 dias.

> **Limitação:** simulação sobre dados sintéticos, não piloto hospitalar. Compras emergenciais usam o preço unitário de referência. O consumo segue FEFO; cada corte recebe um snapshot sintético de lotes temporalmente compatível com seu estoque agregado e reposições simuladas recebem validade de 365 dias. Como não há histórico completo de movimentação por lote, esse snapshot não reproduz os lotes físicos que existiriam no hospital.

## Resultado por mês

| Mês | Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---|---:|---:|---:|---:|
| 10 | episodios_ruptura | 73.00 | 83.00 | -10.00 | -13.7% |
| 10 | unidades_em_ruptura | 2559.52 | 3398.78 | -839.26 | -32.8% |
| 10 | compras_emergenciais_unidades | 2559.52 | 3398.78 | -839.26 | -32.8% |
| 10 | custo_compras_emergenciais_reais | 7672.78 | 11141.00 | -3468.22 | -45.2% |
| 10 | unidades_vencidas | 173.77 | 173.77 | 0.00 | 0.0% |
| 11 | episodios_ruptura | 125.00 | 151.00 | -26.00 | -20.8% |
| 11 | unidades_em_ruptura | 9253.93 | 9312.50 | -58.57 | -0.6% |
| 11 | compras_emergenciais_unidades | 9253.93 | 9312.50 | -58.57 | -0.6% |
| 11 | custo_compras_emergenciais_reais | 21463.98 | 20486.21 | 977.77 | 4.6% |
| 11 | unidades_vencidas | 421.81 | 421.81 | 0.00 | 0.0% |
| 12 | episodios_ruptura | 116.00 | 123.00 | -7.00 | -6.0% |
| 12 | unidades_em_ruptura | 3740.61 | 3965.32 | -224.71 | -6.0% |
| 12 | compras_emergenciais_unidades | 3740.61 | 3965.32 | -224.71 | -6.0% |
| 12 | custo_compras_emergenciais_reais | 18967.48 | 17817.43 | 1150.05 | 6.1% |
| 12 | unidades_vencidas | 69.14 | 69.14 | 0.00 | 0.0% |

## Consolidado (3 meses)

| Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---:|---:|---:|---:|
| compras_emergenciais_unidades | 15554.05 | 16676.59 | -1122.54 | -7.2% |
| custo_compras_emergenciais_reais | 48104.24 | 49444.65 | -1340.41 | -2.8% |
| episodios_ruptura | 314.00 | 357.00 | -43.00 | -13.7% |
| unidades_em_ruptura | 15554.05 | 16676.59 | -1122.54 | -7.2% |
| unidades_vencidas | 664.72 | 664.72 | 0.00 | 0.0% |

## Leitura

No recorte de três meses, o modelo não demonstra ganho operacional consistente frente ao baseline. A comparação deve orientar novos ajustes e validação antes de qualquer uso real.
