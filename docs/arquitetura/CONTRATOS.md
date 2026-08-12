# Contratos de interface entre módulos

**Preencher em conjunto na reunião de kickoff, antes de cada pessoa sair para trabalhar sozinha na sua branch.** Este é o documento mais importante para o trabalho em paralelo funcionar: cada pessoa vai codar contra o que está aqui, sem esperar o módulo anterior estar pronto. Quando algo aqui muda depois de combinado, quem muda **avisa o time antes de dar merge**, porque quebra o contrato para os módulos seguintes.

Cadeia de dependência: `data_ingestion → features → models → recommendation → dashboard`. `evaluation` consome `models` e `recommendation`.

Cada dono de módulo trabalha com um **mock/exemplo pequeno** do contrato de entrada enquanto o módulo anterior não está pronto (ex.: Pessoa C cria um CSV de exemplo com o formato combinado abaixo e desenvolve o modelo contra ele, sem esperar a Pessoa B terminar).

---

## 1. Schema de dados processados (saída de `data_ingestion`, entrada de `features`)

Dono: Pessoa A. A preencher (exemplo de estrutura mínima esperada):

| Coluna | Tipo | Descrição |
|---|---|---|
| `data` | date | Data da observação (granularidade diária) |
| `medicamento_id` | string | Identificador do medicamento |
| `consumo_unidades` | float | Unidades consumidas no dia (variável alvo) |
| `estoque_disponivel` | float | Estoque disponível na data |
| `temperatura_media` | float | Dado externo (clima) |
| `chuva_mm` | float | Dado externo (clima) |
| `casos_dengue_regiao` | float | Dado externo (epidemiologia) |
| `feriado` | bool | Dado externo (calendário) |
| `ocupacao_leitos_pct` | float | Dado interno |
| ... | ... | Completar conforme fontes definidas |

Formato de arquivo: `data/processed/consumo_medicamentos.csv` (ou parquet). **Definir e travar aqui antes de codar.**

## 2. Contrato de entrada/saída de `features`

- **Entrada:** schema da seção 1.
- **Saída:** dataframe com colunas originais + features derivadas (ex.: médias móveis, lags, variáveis sazonais). Nomear features com prefixo claro (ex.: `feat_media_movel_7d`). Documentar aqui a lista final de features geradas.

## 3. Contrato de entrada/saída de `models`

- **Entrada:** saída de `features`, filtrada por `medicamento_id`.
- **Saída esperada por `recommendation`:**

| Coluna | Tipo | Descrição |
|---|---|---|
| `medicamento_id` | string | |
| `data_previsao` | date | Data para a qual a previsão se refere |
| `demanda_prevista` | float | Unidades previstas |
| `intervalo_inferior` | float | Limite inferior do intervalo de confiança (opcional no MVP) |
| `intervalo_superior` | float | Limite superior (opcional no MVP) |

Horizonte de previsão do MVP: **7–14 dias**.

## 4. Contrato de entrada/saída de `recommendation`

- **Entrada:** saída de `models` + estoque atual + pedidos confirmados + prazo do fornecedor + validade dos lotes (de `data_ingestion`).
- **Fórmula base** (ver [docs/negocio/CONTEXTO.md](../negocio/CONTEXTO.md)):
  ```
  compra_recomendada = demanda_prevista + estoque_seguranca - estoque_disponivel - pedidos_confirmados
  ```
- **Saída esperada por `dashboard` e `evaluation`:**

| Coluna | Tipo | Descrição |
|---|---|---|
| `medicamento_id` | string | |
| `compra_recomendada` | float | Unidades recomendadas |
| `risco_falta` | enum(baixo/médio/alto) ou float | |
| `risco_vencimento` | enum(baixo/médio/alto) ou float | |
| `justificativa` | string | Texto explicando a recomendação |

## 5. Contrato de entrada de `dashboard`

- Consome diretamente a saída de `recommendation` (seção 4) + série histórica de `models` (seção 3) para gráficos.
- Definir aqui o(s) arquivo(s)/função(ões) que o dashboard chama para obter esses dados (ex.: `src/recommendation/gerar_recomendacoes() -> pd.DataFrame`).

## 6. Contrato de `evaluation`

- Consome saída de `models` (comparar `demanda_prevista` vs. `consumo_unidades` real) e saída de `recommendation` (simular economia/redução de ruptura vs. baseline).
- Definir aqui o baseline de comparação (ex.: média móvel simples ou ponto de pedido fixo) — combinar com Pessoa C e D.

---

## Histórico de mudanças no contrato

Registrar aqui sempre que um contrato mudar depois de combinado, com data e quem mudou, para rastreabilidade:

| Data | Quem | O que mudou | Módulos afetados |
|---|---|---|---|
| | | | |
