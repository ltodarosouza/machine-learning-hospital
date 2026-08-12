# Fontes de dados externas (Issue #2)

Região de referência do MVP: **João Pessoa – PB** (ver escopo completo em [CONTRATOS.md](CONTRATOS.md) seção 0). O hospital do projeto é fictício, mas os dados climáticos e epidemiológicos usados para calibrar e enriquecer o dataset sintético vêm de fontes públicas reais dessa cidade — isso é o que dá credibilidade ao MVP sem precisarmos de acesso a um sistema hospitalar real.

## 1. Clima — INMET

- **O quê:** temperatura média diária e precipitação (chuva) diária.
- **Fonte:** Instituto Nacional de Meteorologia (INMET), portal de dados históricos: https://portal.inmet.gov.br/dadoshistoricos (download de CSV por estação e ano) ou API pública do INMET (https://apitempo.inmet.gov.br).
- **Formato de acesso:** CSV por estação/ano (mais simples e estável para o MVP) ou chamadas de API.
- **Pendente de confirmação por quem for implementar a Issue #4:** o código exato da estação meteorológica de João Pessoa (existe mais de uma estação na região — convencional e automática). Verificar no portal qual tem melhor cobertura para os 2 anos do período escolhido.
- **Limitações conhecidas:** estações automáticas podem ter falhas pontuais de leitura — a Issue #4 já prevê tratamento de dados faltantes (interpolação/preenchimento).

## 2. Epidemiologia — InfoDengue

- **O quê:** casos estimados/notificados de dengue (e possivelmente outras arboviroses) por semana epidemiológica.
- **Fonte:** InfoDengue (Fiocruz/UFMG) — https://info.dengue.mat.br, tem API pública (https://info.dengue.mat.br/api/) que retorna dados por município via geocódigo do IBGE.
- **Geocódigo IBGE de João Pessoa:** 2507507 (confirmar no momento da implementação — código sujeito a checagem, buscar em https://www.ibge.gov.br caso divirja).
- **Formato de acesso:** API REST retornando JSON, filtrável por município e intervalo de datas/semanas epidemiológicas.
- **Conversão necessária:** o dado vem por semana epidemiológica — a Issue #5 precisa converter para granularidade diária (repetir o valor da semana nos 7 dias, ou interpolar entre semanas — decisão de quem implementar, documentar a escolha).
- **DATASUS/OpenDataSUS:** avaliado como fonte alternativa/complementar (internações, atendimentos gerais), mas tem acesso mais burocrático e granularidade menos amigável para o prazo do projeto. Decisão do kickoff: **não usar diretamente no MVP**, priorizar InfoDengue que é mais direto via API. Se sobrar tempo, pode ser revisitado.

## 3. Calendário de feriados

- **O quê:** feriados nacionais e, se possível, estaduais/municipais (Paraíba / João Pessoa).
- **Fonte:** biblioteca Python `holidays` (`holidays.Brazil(state='PB')`), que já cobre nacional + estadual sem precisar de scraping.
- **Formato de acesso:** biblioteca local, sem chamada de rede — mais simples e confiável das 3 fontes.
- **Nota:** `holidays` não cobre feriados municipais específicos (ex.: aniversário da cidade). Se o time achar que vale a pena, isso pode ser adicionado manualmente na Issue #6 como uma lista fixa curta.

## Resumo de decisão (Issue #1 + #2, kickoff 2026-08-12)

| Fonte | Uso no MVP | Prioridade |
|---|---|---|
| INMET (clima) | Sim | Alta |
| InfoDengue (epidemiologia) | Sim | Alta |
| `holidays` (feriados) | Sim | Alta |
| DATASUS/OpenDataSUS | Não no MVP (avaliar depois) | Baixa |
