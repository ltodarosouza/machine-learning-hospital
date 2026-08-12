# Como contribuir

Somos 5 pessoas trabalhando no mesmo repositório, em máquinas diferentes. Este documento existe para que ninguém sobrescreva o trabalho de outra pessoa e para que o `main` fique sempre em estado demonstrável.

## Estratégia de branches

```
main                    → sempre estável, sempre roda, é o que se mostra na banca
 └─ feature/<escopo>     → uma branch por pessoa/tarefa, nunca commit direto no main
```

Não usamos uma branch `develop` intermediária: com 5 pessoas e módulos bem separados por pasta, `main` + `feature/*` + Pull Request é suficiente e mais simples. Se a integração ficar arriscada perto da entrega, podemos criar `integration` temporariamente — decidir em conjunto se for o caso.

### Branches por pessoa (fixas, ver [docs/TASKS.md](docs/TASKS.md) para o escopo de cada uma)

| Branch | Dono(a) | Pasta principal |
|---|---|---|
| `feature/data-ingestion` | Pessoa A | `src/data_ingestion/`, `data/` |
| `feature/feature-engineering` | Pessoa B | `src/features/` |
| `feature/modelagem-demanda` | Pessoa C | `src/models/` |
| `feature/recomendacao-avaliacao` | Pessoa D | `src/recommendation/`, `src/evaluation/` |
| `feature/dashboard-pitch` | Pessoa E | `dashboard/`, `docs/pitch/` |

Se uma tarefa gerar sub-branches (ex.: um experimento específico), nomeie como `feature/modelagem-demanda-prophet` etc., sempre partindo da branch da pessoa ou do `main`.

## Regra de ouro para evitar conflitos

**Cada pessoa só edita os arquivos dentro da pasta que é dona.** Isso é o que torna possível trabalhar em paralelo sem conflitos de merge. Se você precisa mudar algo fora da sua pasta:

1. Abra uma Issue ou avise no grupo antes.
2. Ou faça a mudança em uma branch separada e peça revisão específica do dono da pasta.

Arquivos compartilhados de leitura (não editar sem avisar o grupo):
- `docs/arquitetura/CONTRATOS.md` — mudanças aqui afetam todo mundo, sempre discutir antes.
- `README.md`, `.gitignore`, `requirements.txt` — mudanças pequenas ok, mas avise no grupo.

**Notebooks (`notebooks/exploracao/`):** cada pessoa cria seus próprios arquivos com prefixo do nome, ex. `pessoa_a_exploracao_clima.ipynb`. Nunca duas pessoas editando o mesmo notebook — notebooks geram conflitos de merge praticamente impossíveis de resolver (o `.ipynb` é JSON com metadata e outputs binários).

## Fluxo de trabalho

1. Atualize sua branch com o `main` antes de começar a trabalhar no dia:
   ```bash
   git checkout main
   git pull origin main
   git checkout feature/<sua-branch>
   git merge main
   ```
2. Trabalhe em commits pequenos e frequentes (não acumule uma semana de trabalho num commit só).
3. Dê push regularmente para a sua branch (pelo menos ao final de cada sessão de trabalho):
   ```bash
   git push origin feature/<sua-branch>
   ```
4. Quando uma parte da sua tarefa estiver pronta e testada, abra um **Pull Request** para `main`.
5. Pelo menos **1 outra pessoa da equipe revisa** antes do merge (não precisa ser especialista na área, é para pegar problemas óbvios e manter todo mundo ciente do que está mudando no projeto).
6. Depois do merge, delete a branch remota da tarefa concluída (mantenha a branch "guarda-chuva" da pessoa se ela for continuar trabalhando nela, ou crie uma nova branch para a próxima etapa).

## Convenção de commits

Formato: `tipo: descrição curta no imperativo`

Tipos: `feat` (funcionalidade nova), `fix` (correção), `data` (mudanças em dados/scripts de ingestão), `docs` (documentação), `test`, `refactor`, `chore` (config, dependências).

Exemplos:
```
feat: adiciona função de previsão de demanda com Prophet
data: adiciona script de ingestão de dados climáticos do INMET
docs: documenta contrato de saída do modelo em CONTRATOS.md
fix: corrige cálculo de estoque de segurança na recomendação
```

## Pull Requests

Use o template automático (`.github/PULL_REQUEST_TEMPLATE.md`). Todo PR deve descrever:
- O que foi feito e por quê.
- Como foi testado.
- Se muda algum contrato de interface (schema de dados, saída do modelo, etc.) — se sim, avisar explicitamente porque impacta outras pessoas.

PRs pequenos e frequentes são melhores que PRs gigantes no fim do prazo. Se sua tarefa é grande, quebre em PRs incrementais.

## Antes de codar em paralelo: contratos de interface

Como os 5 módulos vão se conectar em cadeia (dados → features → modelo → recomendação → dashboard), a equipe precisa combinar **antes** de começar a codar:
- Qual o schema dos dados processados (nomes de colunas, tipos, granularidade).
- Qual o formato de entrada/saída do modelo de previsão.
- Qual o formato de entrada/saída do motor de recomendação.
- Qual o contrato que o dashboard espera consumir.

Isso está documentado em [docs/arquitetura/CONTRATOS.md](docs/arquitetura/CONTRATOS.md) — preencher em conjunto na primeira reunião, antes de dividir para trabalhar sozinhos. Sem isso, cada módulo evolui isolado e a integração final quebra tudo.

## Ambiente

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Nunca commitar dados reais/sensíveis, credenciais ou arquivos `.env` — já cobertos pelo `.gitignore`.
