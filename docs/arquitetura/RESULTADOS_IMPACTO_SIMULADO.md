# Impacto simulado: baseline vs. modelo de ML (Issue #17)

Período simulado: outubro a dezembro de 2025, com validação temporal por janelas de 7 dias.

> **Limitação:** simulação sobre dados sintéticos, não piloto hospitalar. Compras emergenciais usam o preço unitário de referência. O consumo segue FEFO; cada corte recebe um snapshot sintético de lotes temporalmente compatível com seu estoque agregado e reposições simuladas recebem validade de 365 dias. Como não há histórico completo de movimentação por lote, esse snapshot não reproduz os lotes físicos que existiriam no hospital.

## Resultado por mês

| Mês | Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---|---:|---:|---:|---:|
| 10 | episodios_ruptura | 73.00 | 41.00 | 32.00 | 43.8% |
| 10 | unidades_em_ruptura | 2559.52 | 1820.88 | 738.64 | 28.9% |
| 10 | compras_emergenciais_unidades | 2559.52 | 1820.88 | 738.64 | 28.9% |
| 10 | custo_compras_emergenciais_reais | 7672.78 | 6817.93 | 854.85 | 11.1% |
| 10 | unidades_vencidas | 173.77 | 173.77 | 0.00 | 0.0% |
| 10 | quantidade_total_recomendada | 46339.31 | 49757.75 | -3418.44 | -7.4% |
| 11 | episodios_ruptura | 125.00 | 77.00 | 48.00 | 38.4% |
| 11 | unidades_em_ruptura | 9253.93 | 7060.19 | 2193.74 | 23.7% |
| 11 | compras_emergenciais_unidades | 9253.93 | 7060.19 | 2193.74 | 23.7% |
| 11 | custo_compras_emergenciais_reais | 21463.98 | 14784.40 | 6679.58 | 31.1% |
| 11 | unidades_vencidas | 421.81 | 421.81 | 0.00 | 0.0% |
| 11 | quantidade_total_recomendada | 43796.24 | 44855.14 | -1058.90 | -2.4% |
| 12 | episodios_ruptura | 116.00 | 70.00 | 46.00 | 39.7% |
| 12 | unidades_em_ruptura | 3740.61 | 1916.60 | 1824.01 | 48.8% |
| 12 | compras_emergenciais_unidades | 3740.61 | 1916.60 | 1824.01 | 48.8% |
| 12 | custo_compras_emergenciais_reais | 18967.48 | 11334.05 | 7633.43 | 40.2% |
| 12 | unidades_vencidas | 69.14 | 69.14 | 0.00 | 0.0% |
| 12 | quantidade_total_recomendada | 31072.27 | 32879.92 | -1807.64 | -5.8% |

## Consolidado (3 meses)

| Métrica | Baseline | Modelo ML | Redução | Redução (%) |
|---|---:|---:|---:|---:|
| compras_emergenciais_unidades | 15554.05 | 10797.67 | 4756.38 | 30.6% |
| custo_compras_emergenciais_reais | 48104.24 | 32936.38 | 15167.86 | 31.5% |
| episodios_ruptura | 314.00 | 188.00 | 126.00 | 40.1% |
| quantidade_total_recomendada | 121207.83 | 127492.81 | -6284.98 | -5.2% |
| unidades_em_ruptura | 15554.05 | 10797.67 | 4756.38 | 30.6% |
| unidades_vencidas | 664.72 | 664.72 | 0.00 | 0.0% |

## Leitura

No recorte de três meses, o modelo reduz o custo de compra emergencial em 31.5% frente ao baseline, de forma consistente (redução positiva em todos os meses avaliados). Ainda é simulação sobre dados sintéticos, não evidência de piloto real.
