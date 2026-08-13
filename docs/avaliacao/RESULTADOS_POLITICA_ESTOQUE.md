# Avaliação de política de estoque por perfil e prazo (Issue #79)

> **Transparência financeira:** custos são estimativas com dados sintéticos e preços de referência; não representam economia comprovada de um hospital.

A previsão é mantida idêntica em cada comparação. Só muda o buffer de estoque, aplicado por perfil de demanda e faixa de prazo — nunca por configuração manual de medicamento.

## Grupos e políticas avaliadas

| Política | Medicamento | Perfil | Prazo | Buffer |
|---|---|---|---|---:|
| fixa_020 | adrenalina_inj | erratico | longo | 0.20 |
| fixa_020 | amoxicilina | intermitente | longo | 0.20 |
| fixa_020 | azitromicina | intermitente | longo | 0.20 |
| fixa_020 | ceftriaxona_inj | intermitente | longo | 0.20 |
| fixa_020 | diazepam | erratico | longo | 0.20 |
| fixa_020 | diclofenaco | intermitente | curto | 0.20 |
| fixa_020 | dipirona | continuo | curto | 0.20 |
| fixa_020 | hidrocortisona_inj | intermitente | longo | 0.20 |
| fixa_020 | ibuprofeno | continuo | curto | 0.20 |
| fixa_020 | loratadina | intermitente | curto | 0.20 |
| fixa_020 | metoclopramida | intermitente | curto | 0.20 |
| fixa_020 | omeprazol_inj | intermitente | curto | 0.20 |
| fixa_020 | ondansetrona | intermitente | curto | 0.20 |
| fixa_020 | paracetamol | continuo | curto | 0.20 |
| fixa_020 | predinisolona | intermitente | longo | 0.20 |
| fixa_020 | salbutamol | intermitente | longo | 0.20 |
| fixa_020 | soro_antitermico_infantil | intermitente | curto | 0.20 |
| fixa_020 | soro_fisiologico | continuo | curto | 0.20 |
| fixa_020 | soro_ringer | continuo | curto | 0.20 |
| fixa_020 | tramadol | intermitente | longo | 0.20 |
| perfil_prazo_moderada | adrenalina_inj | erratico | longo | 0.50 |
| perfil_prazo_moderada | amoxicilina | intermitente | longo | 0.35 |
| perfil_prazo_moderada | azitromicina | intermitente | longo | 0.35 |
| perfil_prazo_moderada | ceftriaxona_inj | intermitente | longo | 0.35 |
| perfil_prazo_moderada | diazepam | erratico | longo | 0.50 |
| perfil_prazo_moderada | diclofenaco | intermitente | curto | 0.20 |
| perfil_prazo_moderada | dipirona | continuo | curto | 0.10 |
| perfil_prazo_moderada | hidrocortisona_inj | intermitente | longo | 0.35 |
| perfil_prazo_moderada | ibuprofeno | continuo | curto | 0.10 |
| perfil_prazo_moderada | loratadina | intermitente | curto | 0.20 |
| perfil_prazo_moderada | metoclopramida | intermitente | curto | 0.20 |
| perfil_prazo_moderada | omeprazol_inj | intermitente | curto | 0.20 |
| perfil_prazo_moderada | ondansetrona | intermitente | curto | 0.20 |
| perfil_prazo_moderada | paracetamol | continuo | curto | 0.10 |
| perfil_prazo_moderada | predinisolona | intermitente | longo | 0.35 |
| perfil_prazo_moderada | salbutamol | intermitente | longo | 0.35 |
| perfil_prazo_moderada | soro_antitermico_infantil | intermitente | curto | 0.20 |
| perfil_prazo_moderada | soro_fisiologico | continuo | curto | 0.10 |
| perfil_prazo_moderada | soro_ringer | continuo | curto | 0.10 |
| perfil_prazo_moderada | tramadol | intermitente | longo | 0.35 |
| perfil_prazo_conservadora | adrenalina_inj | erratico | longo | 0.70 |
| perfil_prazo_conservadora | amoxicilina | intermitente | longo | 0.50 |
| perfil_prazo_conservadora | azitromicina | intermitente | longo | 0.50 |
| perfil_prazo_conservadora | ceftriaxona_inj | intermitente | longo | 0.50 |
| perfil_prazo_conservadora | diazepam | erratico | longo | 0.70 |
| perfil_prazo_conservadora | diclofenaco | intermitente | curto | 0.35 |
| perfil_prazo_conservadora | dipirona | continuo | curto | 0.20 |
| perfil_prazo_conservadora | hidrocortisona_inj | intermitente | longo | 0.50 |
| perfil_prazo_conservadora | ibuprofeno | continuo | curto | 0.20 |
| perfil_prazo_conservadora | loratadina | intermitente | curto | 0.35 |
| perfil_prazo_conservadora | metoclopramida | intermitente | curto | 0.35 |
| perfil_prazo_conservadora | omeprazol_inj | intermitente | curto | 0.35 |
| perfil_prazo_conservadora | ondansetrona | intermitente | curto | 0.35 |
| perfil_prazo_conservadora | paracetamol | continuo | curto | 0.20 |
| perfil_prazo_conservadora | predinisolona | intermitente | longo | 0.50 |
| perfil_prazo_conservadora | salbutamol | intermitente | longo | 0.50 |
| perfil_prazo_conservadora | soro_antitermico_infantil | intermitente | curto | 0.35 |
| perfil_prazo_conservadora | soro_fisiologico | continuo | curto | 0.20 |
| perfil_prazo_conservadora | soro_ringer | continuo | curto | 0.20 |
| perfil_prazo_conservadora | tramadol | intermitente | longo | 0.50 |

## Decisão formal no protocolo v1.1.0 (janela longa)

A decisão abaixo usa as quatro janelas temporais de 28 dias da Issue #84. O modelo é retreinado a cada 7 dias, mas estoque e lotes não são reiniciados dentro da janela; assim o prazo de entrega de 5–12 dias pode afetar a operação avaliada. Cada política é comparada à `fixa_020` com a mesma previsão.

### Previsão: baseline

| Política | Status | Redução de custo | Janelas na meta | Motivo principal |
|---|---|---:|---:|---|
| perfil_prazo_moderada | rejeitado | 6.0% | 1/4 | Redução agregada de custo 6.00% abaixo da meta de 10.00%.; Consistência insuficiente: meta atingida em 1/4 janelas.; Piora operacional relevante em unidades_em_ruptura: aumento de 5.66%. |
| perfil_prazo_conservadora | aprovado | 23.1% | 4/4 | Meta agregada de redução do custo emergencial atingida.; Meta atingida na fração mínima exigida de janelas.; Sem piora operacional relevante nas métricas de bloqueio. |

### Previsão: modelo_atual

| Política | Status | Redução de custo | Janelas na meta | Motivo principal |
|---|---|---:|---:|---|
| perfil_prazo_moderada | rejeitado | 6.2% | 1/4 | Redução agregada de custo 6.19% abaixo da meta de 10.00%.; Consistência insuficiente: meta atingida em 1/4 janelas.; Piora operacional relevante em unidades_em_ruptura: aumento de 7.05%. |
| perfil_prazo_conservadora | aprovado | 25.2% | 4/4 | Meta agregada de redução do custo emergencial atingida.; Meta atingida na fração mínima exigida de janelas.; Sem piora operacional relevante nas métricas de bloqueio. |

## Simulação contínua mensal (evidência complementar)

Dentro de cada mês o estoque não é reiniciado semanalmente, então pedidos têm tempo de chegar. `estoque_medio_unidades` explicita o trade-off de capital/estoque excedente; não foi convertido em reais porque o MVP não possui custo real de armazenagem.

| Mês | Previsão | Política | Custo emergencial (R$) | Episódios | Unidades em ruptura | Vencidas | Recomendada | Estoque médio |
|---|---|---|---:|---:|---:|---:|---:|---:|
| 10 | baseline | fixa_020 | 7672.78 | 73 | 2559.52 | 173.77 | 46339.31 | 3916.19 |
| 10 | baseline | perfil_prazo_conservadora | 5488.58 | 45 | 2052.75 | 173.77 | 47934.68 | 4684.26 |
| 10 | baseline | perfil_prazo_moderada | 7100.25 | 67 | 2971.76 | 173.77 | 45902.67 | 3790.80 |
| 10 | modelo_atual | fixa_020 | 11179.09 | 93 | 3513.91 | 173.77 | 46377.65 | 3526.48 |
| 10 | modelo_atual | perfil_prazo_conservadora | 7935.49 | 50 | 2863.29 | 173.77 | 48237.73 | 4365.25 |
| 10 | modelo_atual | perfil_prazo_moderada | 10238.07 | 90 | 4242.25 | 173.77 | 45631.95 | 3540.20 |
| 11 | baseline | fixa_020 | 21463.98 | 125 | 9253.93 | 421.81 | 43796.24 | 4668.47 |
| 11 | baseline | perfil_prazo_conservadora | 17159.93 | 83 | 8410.59 | 421.81 | 45750.49 | 5266.81 |
| 11 | baseline | perfil_prazo_moderada | 20329.71 | 113 | 9729.54 | 421.81 | 43177.27 | 4673.40 |
| 11 | modelo_atual | fixa_020 | 21402.28 | 158 | 9223.27 | 421.81 | 40881.14 | 4976.46 |
| 11 | modelo_atual | perfil_prazo_conservadora | 15851.98 | 97 | 8038.57 | 421.81 | 42905.14 | 5635.61 |
| 11 | modelo_atual | perfil_prazo_moderada | 19869.55 | 133 | 9747.51 | 421.81 | 40373.66 | 5022.33 |
| 12 | baseline | fixa_020 | 18967.48 | 116 | 3740.61 | 69.14 | 31072.27 | 10365.19 |
| 12 | baseline | perfil_prazo_conservadora | 12992.44 | 80 | 2617.94 | 69.14 | 33470.28 | 10894.36 |
| 12 | baseline | perfil_prazo_moderada | 16168.41 | 108 | 3858.70 | 69.14 | 30998.80 | 10513.37 |
| 12 | modelo_atual | fixa_020 | 15111.57 | 114 | 3328.26 | 69.14 | 29668.98 | 10505.27 |
| 12 | modelo_atual | perfil_prazo_conservadora | 11709.46 | 66 | 2365.43 | 69.14 | 31754.63 | 11143.35 |
| 12 | modelo_atual | perfil_prazo_moderada | 13940.84 | 96 | 3496.67 | 69.14 | 29518.57 | 10675.17 |

## Consolidado contínuo e trade-offs

Variação contra `fixa_020` do mesmo método; negativo em custo/ruptura é melhora e positivo em estoque médio é o capital adicional mantido no cenário.

| Previsão | Política | Custo (R$) | Δ custo | Episódios | Δ episódios | Unidades ruptura | Δ ruptura | Vencidas | Estoque médio | Δ estoque médio |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | fixa_020 | 48104.24 | +0.0% | 314 | +0.0% | 15554.05 | +0.0% | 664.72 | 18949.84 | +0.0% |
| baseline | perfil_prazo_conservadora | 35640.95 | -25.9% | 208 | -33.8% | 13081.28 | -15.9% | 664.72 | 20845.42 | +10.0% |
| baseline | perfil_prazo_moderada | 43598.36 | -9.4% | 288 | -8.3% | 16559.99 | +6.5% | 664.72 | 18977.57 | +0.1% |
| modelo_atual | fixa_020 | 47692.93 | +0.0% | 365 | +0.0% | 16065.44 | +0.0% | 664.72 | 19008.22 | +0.0% |
| modelo_atual | perfil_prazo_conservadora | 35496.94 | -25.6% | 213 | -41.6% | 13267.29 | -17.4% | 664.72 | 21144.21 | +11.2% |
| modelo_atual | perfil_prazo_moderada | 44048.46 | -7.6% | 319 | -12.6% | 17486.43 | +8.8% | 664.72 | 19237.70 | +1.2% |

## Limitações e próximo passo

A aprovação valida somente o cenário simulado, não uma operação hospitalar real. Antes de adotar uma política aprovada, o time deve decidir o limite aceitável de estoque médio e validar o comportamento em piloto; nenhuma política é aplicada ao dashboard ou ao motor de recomendação nesta issue.
