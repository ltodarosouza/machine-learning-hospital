# Relatório operacional por medicamento, mês e tipo de erro (Issue #76)

Decompõe os totais agregados do relatório de precisão (`RESULTADOS_MODELAGEM.md`) e do relatório de impacto simulado (`RESULTADOS_IMPACTO_SIMULADO.md`) até medicamento e mês, sobre o mesmo corte temporal — para identificar quais itens e períodos explicam a diferença de custo e de ruptura entre baseline e modelo de ML, sem esconder os casos em que o ML perde.

**Comando para regenerar:** `python src/evaluation/relatorio_operacional.py` (ou `python scripts/relatorio_final.py`, que também regenera este relatório).

## Detalhamento por medicamento e mês

| Mês | Medicamento | MAE base/ML | Viés base/ML | Subest. (un) base/ML | Superest. (un) base/ML | Episódios ruptura base/ML | Custo emergencial (R$) base/ML | Vencidas (un) base/ML |
|---|---|---|---|---|---|---|---|---|
| 10 | adrenalina_inj | 2.21 / 2.44 | +0.53 / +1.19 | 29.4 / 21.9 | 47.9 / 63.6 | 0 / 0 | 0.00 / 0.00 | 0.0 / 0.0 |
| 10 | amoxicilina | 11.85 / 12.20 | +1.11 / +3.22 | 187.9 / 157.2 | 226.9 / 269.9 | 6 / 5 | 94.24 / 88.34 | 0.0 / 0.0 |
| 10 | azitromicina | 7.64 / 7.75 | -0.31 / -0.68 | 139.2 / 147.5 | 128.2 / 123.6 | 3 / 4 | 55.30 / 124.49 | 0.0 / 0.0 |
| 10 | ceftriaxona_inj | 6.84 / 8.13 | +1.14 / +1.02 | 99.6 / 124.4 | 139.6 / 160.2 | 5 / 8 | 1931.27 / 2320.92 | 155.3 / 155.3 |
| 10 | diazepam | 3.48 / 3.85 | +0.86 / +2.30 | 45.9 / 27.0 | 75.9 / 107.7 | 0 / 0 | 0.00 / 0.00 | 0.0 / 0.0 |
| 10 | diclofenaco | 12.85 / 15.37 | +2.49 / +2.70 | 181.4 / 221.7 | 268.4 / 316.4 | 4 / 8 | 40.29 / 82.75 | 0.0 / 0.0 |
| 10 | dipirona | 106.48 / 70.33 | +44.33 / +2.12 | 1087.7 / 1193.8 | 2639.2 / 1267.8 | 2 / 8 | 50.69 / 123.25 | 0.0 / 0.0 |
| 10 | hidrocortisona_inj | 6.20 / 7.59 | +1.77 / +5.07 | 77.4 / 44.0 | 139.4 / 221.5 | 8 / 8 | 647.60 / 596.30 | 18.4 / 18.4 |
| 10 | ibuprofeno | 20.53 / 21.26 | +2.14 / +10.66 | 321.8 / 185.4 | 396.8 / 558.6 | 12 / 7 | 93.86 / 64.41 | 0.0 / 0.0 |
| 10 | loratadina | 10.64 / 8.79 | +3.57 / +4.46 | 123.7 / 75.9 | 248.7 / 231.8 | 6 / 7 | 54.52 / 53.32 | 0.0 / 0.0 |
| 10 | metoclopramida | 22.21 / 15.66 | +6.97 / +0.90 | 266.6 / 258.3 | 510.6 / 289.8 | 0 / 2 | 0.00 / 16.63 | 0.0 / 0.0 |
| 10 | omeprazol_inj | 7.13 / 8.47 | +2.43 / +1.73 | 82.3 / 118.0 | 167.3 / 178.4 | 3 / 5 | 102.00 / 213.42 | 0.0 / 0.0 |
| 10 | ondansetrona | 18.17 / 14.73 | +9.59 / +6.42 | 150.1 / 145.4 | 485.6 / 370.1 | 4 / 4 | 894.86 / 894.86 | 0.0 / 0.0 |
| 10 | paracetamol | 81.28 / 58.12 | +36.87 / +13.39 | 777.1 / 782.8 | 2067.6 / 1251.3 | 3 / 4 | 67.75 / 57.64 | 0.0 / 0.0 |
| 10 | predinisolona | 11.40 / 11.30 | +3.44 / +5.32 | 139.3 / 104.5 | 259.8 / 290.9 | 4 / 3 | 44.82 / 48.64 | 0.0 / 0.0 |
| 10 | salbutamol | 18.48 / 16.78 | +3.37 / +4.08 | 264.4 / 222.2 | 382.4 / 365.2 | 3 / 3 | 237.60 / 740.07 | 0.0 / 0.0 |
| 10 | soro_antitermico_infantil | 33.53 / 24.10 | +12.93 / +12.29 | 360.5 / 206.6 | 813.0 / 636.8 | 5 / 7 | 1668.34 / 1878.15 | 0.0 / 0.0 |
| 10 | soro_fisiologico | 65.99 / 53.11 | +32.91 / +5.29 | 578.9 / 836.8 | 1730.9 / 1021.9 | 2 / 4 | 1577.57 / 3505.16 | 0.0 / 0.0 |
| 10 | soro_ringer | 31.32 / 22.54 | +13.89 / +6.35 | 305.1 / 283.3 | 791.1 / 505.6 | 1 / 2 | 100.86 / 327.91 | 0.0 / 0.0 |
| 10 | tramadol | 5.14 / 5.96 | +1.39 / +3.03 | 65.7 / 51.2 | 114.2 / 157.3 | 2 / 4 | 11.23 / 42.85 | 0.0 / 0.0 |
| 11 | adrenalina_inj | 2.24 / 2.55 | +0.03 / +1.02 | 38.7 / 26.8 | 39.7 / 62.4 | 2 / 5 | 140.86 / 293.82 | 0.0 / 0.0 |
| 11 | amoxicilina | 10.14 / 11.86 | +0.70 / +0.53 | 165.1 / 198.4 | 189.6 / 216.8 | 12 / 14 | 332.15 / 372.35 | 0.0 / 0.0 |
| 11 | azitromicina | 7.06 / 7.86 | -0.84 / -1.66 | 138.4 / 166.6 | 108.9 / 108.5 | 4 / 9 | 57.40 / 275.15 | 0.0 / 0.0 |
| 11 | ceftriaxona_inj | 9.61 / 9.74 | +0.40 / +0.45 | 161.1 / 162.5 | 175.1 / 178.3 | 7 / 8 | 3948.00 / 4051.15 | 366.0 / 366.0 |
| 11 | diazepam | 4.03 / 5.14 | -0.67 / +0.83 | 82.4 / 75.4 | 58.9 / 104.6 | 1 / 2 | 9.09 / 17.67 | 0.0 / 0.0 |
| 11 | diclofenaco | 14.61 / 17.43 | -3.87 / -3.76 | 323.4 / 370.8 | 187.9 / 239.3 | 7 / 11 | 93.26 / 113.96 | 0.0 / 0.0 |
| 11 | dipirona | 116.15 / 74.78 | +2.41 / -18.95 | 1990.4 / 1640.3 | 2074.9 / 976.9 | 4 / 8 | 377.43 / 392.31 | 0.0 / 0.0 |
| 11 | hidrocortisona_inj | 7.01 / 7.04 | -1.90 / -0.31 | 155.9 / 128.7 | 89.4 / 117.8 | 11 / 10 | 733.37 / 855.56 | 55.8 / 55.8 |
| 11 | ibuprofeno | 20.84 / 17.12 | +0.30 / -3.92 | 359.5 / 368.2 | 370.0 / 231.0 | 11 / 14 | 106.71 / 144.32 | 0.0 / 0.0 |
| 11 | loratadina | 5.86 / 7.89 | -2.17 / +0.15 | 140.5 / 135.4 | 64.5 / 140.7 | 8 / 10 | 35.03 / 37.65 | 0.0 / 0.0 |
| 11 | metoclopramida | 28.23 / 21.99 | -2.36 / -4.91 | 535.2 / 470.6 | 452.7 / 298.9 | 6 / 4 | 284.30 / 255.92 | 0.0 / 0.0 |
| 11 | omeprazol_inj | 6.40 / 5.97 | -0.47 / +0.72 | 120.2 / 91.9 | 103.7 / 117.2 | 6 / 6 | 263.06 / 327.13 | 0.0 / 0.0 |
| 11 | ondansetrona | 16.85 / 13.77 | -2.07 / -3.18 | 331.1 / 296.7 | 258.6 / 185.4 | 5 / 8 | 1317.86 / 1308.53 | 0.0 / 0.0 |
| 11 | paracetamol | 127.01 / 71.10 | -8.77 / -30.10 | 2376.2 / 1770.9 | 2069.2 / 717.5 | 10 / 11 | 405.49 / 354.98 | 0.0 / 0.0 |
| 11 | predinisolona | 13.23 / 12.96 | +0.37 / +1.02 | 225.1 / 208.9 | 238.1 / 244.5 | 3 / 6 | 104.22 / 132.10 | 0.0 / 0.0 |
| 11 | salbutamol | 13.69 / 11.54 | +0.60 / +1.46 | 229.1 / 176.4 | 250.1 / 227.6 | 6 / 6 | 2455.20 / 2267.47 | 0.0 / 0.0 |
| 11 | soro_antitermico_infantil | 28.11 / 21.69 | -3.06 / -5.55 | 545.4 / 476.6 | 438.4 / 282.5 | 5 / 7 | 4149.26 / 3743.90 | 0.0 / 0.0 |
| 11 | soro_fisiologico | 44.83 / 39.88 | +3.84 / +12.38 | 717.2 / 481.2 | 851.7 / 914.6 | 3 / 3 | 3099.21 / 2683.61 | 0.0 / 0.0 |
| 11 | soro_ringer | 36.69 / 27.56 | -0.11 / -7.59 | 644.1 / 615.1 | 640.1 / 349.5 | 8 / 12 | 3459.43 / 3710.95 | 0.0 / 0.0 |
| 11 | tramadol | 5.72 / 6.06 | +0.33 / +2.32 | 94.4 / 65.4 | 105.9 / 146.6 | 6 / 4 | 92.66 / 63.78 | 0.0 / 0.0 |
| 12 | adrenalina_inj | 2.00 / 2.97 | -0.47 / -0.30 | 38.4 / 50.7 | 23.8 / 41.4 | 8 / 5 | 290.21 / 162.71 | 0.0 / 0.0 |
| 12 | amoxicilina | 12.12 / 12.12 | -3.73 / -6.11 | 245.6 / 282.5 | 130.1 / 93.2 | 11 / 11 | 318.13 / 331.78 | 0.0 / 0.0 |
| 12 | azitromicina | 9.63 / 8.29 | -2.35 / -3.08 | 185.6 / 176.4 | 112.9 / 80.8 | 5 / 7 | 295.40 / 332.86 | 0.0 / 0.0 |
| 12 | ceftriaxona_inj | 9.79 / 7.90 | -2.36 / -2.20 | 188.4 / 156.5 | 115.1 / 88.3 | 7 / 10 | 2906.31 / 2334.55 | 69.1 / 69.1 |
| 12 | diazepam | 4.19 / 5.08 | -0.37 / -0.02 | 70.7 / 79.0 | 59.1 / 78.4 | 10 / 10 | 238.46 / 238.46 | 0.0 / 0.0 |
| 12 | diclofenaco | 9.28 / 9.13 | -0.84 / -0.95 | 156.9 / 156.3 | 130.8 / 126.7 | 5 / 5 | 39.89 / 44.47 | 0.0 / 0.0 |
| 12 | dipirona | 45.71 / 44.22 | -32.72 / -9.94 | 1215.6 / 839.5 | 201.4 / 531.4 | 4 / 3 | 120.34 / 113.80 | 0.0 / 0.0 |
| 12 | hidrocortisona_inj | 9.50 / 10.01 | -2.23 / -2.32 | 181.9 / 191.1 | 112.7 / 119.2 | 5 / 4 | 640.80 / 587.11 | 0.0 / 0.0 |
| 12 | ibuprofeno | 13.97 / 11.71 | -5.74 / -3.62 | 305.4 / 237.6 | 127.5 / 125.3 | 9 / 11 | 67.20 / 68.03 | 0.0 / 0.0 |
| 12 | loratadina | 13.29 / 11.68 | -0.25 / -4.84 | 209.9 / 256.0 | 202.1 / 105.9 | 10 / 8 | 69.90 / 86.54 | 0.0 / 0.0 |
| 12 | metoclopramida | 8.71 / 10.19 | +3.20 / +5.61 | 85.4 / 70.9 | 184.6 / 244.9 | 0 / 0 | 0.00 / 0.00 | 0.0 / 0.0 |
| 12 | omeprazol_inj | 7.77 / 8.37 | -3.31 / -6.81 | 171.7 / 235.2 | 69.1 / 24.2 | 7 / 12 | 465.17 / 569.10 | 0.0 / 0.0 |
| 12 | ondansetrona | 7.79 / 7.75 | +1.15 / +4.28 | 102.9 / 53.8 | 138.5 / 186.5 | 4 / 2 | 195.04 / 90.87 | 0.0 / 0.0 |
| 12 | paracetamol | 48.80 / 39.35 | +8.96 / +5.65 | 617.6 / 522.2 | 895.3 / 697.5 | 0 / 0 | 0.00 / 0.00 | 0.0 / 0.0 |
| 12 | predinisolona | 16.14 / 14.09 | -4.98 / -6.86 | 327.3 / 324.8 | 173.0 / 112.0 | 6 / 7 | 213.27 / 182.36 | 0.0 / 0.0 |
| 12 | salbutamol | 22.10 / 18.42 | -4.18 / -6.39 | 407.4 / 384.5 | 277.9 / 186.5 | 6 / 9 | 9432.77 / 7767.50 | 0.0 / 0.0 |
| 12 | soro_antitermico_infantil | 23.58 / 21.65 | -2.98 / -1.20 | 411.7 / 354.3 | 319.2 / 317.0 | 9 / 7 | 2898.74 / 2137.27 | 0.0 / 0.0 |
| 12 | soro_fisiologico | 22.34 / 21.27 | -2.50 / +9.52 | 385.1 / 182.2 | 307.5 / 477.2 | 2 / 0 | 646.71 / 0.00 | 0.0 / 0.0 |
| 12 | soro_ringer | 15.61 / 19.33 | +3.31 / +13.86 | 190.6 / 84.7 | 293.2 / 514.4 | 0 / 0 | 0.00 / 0.00 | 0.0 / 0.0 |
| 12 | tramadol | 5.90 / 6.06 | -2.01 / +0.32 | 122.6 / 88.9 | 60.2 / 99.0 | 8 / 3 | 129.13 / 64.16 | 0.0 / 0.0 |

## Medicamentos que mais pioram no consolidado (ML - baseline, custo emergencial)

Soma da diferença (modelo de ML menos baseline) nos meses avaliados. Positivo = o modelo de ML custou mais caro nesse medicamento.

| Medicamento | Diferença de custo (R$) | Diferença de episódios de ruptura | Diferença de unidades vencidas |
|---|---:|---:|---:|
| soro_fisiologico | +865.26 | +0 | +0.0 |
| soro_ringer | +478.58 | +5 | +0.0 |
| azitromicina | +324.40 | +8 | +0.0 |
| omeprazol_inj | +279.41 | +7 | +0.0 |
| dipirona | +80.90 | +9 | +0.0 |

## Medicamentos que mais melhoram no consolidado (ML - baseline, custo emergencial)

| Medicamento | Diferença de custo (R$) | Diferença de episódios de ruptura | Diferença de unidades vencidas |
|---|---:|---:|---:|
| salbutamol | -1350.53 | +3 | +0.0 |
| soro_antitermico_infantil | -957.03 | +2 | +0.0 |
| ondansetrona | -113.50 | +1 | +0.0 |
| ceftriaxona_inj | -78.97 | +7 | +0.0 |
| tramadol | -62.22 | -5 | +0.0 |

## Leitura

`Subest.` e `Superest.` decompõem o erro absoluto na direção em que ele ocorreu: subestimação é o tipo de erro que causa ruptura (previu de menos que o consumo real); superestimação é o tipo que causa compra e vencimento em excesso (previu de mais). Um MAE parecido entre baseline e modelo pode esconder uma mudança de direção do erro — por isso as duas colunas são reportadas separadamente, nunca só o MAE agregado.

Herda a mesma limitação do relatório de impacto simulado: cenário sobre dados sintéticos, não evidência de piloto real.
