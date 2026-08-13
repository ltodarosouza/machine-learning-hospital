# Relatório operacional por medicamento, mês e tipo de erro (Issue #76)

Decompõe os totais agregados do relatório de precisão (`RESULTADOS_MODELAGEM.md`) e do relatório de impacto simulado (`RESULTADOS_IMPACTO_SIMULADO.md`) até medicamento e mês, sobre o mesmo corte temporal — para identificar quais itens e períodos explicam a diferença de custo e de ruptura entre baseline e modelo de ML, sem esconder os casos em que o ML perde.

**Comando para regenerar:** `python src/evaluation/relatorio_operacional.py` (ou `python scripts/relatorio_final.py`, que também regenera este relatório).

## Detalhamento por medicamento e mês

| Mês | Medicamento | MAE base/ML | Viés base/ML | Subest. (un) base/ML | Superest. (un) base/ML | Episódios ruptura base/ML | Custo emergencial (R$) base/ML | Vencidas (un) base/ML |
|---|---|---|---|---|---|---|---|---|
| 10 | adrenalina_inj | 2.21 / 3.00 | +0.53 / +2.27 | 29.4 / 12.8 | 47.9 / 92.2 | 0 / 0 | 0.00 / 0.00 | 0.0 / 0.0 |
| 10 | amoxicilina | 11.85 / 16.07 | +1.11 / +11.61 | 187.9 / 77.9 | 226.9 / 484.4 | 6 / 3 | 94.24 / 36.08 | 0.0 / 0.0 |
| 10 | azitromicina | 7.64 / 10.35 | -0.31 / +8.08 | 139.2 / 39.6 | 128.2 / 322.5 | 3 / 0 | 55.30 / 0.00 | 0.0 / 0.0 |
| 10 | ceftriaxona_inj | 6.84 / 10.21 | +1.14 / +7.57 | 99.6 / 46.1 | 139.6 / 311.1 | 5 / 5 | 1931.27 / 1351.47 | 155.3 / 155.3 |
| 10 | diazepam | 3.48 / 5.88 | +0.86 / +5.74 | 45.9 / 2.5 | 75.9 / 203.3 | 0 / 0 | 0.00 / 0.00 | 0.0 / 0.0 |
| 10 | diclofenaco | 12.85 / 18.02 | +2.49 / +12.65 | 181.4 / 94.0 | 268.4 / 536.6 | 4 / 3 | 40.29 / 16.94 | 0.0 / 0.0 |
| 10 | dipirona | 106.48 / 89.65 | +44.33 / +52.33 | 1087.7 / 653.1 | 2639.2 / 2484.8 | 2 / 3 | 50.69 / 12.78 | 0.0 / 0.0 |
| 10 | hidrocortisona_inj | 6.20 / 12.80 | +1.77 / +12.25 | 77.4 / 9.7 | 139.4 / 438.5 | 8 / 4 | 647.60 / 485.60 | 18.4 / 18.4 |
| 10 | ibuprofeno | 20.53 / 25.42 | +2.14 / +20.49 | 321.8 / 86.2 | 396.8 / 803.4 | 12 / 6 | 93.86 / 34.77 | 0.0 / 0.0 |
| 10 | loratadina | 10.64 / 13.51 | +3.57 / +12.13 | 123.7 / 24.1 | 248.7 / 448.6 | 6 / 4 | 54.52 / 33.93 | 0.0 / 0.0 |
| 10 | metoclopramida | 22.21 / 22.34 | +6.97 / +13.00 | 266.6 / 163.6 | 510.6 / 618.5 | 0 / 0 | 0.00 / 0.00 | 0.0 / 0.0 |
| 10 | omeprazol_inj | 7.13 / 11.09 | +2.43 / +9.39 | 82.3 / 29.8 | 167.3 / 358.3 | 3 / 0 | 102.00 / 0.00 | 0.0 / 0.0 |
| 10 | ondansetrona | 18.17 / 16.28 | +9.59 / +9.88 | 150.1 / 112.0 | 485.6 / 457.6 | 4 / 4 | 894.86 / 894.86 | 0.0 / 0.0 |
| 10 | paracetamol | 81.28 / 74.61 | +36.87 / +48.40 | 777.1 / 458.5 | 2067.6 / 2152.6 | 3 / 2 | 67.75 / 48.70 | 0.0 / 0.0 |
| 10 | predinisolona | 11.40 / 16.54 | +3.44 / +15.78 | 139.3 / 13.3 | 259.8 / 565.6 | 4 / 0 | 44.82 / 0.00 | 0.0 / 0.0 |
| 10 | salbutamol | 18.48 / 22.47 | +3.37 / +13.14 | 264.4 / 163.2 | 382.4 / 623.1 | 3 / 0 | 237.60 / 0.00 | 0.0 / 0.0 |
| 10 | soro_antitermico_infantil | 33.53 / 35.18 | +12.93 / +27.55 | 360.5 / 133.6 | 813.0 / 1097.8 | 5 / 3 | 1668.34 / 1313.14 | 0.0 / 0.0 |
| 10 | soro_fisiologico | 65.99 / 58.26 | +32.91 / +23.26 | 578.9 / 612.5 | 1730.9 / 1426.6 | 2 / 4 | 1577.57 / 2589.67 | 0.0 / 0.0 |
| 10 | soro_ringer | 31.32 / 29.13 | +13.89 / +18.80 | 305.1 / 180.8 | 791.1 / 838.8 | 1 / 0 | 100.86 / 0.00 | 0.0 / 0.0 |
| 10 | tramadol | 5.14 / 8.25 | +1.39 / +7.51 | 65.7 / 13.1 | 114.2 / 275.8 | 2 / 0 | 11.23 / 0.00 | 0.0 / 0.0 |
| 11 | adrenalina_inj | 2.24 / 2.96 | +0.03 / +2.19 | 38.7 / 13.6 | 39.7 / 90.1 | 2 / 0 | 140.86 / 0.00 | 0.0 / 0.0 |
| 11 | amoxicilina | 10.14 / 11.13 | +0.70 / +6.90 | 165.1 / 74.0 | 189.6 / 315.5 | 12 / 7 | 332.15 / 292.63 | 0.0 / 0.0 |
| 11 | azitromicina | 7.06 / 8.72 | -0.84 / +5.32 | 138.4 / 59.4 | 108.9 / 245.7 | 4 / 0 | 57.40 / 0.00 | 0.0 / 0.0 |
| 11 | ceftriaxona_inj | 9.61 / 11.13 | +0.40 / +6.33 | 161.1 / 84.1 | 175.1 / 305.5 | 7 / 7 | 3948.00 / 3948.00 | 366.0 / 366.0 |
| 11 | diazepam | 4.03 / 4.98 | -0.67 / +3.70 | 82.4 / 22.4 | 58.9 / 151.9 | 1 / 1 | 9.09 / 9.09 | 0.0 / 0.0 |
| 11 | diclofenaco | 14.61 / 13.13 | -3.87 / +2.89 | 323.4 / 179.2 | 187.9 / 280.4 | 7 / 5 | 93.26 / 35.84 | 0.0 / 0.0 |
| 11 | dipirona | 116.15 / 88.91 | +2.41 / +7.91 | 1990.4 / 1417.4 | 2074.9 / 1694.3 | 4 / 3 | 377.43 / 352.73 | 0.0 / 0.0 |
| 11 | hidrocortisona_inj | 7.01 / 8.94 | -1.90 / +3.55 | 155.9 / 94.2 | 89.4 / 218.6 | 11 / 2 | 733.37 / 51.60 | 55.8 / 55.8 |
| 11 | ibuprofeno | 20.84 / 18.13 | +0.30 / +6.58 | 359.5 / 202.1 | 370.0 / 432.6 | 11 / 11 | 106.71 / 67.44 | 0.0 / 0.0 |
| 11 | loratadina | 5.86 / 9.13 | -2.17 / +5.71 | 140.5 / 59.8 | 64.5 / 259.8 | 8 / 3 | 35.03 / 12.08 | 0.0 / 0.0 |
| 11 | metoclopramida | 28.23 / 23.56 | -2.36 / +2.73 | 535.2 / 364.5 | 452.7 / 460.0 | 6 / 4 | 284.30 / 222.20 | 0.0 / 0.0 |
| 11 | omeprazol_inj | 6.40 / 7.08 | -0.47 / +5.15 | 120.2 / 33.7 | 103.7 / 214.1 | 6 / 3 | 263.06 / 92.64 | 0.0 / 0.0 |
| 11 | ondansetrona | 16.85 / 15.73 | -2.07 / +4.02 | 331.1 / 204.9 | 258.6 / 345.5 | 5 / 5 | 1317.86 / 1008.90 | 0.0 / 0.0 |
| 11 | paracetamol | 127.01 / 91.19 | -8.77 / +4.42 | 2376.2 / 1518.4 | 2069.2 / 1673.2 | 10 / 8 | 405.49 / 312.62 | 0.0 / 0.0 |
| 11 | predinisolona | 13.23 / 15.73 | +0.37 / +10.02 | 225.1 / 99.9 | 238.1 / 450.7 | 3 / 3 | 104.22 / 39.79 | 0.0 / 0.0 |
| 11 | salbutamol | 13.69 / 17.16 | +0.60 / +11.80 | 229.1 / 93.8 | 250.1 / 506.8 | 6 / 0 | 2455.20 / 0.00 | 0.0 / 0.0 |
| 11 | soro_antitermico_infantil | 28.11 / 29.27 | -3.06 / +8.50 | 545.4 / 363.5 | 438.4 / 661.0 | 5 / 4 | 4149.26 / 3211.38 | 0.0 / 0.0 |
| 11 | soro_fisiologico | 44.83 / 49.37 | +3.84 / +29.83 | 717.2 / 342.1 | 851.7 / 1386.0 | 3 / 3 | 3099.21 / 2290.73 | 0.0 / 0.0 |
| 11 | soro_ringer | 36.69 / 28.33 | -0.11 / +1.55 | 644.1 / 468.6 | 640.1 / 522.8 | 8 / 7 | 3459.43 / 2825.81 | 0.0 / 0.0 |
| 11 | tramadol | 5.72 / 7.99 | +0.33 / +6.84 | 94.4 / 20.1 | 105.9 / 259.5 | 6 / 1 | 92.66 / 10.93 | 0.0 / 0.0 |
| 12 | adrenalina_inj | 2.00 / 3.53 | -0.47 / +2.94 | 38.4 / 9.1 | 23.8 / 100.4 | 8 / 5 | 290.21 / 162.71 | 0.0 / 0.0 |
| 12 | amoxicilina | 12.12 / 11.11 | -3.73 / +4.05 | 245.6 / 109.4 | 130.1 / 234.9 | 11 / 8 | 318.13 / 255.43 | 0.0 / 0.0 |
| 12 | azitromicina | 9.63 / 10.38 | -2.35 / +4.83 | 185.6 / 86.0 | 112.9 / 235.7 | 5 / 3 | 295.40 / 74.98 | 0.0 / 0.0 |
| 12 | ceftriaxona_inj | 9.79 / 9.23 | -2.36 / +4.22 | 188.4 / 77.6 | 115.1 / 208.5 | 7 / 6 | 2906.31 / 1533.97 | 69.1 / 69.1 |
| 12 | diazepam | 4.19 / 5.70 | -0.37 / +4.71 | 70.7 / 15.4 | 59.1 / 161.3 | 10 / 10 | 238.46 / 238.46 | 0.0 / 0.0 |
| 12 | diclofenaco | 9.28 / 12.57 | -0.84 / +9.10 | 156.9 / 53.7 | 130.8 / 335.9 | 5 / 2 | 39.89 / 11.34 | 0.0 / 0.0 |
| 12 | dipirona | 45.71 / 50.99 | -32.72 / +28.08 | 1215.6 / 355.1 | 201.4 / 1225.5 | 4 / 3 | 120.34 / 64.24 | 0.0 / 0.0 |
| 12 | hidrocortisona_inj | 9.50 / 11.05 | -2.23 / +6.58 | 181.9 / 69.2 | 112.7 / 273.2 | 5 / 0 | 640.80 / 0.00 | 0.0 / 0.0 |
| 12 | ibuprofeno | 13.97 / 11.97 | -5.74 / +4.00 | 305.4 / 123.5 | 127.5 / 247.5 | 9 / 6 | 67.20 / 22.53 | 0.0 / 0.0 |
| 12 | loratadina | 13.29 / 12.24 | -0.25 / +6.06 | 209.9 / 95.7 | 202.1 / 283.6 | 10 / 6 | 69.90 / 27.50 | 0.0 / 0.0 |
| 12 | metoclopramida | 8.71 / 17.00 | +3.20 / +16.20 | 85.4 / 12.4 | 184.6 / 514.5 | 0 / 0 | 0.00 / 0.00 | 0.0 / 0.0 |
| 12 | omeprazol_inj | 7.77 / 6.71 | -3.31 / +1.79 | 171.7 / 76.2 | 69.1 / 131.8 | 7 / 3 | 465.17 / 167.23 | 0.0 / 0.0 |
| 12 | ondansetrona | 7.79 / 12.49 | +1.15 / +11.24 | 102.9 / 19.4 | 138.5 / 367.8 | 4 / 0 | 195.04 / 0.00 | 0.0 / 0.0 |
| 12 | paracetamol | 48.80 / 50.94 | +8.96 / +34.78 | 617.6 / 250.6 | 895.3 / 1328.7 | 0 / 0 | 0.00 / 0.00 | 0.0 / 0.0 |
| 12 | predinisolona | 16.14 / 15.13 | -4.98 / +4.46 | 327.3 / 165.3 | 173.0 / 303.7 | 6 / 8 | 213.27 / 92.62 | 0.0 / 0.0 |
| 12 | salbutamol | 22.10 / 18.04 | -4.18 / +3.54 | 407.4 / 224.6 | 277.9 / 334.5 | 6 / 4 | 9432.77 / 7445.57 | 0.0 / 0.0 |
| 12 | soro_antitermico_infantil | 23.58 / 19.82 | -2.98 / +9.02 | 411.7 / 167.4 | 319.2 / 447.1 | 9 / 6 | 2898.74 / 1237.47 | 0.0 / 0.0 |
| 12 | soro_fisiologico | 22.34 / 27.20 | -2.50 / +17.90 | 385.1 / 144.2 | 307.5 / 698.9 | 2 / 0 | 646.71 / 0.00 | 0.0 / 0.0 |
| 12 | soro_ringer | 15.61 / 24.27 | +3.31 / +21.50 | 190.6 / 42.9 | 293.2 / 709.6 | 0 / 0 | 0.00 / 0.00 | 0.0 / 0.0 |
| 12 | tramadol | 5.90 / 8.64 | -2.01 / +6.36 | 122.6 / 35.3 | 60.2 / 232.5 | 8 / 0 | 129.13 / 0.00 | 0.0 / 0.0 |

## Medicamentos que mais pioram no consolidado (ML - baseline, custo emergencial)

Soma da diferença (modelo de ML menos baseline) nos meses avaliados. Positivo = o modelo de ML custou mais caro nesse medicamento.

| Medicamento | Diferença de custo (R$) | Diferença de episódios de ruptura | Diferença de unidades vencidas |
|---|---:|---:|---:|
| diazepam | +0.00 | +0 | +0.0 |
| metoclopramida | -62.10 | -2 | +0.0 |
| loratadina | -85.94 | -11 | +0.0 |
| diclofenaco | -109.32 | -6 | +0.0 |
| paracetamol | -111.92 | -3 | +0.0 |

## Medicamentos que mais melhoram no consolidado (ML - baseline, custo emergencial)

| Medicamento | Diferença de custo (R$) | Diferença de episódios de ruptura | Diferença de unidades vencidas |
|---|---:|---:|---:|
| salbutamol | -4680.00 | -11 | +0.0 |
| soro_antitermico_infantil | -2954.35 | -6 | +0.0 |
| ceftriaxona_inj | -1952.14 | -1 | +0.0 |
| hidrocortisona_inj | -1484.57 | -18 | +0.0 |
| soro_ringer | -734.47 | -2 | +0.0 |

## Leitura

`Subest.` e `Superest.` decompõem o erro absoluto na direção em que ele ocorreu: subestimação é o tipo de erro que causa ruptura (previu de menos que o consumo real); superestimação é o tipo que causa compra e vencimento em excesso (previu de mais). Um MAE parecido entre baseline e modelo pode esconder uma mudança de direção do erro — por isso as duas colunas são reportadas separadamente, nunca só o MAE agregado.

Herda a mesma limitação do relatório de impacto simulado: cenário sobre dados sintéticos, não evidência de piloto real.
