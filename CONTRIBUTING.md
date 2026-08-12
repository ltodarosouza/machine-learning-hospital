# Como contribuir

Somos 5 pessoas trabalhando no mesmo repositório, em máquinas diferentes. Este documento existe para que ninguém sobrescreva o trabalho de outra pessoa e para que o `main` fique sempre em estado demonstrável.

## Como o trabalho é organizado: tasks, não pessoas fixas

O projeto está dividido em ~25 tasks na [aba Issues](../../issues), cada uma com escopo, pastas envolvidas, pré-requisitos e critério de pronto bem explícitos. **Não existe "a pessoa dos dados" ou "a pessoa do dashboard" fixa** — qualquer um pode pegar qualquer task, desde que os pré-requisitos dela já estejam prontos (cada Issue lista isso na seção "Pré-requisitos", com link para as Issues das quais depende).

Isso é o que substitui a divisão por área que tínhamos antes: mais granular, mais flexível, e deixa claro o que trava o quê.

### Como escolher uma task

1. Olhe a [aba Issues](../../issues) e veja quais estão **sem ninguém atribuído** e **com os pré-requisitos já fechados** (a Issue de pré-requisito precisa estar com PR mergeado no `main`).
2. Atribua a Issue a você mesmo (`Assignees`) e comente avisando que vai começar — evita duas pessoas pegando a mesma task sem saber.
3. Crie sua branch a partir do `main`, nomeada `feature/<número-da-issue>-<slug-curto>` (ex.: `feature/12-modelo-previsao-demanda` — o próprio corpo de cada Issue já sugere o nome).
4. As duas primeiras Issues (**#1** e **#2**) são de kickoff e devem ser feitas **pelo time todo junto**, antes de qualquer task individual começar — elas travam o schema de dados que todo o resto depende.

## Estratégia de branches

```
main                          → sempre estável, sempre roda, é o que se mostra na banca
 └─ feature/<issue>-<slug>     → uma branch por task/Issue, nunca commit direto no main
```

Não usamos uma branch `develop` intermediária: `main` + `feature/<issue>` + Pull Request é suficiente. Se a integração ficar arriscada perto da entrega, podemos criar `integration` temporariamente — decidir em conjunto se for o caso.

## Regra de ouro para evitar conflitos

**Cada task tem pastas específicas listadas na própria Issue — só mexa nelas.** Como as tasks já foram desenhadas para não se sobreporem em arquivos, trabalhar em branches separadas ao mesmo tempo não deve gerar conflito, desde que cada um fique dentro do escopo da sua Issue. Se você precisa mudar algo fora da sua task:

1. Comente na Issue relevante ou avise no grupo antes.
2. Ou faça a mudança em uma branch separada e peça revisão específica de quem estiver com aquela task.

Arquivos compartilhados (não editar sem avisar o grupo):
- `docs/arquitetura/CONTRATOS.md` — mudanças aqui afetam todo mundo, sempre discutir antes. Toda mudança feita depois do kickoff deve ser registrada na tabela de histórico no fim do arquivo.
- `README.md`, `.gitignore`, `requirements.txt` — mudanças pequenas ok, mas avise no grupo.

**Notebooks (`notebooks/exploracao/`):** cada pessoa cria seus próprios arquivos com prefixo do nome, ex. `joao_exploracao_modelo.ipynb`. Nunca duas pessoas editando o mesmo notebook — notebooks geram conflitos de merge praticamente impossíveis de resolver (o `.ipynb` é JSON com metadata e outputs binários).

## Fluxo de trabalho

1. Escolha uma Issue sem atribuição e com pré-requisitos prontos, atribua a si mesmo e comente.
2. Crie a branch a partir do `main` atualizado:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/<numero-da-issue>-<slug>
   ```
3. Trabalhe em commits pequenos e frequentes (não acumule dias de trabalho num commit só).
4. Dê push regularmente (pelo menos ao final de cada sessão de trabalho):
   ```bash
   git push -u origin feature/<numero-da-issue>-<slug>
   ```
5. Quando a task estiver pronta (critério de pronto da Issue cumprido), abra um **Pull Request** para `main` referenciando a Issue (`Closes #<numero>` na descrição do PR fecha a Issue automaticamente ao mergear).
6. Pelo menos **1 outra pessoa da equipe revisa** antes do merge (não precisa ser especialista na área — é para pegar problemas óbvios e manter todo mundo ciente do que está mudando).
7. Depois do merge, delete a branch. Isso pode destravar outras Issues que tinham esta como pré-requisito — avise no grupo/comente nas Issues dependentes que já podem começar.

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
