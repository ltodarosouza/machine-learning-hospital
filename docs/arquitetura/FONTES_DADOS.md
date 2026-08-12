# Fontes de dados externas (Issue #2)

Região de referência do MVP: **João Pessoa – PB** (ver escopo completo em [CONTRATOS.md](CONTRATOS.md) seção 0). O hospital do projeto é fictício, mas os dados climáticos e epidemiológicos usados para calibrar e enriquecer o dataset sintético vêm de fontes públicas reais dessa cidade — isso é o que dá credibilidade ao MVP sem precisarmos de acesso a um sistema hospitalar real.

## 1. Clima — Open-Meteo (trocado de INMET na Issue #4)

- **O quê:** temperatura média diária e precipitação (chuva) diária.
- **Fonte usada de fato:** Open-Meteo Historical Weather API (https://open-meteo.com/en/docs/historical-weather-api), dados de reanálise ERA5, reais e públicos, sem necessidade de cadastro/chave.
- **Por que não INMET, como estava planejado aqui originalmente:** na implementação da Issue #4, o portal do INMET (`portal.inmet.gov.br` e `bdmep.inmet.gov.br`) não respondeu a chamadas automatizadas (timeout/conexão recusada) no ambiente usado, e mesmo quando acessível manualmente, o fluxo de download é um zip por ano com todas as estações do Brasil — não trivial de automatizar. A Open-Meteo entrega o mesmo tipo de dado, já filtrado por coordenada geográfica, via uma chamada HTTP simples, 100% reprodutível. Se alguém do time tiver acesso ao INMET funcionando e preferir usá-lo (dado "oficial" pode pesar melhor na banca), a troca fica isolada em `src/data_ingestion/ingestao_clima.py::buscar_clima_openmeteo` — o contrato de saída (`CONTRATOS.md` seção 1.2) não muda.
- **Formato de acesso:** chamada HTTP GET com latitude/longitude/intervalo de datas, retorna JSON.
- **Coordenadas usadas:** lat -7.115, lon -34.845 (João Pessoa), definidas em `src/utils/config.py`.
- **Limitações conhecidas:** é dado de reanálise (modelo climático global recalibrado com observações), não leitura direta de uma estação local — pequenas diferenças frente ao que uma estação específica de João Pessoa mediria são esperadas, mas dentro da margem aceitável para o MVP.

## 2. Epidemiologia — InfoDengue

- **O quê:** casos estimados/notificados de dengue (e possivelmente outras arboviroses) por semana epidemiológica.
- **Fonte:** InfoDengue (Fiocruz/UFMG) — https://info.dengue.mat.br, tem API pública (https://info.dengue.mat.br/api/) que retorna dados por município via geocódigo do IBGE.
- **Geocódigo IBGE de João Pessoa:** 2507507 — **confirmado** na Issue #5 (a resposta da API retorna `municipio_nome: "João Pessoa"` para esse código).
- **Formato de acesso:** API REST retornando JSON, filtrável por município e intervalo de datas/semanas epidemiológicas.
- **Conversão feita (Issue #5):** o dado vem por semana epidemiológica (`casos_est`, casos estimados na semana inteira). Convertido para diário dividindo por 7 e repetindo nos 7 dias da semana — ou seja, `casos_dengue_regiao` é uma média diária aproximada, não o total semanal. Ver racional completo em `src/data_ingestion/ingestao_epidemiologia.py`.
- **DATASUS/OpenDataSUS:** avaliado como fonte alternativa/complementar (internações, atendimentos gerais), mas tem acesso mais burocrático e granularidade menos amigável para o prazo do projeto. Decisão do kickoff: **não usar diretamente no MVP**, priorizar InfoDengue que é mais direto via API. Se sobrar tempo, pode ser revisitado.

## 3. Calendário de feriados

- **O quê:** feriados nacionais e, se possível, estaduais/municipais (Paraíba / João Pessoa).
- **Fonte:** biblioteca Python `holidays` (`holidays.Brazil(state='PB')`), que já cobre nacional + estadual sem precisar de scraping.
- **Formato de acesso:** biblioteca local, sem chamada de rede — mais simples e confiável das 3 fontes.
- **Nota:** `holidays` não cobre feriados municipais específicos (ex.: aniversário da cidade). Se o time achar que vale a pena, isso pode ser adicionado manualmente na Issue #6 como uma lista fixa curta.

## Resumo de decisão (Issue #1 + #2, kickoff 2026-08-12)

| Fonte | Uso no MVP | Prioridade |
|---|---|---|
| ~~INMET~~ → Open-Meteo (clima) | Sim (trocado na Issue #4, ver seção 1) | Alta |
| InfoDengue (epidemiologia) | Sim | Alta |
| `holidays` (feriados) | Sim | Alta |
| DATASUS/OpenDataSUS | Não no MVP (avaliar depois) | Baixa |
