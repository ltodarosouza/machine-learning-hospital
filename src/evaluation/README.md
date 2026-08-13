# `src/evaluation/`

Métricas de avaliação: precisão dos modelos de previsão (`comparar_modelos.py`) e impacto simulado do motor de recomendação (`impacto_simulado.py`, Issue #17).

**Comando único recomendado**, que treina o modelo oficial e gera os dois relatórios abaixo numa execução só: `python scripts/relatorio_final.py` (ver `src/models/README.md` para detalhes e flags).

## `comparar_modelos.py` (Issue #13) — pronto

Roda o baseline (`src/models/baseline.py`, Issue #11) e o modelo de ML (`src/models/modelo_demanda.py`, Issue #12) sobre o mesmo período de teste e calcula MAE e MAPE, por medicamento e agregado. O modelo de ML é retreinado do zero a cada janela de 7 dias, usando só dado anterior ao corte — nunca olha o "futuro" que está sendo avaliado.

```bash
python src/evaluation/comparar_modelos.py
```

Gera [`docs/arquitetura/RESULTADOS_MODELAGEM.md`](../../docs/arquitetura/RESULTADOS_MODELAGEM.md) com o relatório completo, incluindo uma seção "Reprodutibilidade" (commit, período, algoritmo, hiperparâmetros) — regenerar sempre que o dataset ou o modelo mudarem, para o relatório nunca ficar defasado em relação ao código (Issue #54).

**Resultado atual** (dataset com as 4 issues de realismo do gerador — #58-#61 — já aplicadas, modelo retunado): o modelo de ML reduz o MAE agregado em **8.4%** frente ao baseline (14.22 vs. 15.52 unidades/dia), vencendo em 14 dos 20 medicamentos. **Reportado sem maquiagem.** O MAE absoluto não é comparável a rodadas anteriores (era ~9-10) — o dataset ficou estruturalmente mais variável (surtos, demanda censurada), não é o modelo piorando.

**Achado importante:** apesar do MAE melhor, a simulação de impacto (`impacto_simulado.py`, abaixo) mostra o modelo causando **mais** ruptura que o baseline. Ver `src/models/README.md` para a hipótese de por que isso acontece (MAE não é a métrica certa para evitar ruptura) — não escondemos esse resultado, é informação real.

Histórico completo das rodadas de melhoria (troca de algoritmo, extensão do dataset, correção de vazamento de normalização, adição de realismo no gerador, retuning): ver [`src/models/README.md`](../models/README.md).

**Por que só 4 janelas (28 dias) de teste:** o modelo de ML é retreinado do zero a cada janela (é o jeito correto de simular "o que o modelo saberia prever, sem olhar o futuro"), o que fica lento com muitas janelas. 28 dias foi uma escolha de custo-benefício para essa task — se o time achar pouco, `avaliar_modelo_periodo` aceita qualquer intervalo de datas.

## `impacto_simulado.py` (Issue #17) — pronto

Simula, dia a dia, uma política de reposição orientada pela previsão de demanda (baseline ou modelo de ML): pede o necessário para cobrir o lead time do fornecedor mais um estoque de segurança, e contabiliza rupturas, compras emergenciais e o custo delas ao preço unitário de referência. Compara os dois métodos mês a mês e no consolidado.

```bash
python src/evaluation/impacto_simulado.py
```

Gera [`docs/arquitetura/RESULTADOS_IMPACTO_SIMULADO.md`](../../docs/arquitetura/RESULTADOS_IMPACTO_SIMULADO.md). **Limitação explícita no próprio relatório:** é simulação sobre dado sintético, não piloto real; vencimentos ainda não são estimados porque a simulação não movimenta lotes individualmente (fica para uma iteração futura).
