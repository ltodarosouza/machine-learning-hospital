# Machine Learning Hospital

Plataforma de inteligência para gestão de estoque de medicamentos em hospitais: previsão de demanda + recomendação de compra, para reduzir simultaneamente **falta** e **vencimento** de medicamentos.

> "Remédio falta onde precisa e vence onde sobra."

## Tese do projeto

Hospitais tomam decisões de estoque olhando principalmente para o passado, enquanto a demanda acontece no futuro. Esta plataforma usa dados internos (consumo, estoque, internações) e externos (clima, sazonalidade, epidemiologia) para prever a demanda futura de cada medicamento e recomendar quanto e quando comprar — mantendo o farmacêutico/gestor no controle da decisão final.

Contexto completo do problema, mercado e cenários de impacto: [docs/negocio/CONTEXTO.md](docs/negocio/CONTEXTO.md).

## Estrutura do repositório

```
machine-learning-hospital/
├── data/                     # Dados (não versionados no git, ver .gitignore)
│   ├── raw/                  # Dados brutos (originais, nunca editados)
│   ├── external/             # Dados externos (clima, epidemiologia, feriados)
│   └── processed/            # Dados tratados/prontos para features e modelo
├── notebooks/
│   └── exploracao/           # Notebooks de exploração (1 arquivo por pessoa/tópico)
├── src/
│   ├── data_ingestion/       # Coleta e carga de dados (internos e externos)
│   ├── features/             # Engenharia de features / pipeline de transformação
│   ├── models/                # Modelos de previsão de demanda
│   ├── recommendation/       # Motor de recomendação de compra (regras + saída do modelo)
│   ├── evaluation/           # Métricas de precisão, economia, redução de ruptura/vencimento
│   └── utils/                 # Utilitários compartilhados
├── dashboard/                # App Streamlit (painel do gestor)
│   ├── pages/
│   └── components/
├── docs/
│   ├── negocio/               # Contexto do problema, cenários de impacto, mercado
│   └── arquitetura/           # Contratos de interface entre módulos, schema de dados
├── tests/                     # Testes automatizados
└── scripts/                   # Scripts utilitários (setup, geração de dados sintéticos, etc.)
```

## Como contribuir

O trabalho é dividido em **tasks (Issues do GitHub)**, não por pessoa fixa — cada pessoa escolhe uma task disponível, entre as que já têm os pré-requisitos prontos. Ver a [aba Issues](../../issues) para a lista completa, com escopo, pré-requisitos e critério de pronto de cada uma.

Antes de pegar sua primeira task, leia:
1. [CONTRIBUTING.md](CONTRIBUTING.md) — fluxo de git, branches, commits, PRs, e como escolher/travar uma task.
2. [docs/arquitetura/CONTRATOS.md](docs/arquitetura/CONTRATOS.md) — contratos de interface entre os módulos (schema de dados, entrada/saída do modelo, fórmula de recomendação). **Definido em conjunto na Issue #1, antes de qualquer outra task começar.**

## Stack

- Python 3.11+
- pandas, scikit-learn / Prophet (previsão de demanda)
- Streamlit (dashboard)
- pytest (testes)

## Estado atual do MVP

O MVP cobre o fluxo completo de dados até a recomendação:

- dataset sintético de um pronto-socorro fictício, com 20 medicamentos;
- dados históricos diários de 2022-01-01 a 2025-12-31;
- região de referência: João Pessoa, Paraíba;
- clima diário da Open-Meteo, epidemiologia semanal do InfoDengue convertida para diário e calendário de feriados;
- lags, médias móveis, calendário e variáveis externas como features;
- tratamento de valores ausentes, valores negativos e outliers;
- baseline por média móvel e modelo de demanda com XGBoost;
- previsão dos próximos sete dias;
- cálculo de estoque de segurança;
- recomendação de compra com riscos de falta e vencimento;
- dashboard Streamlit conectado ao pipeline real.

Os dados hospitalares são sintéticos e calibrados com padrões plausíveis. Os dados externos de clima e epidemiologia são públicos e referem-se a João Pessoa. O projeto não utiliza dados reais de pacientes ou de estoque de um hospital.

## Como executar

Crie o ambiente virtual e instale as dependências:

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
```

Para reproduzir o pipeline de dados, execute os scripts nesta ordem:

```bash
python src/data_ingestion/ingestao_calendario.py
python src/data_ingestion/ingestao_clima.py
python src/data_ingestion/ingestao_epidemiologia.py
python src/data_ingestion/gerar_dataset_sintetico.py
python src/data_ingestion/consolidar_dataset.py
```

Os scripts de clima e epidemiologia acessam APIs públicas. Os arquivos gerados ficam em `data/external/` e `data/processed/`.

Para executar e validar de uma vez o fluxo completo — coleta, dados sintéticos,
features, modelo, recomendação e contrato do dashboard —, use:

```bash
python scripts/rodar_pipeline_completo.py
```

Se as APIs públicas estiverem indisponíveis, `--sem-coleta-externa` reutiliza
os CSVs externos versionados e ainda regenera todo o dataset sintético. Para
iniciar a interface depois da validação, acrescente `--abrir-dashboard`.

Execute os testes automatizados com:

```bash
pytest tests/ -q
```

Para abrir o dashboard:

```bash
streamlit run dashboard/app.py
```

Esse comando pressupõe que o artefato já foi gerado pelo pipeline completo ou
por `python src/models/modelo_demanda.py`. Depois, acesse
`http://localhost:8501` no navegador.

Para retreinar o modelo oficial e gerar os relatórios de precisão e de impacto simulado numa única execução:

```bash
python scripts/relatorio_final.py                  # usa os dados já processados
python scripts/relatorio_final.py --regenerar-dados # reconstrói o dataset primeiro
python scripts/relatorio_final.py --abrir-dashboard # ao final, abre o Streamlit
```

Para rodar só a comparação entre baseline e modelo (sem retreinar nem gerar o relatório de impacto):

```bash
python src/evaluation/comparar_modelos.py
```

## Resultado da modelagem

Na avaliação atual (dataset com estados latentes de surto, causalidade de atendimentos, censura de demanda por ruptura e ruído autocorrelacionado por medicamento — Issues #58-#61 —, modelo retunado):

- baseline: MAE de 15,52 unidades/dia;
- XGBoost: MAE de 14,69 unidades/dia;
- redução do MAE: 5,3% frente ao baseline;
- o modelo venceu o baseline em 11 dos 20 medicamentos.

O relatório reproduzível completo está em [docs/arquitetura/RESULTADOS_MODELAGEM.md](docs/arquitetura/RESULTADOS_MODELAGEM.md).

**Achado importante:** apesar do MAE menor, a simulação de impacto operacional ([docs/arquitetura/RESULTADOS_IMPACTO_SIMULADO.md](docs/arquitetura/RESULTADOS_IMPACTO_SIMULADO.md)) mostra o modelo de ML gerando **mais** rupturas e custo de compra emergencial que o baseline no trimestre simulado. Hipótese e próximos passos documentados em [src/models/README.md](src/models/README.md) — reportado sem filtro, é um resultado real que ainda precisa de investigação antes de qualquer conclusão de que o modelo está pronto para uso.

## Estrutura efetiva atual

Além das pastas descritas acima, os scripts de experimentação e tuning ficam em `scripts/`, o modelo atual utiliza `XGBRegressor` e a interface está concentrada em `dashboard/app.py`.

## Limitações conhecidas

- o hospital, o consumo, o estoque, os lotes e os pedidos são sintéticos;
- DATASUS/OpenDataSUS ainda não está integrado ao MVP;
- o dashboard apresenta recomendações, mas não registra a aprovação ou a realização de uma compra;
- a avaliação de impacto é uma simulação sobre dados sintéticos, não um piloto hospitalar;
- a fonte climática é a Open-Meteo, com dados de reanálise, e não uma estação local específica.

## Observação para macOS

O XGBoost pode exigir o runtime OpenMP para carregar sua biblioteca nativa. Em instalações com Homebrew, use:

```bash
brew install libomp
```
