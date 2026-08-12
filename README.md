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
