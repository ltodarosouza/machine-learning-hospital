# `src/evaluation/`

Métricas de avaliação: precisão dos modelos de previsão (esta pasta) e impacto simulado do motor de recomendação (Issues #17/#18, pendentes).

## `comparar_modelos.py` (Issue #13) — pronto

Roda o baseline (`src/models/baseline.py`, Issue #11) e o modelo de ML (`src/models/modelo_demanda.py`, Issue #12) sobre o mesmo período de teste e calcula MAE e MAPE, por medicamento e agregado. O modelo de ML é retreinado do zero a cada janela de 7 dias, usando só dado anterior ao corte — nunca olha o "futuro" que está sendo avaliado.

```bash
python src/evaluation/comparar_modelos.py
```

Gera [`docs/arquitetura/RESULTADOS_MODELAGEM.md`](../../docs/arquitetura/RESULTADOS_MODELAGEM.md) com o relatório completo, incluindo uma seção "Reprodutibilidade" (commit, período, algoritmo, hiperparâmetros) — regenerar sempre que o dataset ou o modelo mudarem, para o relatório nunca ficar defasado em relação ao código (Issue #54).

**Resultado atual (período de teste 2025-12-04 a 2025-12-31, 4 janelas de 7 dias, dataset de 4 anos):** o modelo de ML reduz o MAE agregado em **1.9%** frente ao baseline (10.42 vs. 10.62 unidades/dia), vencendo em 10 dos 20 medicamentos e perdendo em 10. **Reportado sem maquiagem** — é uma vantagem modesta, não uma vitória esmagadora, e essa é a informação real que temos agora.

Este número passou por três rodadas de melhoria — ver [`src/models/README.md`](../models/README.md) para o histórico completo: (1) troca de Random Forest para XGBoost; (2) extensão do período histórico de 2 para 4 anos + tuning de hiperparâmetros; (3) correção de vazamento na normalização de features (feita por outra pessoa do time) exigiu retunar de novo. **Importante:** o `%` de redução não é comparável entre rodadas 1→2, porque estender o dataset sintético mudou os valores do período de teste (mesma data de calendário, valor diferente — efeito do gerador usar uma sequência de aleatoriedade sobre o array do período inteiro). Dentro de cada versão do dataset/features, a comparação é válida e honesta.

**Por que só 4 janelas (28 dias) de teste:** o modelo de ML é retreinado do zero a cada janela (é o jeito correto de simular "o que o modelo saberia prever, sem olhar o futuro"), o que fica lento com muitas janelas. 28 dias foi uma escolha de custo-benefício para essa task — se o time achar pouco, `avaliar_modelo_periodo` aceita qualquer intervalo de datas.
