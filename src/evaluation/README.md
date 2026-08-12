# `src/evaluation/`

Métricas de avaliação: precisão dos modelos de previsão (esta pasta) e impacto simulado do motor de recomendação (Issues #17/#18, pendentes).

## `comparar_modelos.py` (Issue #13) — pronto

Roda o baseline (`src/models/baseline.py`, Issue #11) e o modelo de ML (`src/models/modelo_demanda.py`, Issue #12) sobre o mesmo período de teste e calcula MAE e MAPE, por medicamento e agregado. O modelo de ML é retreinado do zero a cada janela de 7 dias, usando só dado anterior ao corte — nunca olha o "futuro" que está sendo avaliado.

```bash
python src/evaluation/comparar_modelos.py
```

Gera [`docs/arquitetura/RESULTADOS_MODELAGEM.md`](../../docs/arquitetura/RESULTADOS_MODELAGEM.md) com o relatório completo e os metadados da execução. Para reproduzir os números no estado atual do repositório, execute:

```bash
python src/evaluation/comparar_modelos.py
```

**Resultado atual (período de teste 2025-12-04 a 2025-12-31, 4 janelas de 7 dias):** o modelo de ML reduz o MAE agregado em **2.0%** frente ao baseline (9.79 vs. 9.99 unidades/dia), vencendo em 13 dos 20 medicamentos e perdendo em 7. **Reportado sem maquiagem** — a vitória é pequena e não é unânime, e isso é informação real, não um problema a esconder. Ver o relatório completo para o detalhamento por medicamento e para decidir se vale a pena investir em melhorar o modelo (mais dado de treino, outras features, outro algoritmo) antes de seguir para o motor de recomendação.

**Por que só 4 janelas (28 dias) de teste:** o modelo de ML é retreinado do zero a cada janela (é o jeito correto de simular "o que o modelo saberia prever, sem olhar o futuro"), o que fica lento com muitas janelas. 28 dias foi uma escolha de custo-benefício para essa task — se o time achar pouco, `avaliar_modelo_periodo` aceita qualquer intervalo de datas.
