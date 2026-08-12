"""Issue #4 — Ingestão de dados climáticos (temperatura e chuva).

Fonte: Open-Meteo Historical Weather API (https://open-meteo.com/en/docs/historical-weather-api),
que serve dados de reanálise ERA5 (real, público, sem necessidade de
cadastro/chave de API).

Por que Open-Meteo e não o INMET, como estava planejado em
docs/arquitetura/FONTES_DADOS.md?
    O portal do INMET (portal.inmet.gov.br e bdmep.inmet.gov.br) não
    respondeu a chamadas automatizadas no ambiente em que esta task foi
    feita (timeout/conexão recusada) — e mesmo quando acessível, o
    fluxo de download é manual (zip por ano, todas as estações do
    Brasil, é preciso extrair a estação certa). A Open-Meteo entrega o
    mesmo tipo de dado (temperatura média diária, precipitação diária)
    já filtrado por coordenada geográfica, via uma chamada HTTP simples
    e 100% reprodutível — melhor para automação em equipe. Se o time
    preferir trocar para INMET depois, a função `buscar_clima_openmeteo`
    é o único lugar que precisa mudar; o contrato de saída (seção 1.2 de
    CONTRATOS.md) não muda.

Saída: data/external/clima.csv, com `data`, `temperatura_media` (°C) e
`chuva_mm`, cobrindo o período definido em src/utils/config.py.
"""

import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.config import PERIODO_INICIO, PERIODO_FIM, REGIAO_LATITUDE, REGIAO_LONGITUDE

SAIDA = Path(__file__).resolve().parents[2] / "data" / "external" / "clima.csv"

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"


def buscar_clima_openmeteo(
    inicio: str = PERIODO_INICIO,
    fim: str = PERIODO_FIM,
    lat: float = REGIAO_LATITUDE,
    lon: float = REGIAO_LONGITUDE,
) -> pd.DataFrame:
    """Busca temperatura média e precipitação diárias na API da Open-Meteo."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": inicio,
        "end_date": fim,
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": "America/Sao_Paulo",
    }
    resposta = requests.get(OPEN_METEO_URL, params=params, timeout=60)
    resposta.raise_for_status()
    dados = resposta.json()["daily"]

    df = pd.DataFrame(
        {
            "data": dados["time"],
            "temperatura_media": dados["temperature_2m_mean"],
            "chuva_mm": dados["precipitation_sum"],
        }
    )
    return df


def validar_clima(df: pd.DataFrame, inicio: str, fim: str) -> None:
    """Confere que não há dias faltando/duplicados e que os valores são plausíveis."""
    esperado = pd.date_range(start=inicio, end=fim, freq="D")
    datas_geradas = pd.to_datetime(df["data"])

    faltando = set(esperado) - set(datas_geradas)
    if faltando:
        raise ValueError(f"{len(faltando)} dia(s) faltando no clima gerado: {sorted(faltando)[:5]}...")

    if len(df) != len(esperado):
        raise ValueError(f"Esperado {len(esperado)} linhas, obtido {len(df)}.")

    if df["temperatura_media"].isna().any() or df["chuva_mm"].isna().any():
        raise ValueError("Há valores nulos em temperatura_media ou chuva_mm — API retornou dado incompleto.")

    # João Pessoa é uma cidade litorânea tropical: faixa de temperatura plausível é
    # bem estreita (raramente sai de ~18°C a ~34°C). Fora disso, é sinal de erro na
    # chamada (coordenada errada, unidade errada, etc.), não uma variação real.
    if not df["temperatura_media"].between(15, 36).all():
        raise ValueError("Temperatura fora da faixa plausível para João Pessoa (15–36°C) — revisar coordenadas/API.")

    if (df["chuva_mm"] < 0).any():
        raise ValueError("Valores negativos de chuva encontrados — revisar dado de origem.")


def main() -> None:
    df = buscar_clima_openmeteo()
    validar_clima(df, PERIODO_INICIO, PERIODO_FIM)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA, index=False, encoding="utf-8")

    print(f"Clima gerado: {len(df)} dias ({PERIODO_INICIO} a {PERIODO_FIM}).")
    print(f"Temperatura média do período: {df['temperatura_media'].mean():.1f}°C")
    print(f"Chuva total do período: {df['chuva_mm'].sum():.0f}mm")
    print(f"Arquivo salvo em: {SAIDA}")


if __name__ == "__main__":
    main()
