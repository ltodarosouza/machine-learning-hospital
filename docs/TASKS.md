# Divisão de tarefas (5 pessoas)

Objetivo desta divisão: cada pessoa trabalha em **pastas próprias**, em **branches próprias**, com o mínimo de dependência bloqueante entre elas. As dependências que existem (a cadeia dados → features → modelo → recomendação → dashboard) são resolvidas com **contratos de interface definidos antes de codar** (ver [docs/arquitetura/CONTRATOS.md](arquitetura/CONTRATOS.md)) e **dados de exemplo (mock)**, não com espera sequencial.

## Reunião de kickoff (obrigatória antes de começar a codar, ~1-2h)

Toda a equipe junta, ao vivo ou por chamada, para:
1. Ler [docs/negocio/CONTEXTO.md](negocio/CONTEXTO.md) juntos e alinhar entendimento do problema.
2. Preencher [docs/arquitetura/CONTRATOS.md](arquitetura/CONTRATOS.md) em conjunto — especialmente o schema de dados da seção 1, que é a base de tudo.
3. Definir o hospital/setor/medicamentos fictícios ou fonte pública que servirão de base para o MVP.
4. Cada pessoa cria sua branch a partir do `main` e começa.

Sem esse passo, os 5 módulos evoluem com premissas diferentes e a integração final não funciona.

---

## Pessoa A — Dados & Integração

**Branch:** `feature/data-ingestion` · **Pastas:** `src/data_ingestion/`, `data/`

**Escopo:**
- Levantar e documentar as fontes de dados internas (simuladas, já que não teremos acesso a sistema hospitalar real) e externas (públicas: DATASUS/OpenDataSUS, InfoDengue, INMET, calendário de feriados).
- Gerar um dataset sintético realista de consumo de medicamentos (ex.: 1 hospital, 1 setor, 10–30 medicamentos, série diária de pelo menos 1–2 anos) calibrado com padrões plausíveis (sazonalidade, picos por surto, etc.) — deixar claro no código/docs que é sintético e por quê.
- Escrever scripts de ingestão dos dados externos públicos (clima, epidemiologia, feriados) e o merge com o dataset de consumo.
- Entregar o dataset final no schema combinado em `CONTRATOS.md` seção 1, salvo em `data/processed/`.
- Documentar em `src/data_ingestion/README.md` como rodar os scripts e de onde vem cada fonte.

**Entregável (Definition of Done):**
- [ ] `docs/arquitetura/CONTRATOS.md` seção 1 preenchida e revisada pelo time.
- [ ] Scripts em `src/data_ingestion/` rodáveis, gerando o dataset final.
- [ ] Dataset de exemplo pequeno (`data/processed/sample_*.csv`, poucas linhas) commitado para as outras pessoas usarem como mock imediatamente, sem esperar o pipeline completo.
- [ ] README explicando fontes, premissas e limitações dos dados sintéticos.

**Depende de:** ninguém (é a primeira peça da cadeia — deve sair primeiro, mesmo que em versão simples/mock, para destravar as pessoas B, C, D).

---

## Pessoa B — Engenharia de Features

**Branch:** `feature/feature-engineering` · **Pasta:** `src/features/`

**Escopo:**
- A partir do schema definido em `CONTRATOS.md`, construir o pipeline de transformação: médias móveis, lags de consumo, variáveis de sazonalidade (dia da semana, mês, feriado), variáveis climáticas/epidemiológicas defasadas (ex.: casos de dengue da semana anterior), normalização se necessário.
- Tratar dados faltantes e outliers.
- Documentar cada feature criada (nome, janela, racional) em `CONTRATOS.md` seção 2.

**Entregável:**
- [ ] Função/pipeline em `src/features/` que recebe o dataset da Pessoa A e devolve o dataset com features prontas para o modelo.
- [ ] Lista de features documentada em `CONTRATOS.md` seção 2.
- [ ] Testes básicos em `tests/` garantindo que o pipeline não quebra com dados faltantes.

**Depende de:** schema da Pessoa A (mas pode começar imediatamente usando o `sample_*.csv` mock, sem esperar o pipeline completo dela).

---

## Pessoa C — Modelagem de Previsão de Demanda

**Branch:** `feature/modelagem-demanda` · **Pastas:** `src/models/`, `notebooks/exploracao/` (arquivos próprios)

**Escopo:**
- Explorar o dataset com features (notebook próprio, ex. `notebooks/exploracao/pessoa_c_baseline.ipynb`).
- Implementar um **baseline simples** (média móvel ou ponto de pedido fixo) — necessário para depois provar que o ML melhora algo.
- Implementar e comparar 1–2 modelos de previsão (ex.: Prophet e/ou scikit-learn — regressão/gradient boosting) prevendo `consumo_unidades` por `medicamento_id`, horizonte 7–14 dias.
- Expor uma função clara de treino/previsão em `src/models/` seguindo o contrato de saída da seção 3 de `CONTRATOS.md`.

**Entregável:**
- [ ] Baseline implementado e documentado.
- [ ] Pelo menos 1 modelo de ML treinado, com métricas de erro (MAE/MAPE) documentadas comparando com o baseline.
- [ ] Função de previsão em `src/models/` seguindo o contrato de saída (seção 3).
- [ ] Notebook de exploração documentado (decisões, gráficos, por que esse modelo).

**Depende de:** features da Pessoa B (mas pode começar com um mock do formato de features, definido no contrato, sem esperar o pipeline dela terminar).

---

## Pessoa D — Motor de Recomendação & Avaliação de Impacto

**Branch:** `feature/recomendacao-avaliacao` · **Pastas:** `src/recommendation/`, `src/evaluation/`

**Escopo:**
- Implementar a lógica de recomendação de compra a partir da fórmula em `CONTRATOS.md` seção 4 (demanda prevista + estoque de segurança − estoque disponível − pedidos confirmados), incluindo cálculo de estoque de segurança e classificação de risco de falta/vencimento.
- Gerar a justificativa textual da recomendação (ex.: "estoque cobre 4 dias; fornecedor demora 7 dias").
- Implementar as métricas de avaliação de impacto: comparar cenário com vs. sem o modelo (redução simulada de ruptura, de vencimento, economia estimada), usando o baseline da Pessoa C como referência de "método atual".
- Montar a tabela de cenários de impacto (conservador/provável/otimista) com base em premissas explícitas, para uso no pitch.

**Entregável:**
- [ ] Função de recomendação em `src/recommendation/` seguindo contrato da seção 4.
- [ ] Métricas de avaliação em `src/evaluation/` (precisão do modelo, redução de ruptura/vencimento simulada, economia estimada).
- [ ] Tabela de cenários de impacto documentada (ligar com `docs/negocio/CONTEXTO.md`).

**Depende de:** saída do modelo da Pessoa C (mock definido no contrato libera início em paralelo).

---

## Pessoa E — Dashboard & Documentação/Pitch

**Branch:** `feature/dashboard-pitch` · **Pastas:** `dashboard/`, `docs/pitch/`

**Escopo:**
- Construir o painel em Streamlit consumindo a saída de `recommendation` (contrato seção 5): visão por medicamento com previsão de demanda, recomendação de compra, risco de falta/vencimento, justificativa, alertas visuais (🔴/🟡).
- Pode começar o layout/wireframe com dados mockados (CSV de exemplo) sem esperar os outros módulos.
- Preparar o material de pitch: narrativa, cenários de impacto (puxando da Pessoa D), respostas preparadas para as perguntas da banca (já listadas em `CONTEXTO.md`), roteiro dos 5 minutos.
- Garantir que o dashboard "conta a história" do projeto de forma visual para a apresentação.

**Entregável:**
- [ ] Dashboard funcional em `dashboard/` rodando com `streamlit run`.
- [ ] Roteiro de pitch em `docs/pitch/`.
- [ ] Slides ou material visual de apoio (se necessário) em `docs/pitch/`.

**Depende de:** contrato de saída da recomendação (seção 5) — pode começar com mock imediatamente.

---

## Cronograma sugerido (ajustar à duração real do projeto)

| Fase | O que acontece |
|---|---|
| Semana 1 | Kickoff + contratos definidos. Pessoa A entrega dataset mock pequeno. Todos criam suas branches e começam a trabalhar contra os mocks. |
| Semana 2–3 | Desenvolvimento paralelo dentro de cada branch. PRs incrementais para `main` conforme partes ficam prontas (não esperar tudo pronto para abrir PR). Pessoa A substitui o mock pelo dataset completo assim que pronto — avisa o time. |
| Semana 4 | Integração fim-a-fim: rodar a cadeia completa (dados reais do pipeline → features → modelo → recomendação → dashboard). Resolver divergências de contrato que apareceram na prática. |
| Última semana | Ajustes finais, `evaluation` consolidando números para o pitch, ensaio da apresentação, `main` congelado no estado de demo. |

## Pontos de sincronização (reuniões curtas recomendadas)

- Fim da semana 1: todos confirmam que conseguem rodar seu módulo contra o mock.
- Meio do projeto: checkpoint de integração parcial (dados reais da Pessoa A já circulando).
- Antes da última semana: integração completa testada por todos, sem pendência bloqueante.

## Ownership e revisão de PR

Cada pessoa é dona da sua pasta, mas **PRs devem ser revisados por pelo menos 1 outra pessoa** antes do merge em `main` — não precisa ser da mesma área, é para manter todo mundo com visão do projeto inteiro e pegar problemas de integração cedo (ex.: quem revisa o PR da Pessoa C pode notar que o formato de saída não bate com o que a Pessoa D espera).
