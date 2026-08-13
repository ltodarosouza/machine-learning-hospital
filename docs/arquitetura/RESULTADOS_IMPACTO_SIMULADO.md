# Impacto simulado: baseline vs. modelo de ML (Issue #17)

Período simulado: outubro a dezembro de 2025, com validação temporal por janelas de 7 dias.

> **Limitação:** simulação sobre dados sintéticos, não piloto hospitalar. Compras emergenciais usam o preço unitário de referência. O consumo segue FEFO; cada corte recebe um snapshot sintético de lotes temporalmente compatível com seu estoque agregado e reposições simuladas recebem validade de 365 dias. Como não há histórico completo de movimentação por lote, esse snapshot não reproduz os lotes físicos que existiriam no hospital.

## Resultado por mês

| Mês | Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---|---:|---:|---:|---:|
| 10 | episodios_ruptura | 73.00 | 93.00 | -20.00 | -27.4% |
| 10 | unidades_em_ruptura | 2559.52 | 3513.91 | -954.39 | -37.3% |
| 10 | compras_emergenciais_unidades | 2559.52 | 3513.91 | -954.39 | -37.3% |
| 10 | custo_compras_emergenciais_reais | 7672.78 | 11179.09 | -3506.31 | -45.7% |
| 10 | unidades_vencidas | 173.77 | 173.77 | 0.00 | 0.0% |
| 11 | episodios_ruptura | 125.00 | 158.00 | -33.00 | -26.4% |
| 11 | unidades_em_ruptura | 9253.93 | 9223.27 | 30.66 | 0.3% |
| 11 | compras_emergenciais_unidades | 9253.93 | 9223.27 | 30.66 | 0.3% |
| 11 | custo_compras_emergenciais_reais | 21463.98 | 21402.28 | 61.69 | 0.3% |
| 11 | unidades_vencidas | 421.81 | 421.81 | 0.00 | 0.0% |
| 12 | episodios_ruptura | 116.00 | 114.00 | 2.00 | 1.7% |
| 12 | unidades_em_ruptura | 3740.61 | 3328.26 | 412.35 | 11.0% |
| 12 | compras_emergenciais_unidades | 3740.61 | 3328.26 | 412.35 | 11.0% |
| 12 | custo_compras_emergenciais_reais | 18967.48 | 15111.57 | 3855.92 | 20.3% |
| 12 | unidades_vencidas | 69.14 | 69.14 | 0.00 | 0.0% |

## Consolidado (3 meses)

| Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---:|---:|---:|---:|
| compras_emergenciais_unidades | 15554.05 | 16065.44 | -511.39 | -3.3% |
| custo_compras_emergenciais_reais | 48104.24 | 47692.93 | 411.31 | 0.9% |
| episodios_ruptura | 314.00 | 365.00 | -51.00 | -16.2% |
| unidades_em_ruptura | 15554.05 | 16065.44 | -511.39 | -3.3% |
| unidades_vencidas | 664.72 | 664.72 | 0.00 | 0.0% |

## Leitura

No recorte de três meses, o modelo não demonstra ganho operacional consistente frente ao baseline. A comparação deve orientar novos ajustes e validação antes de qualquer uso real.
