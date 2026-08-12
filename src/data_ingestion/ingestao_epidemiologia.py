"""Issue #5 — Ingestão de dados epidemiológicos (casos de dengue).

Fonte: API pública do InfoDengue (Fiocruz/UFMG) — https://info.dengue.mat.br/api/,
consultada por geocódigo IBGE do município (João Pessoa = 2507507, confirmado
nesta task: a resposta da API retorna `municipio_nome: "João Pessoa"`).

O InfoDengue entrega os dados por **semana epidemiológica** (SE), não por
dia. Para chegar na granularidade diária exigida pelo contrato
(CONTRATOS.md seção 1.2), cada valor semanal (`casos_est`, o número de
casos estimados na semana) é **dividido por 7** e repetido nos 7 dias
daquela semana — ou seja, `casos_dengue_regiao` representa uma média
diária aproximada da semana, não o total da semana. Essa escolha foi
feita porque o contrato descreve a coluna como "casos estimados no dia";
repetir o total da semana em cada um dos 7 dias infla a escala em 7x e
dificultaria comparar com variáveis realmente diárias (temperatura, chuva).
Se o time preferir manter o total semanal (ex.: para destacar picos com
mais força visual no dashboard), é só remover a divisão por 7 abaixo —
mudança de uma linha.

Saída: data/external/epidemiologia.csv, com `data` e `casos_dengue_regiao`,
cobrindo o período definido em src/utils/config.py.
"""

import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.config import PERIODO_INICIO, PERIODO_FIM, REGIAO_GEOCODIGO_IBGE

SAIDA = Path(__file__).resolve().parents[2] / "data" / "external" / "epidemiologia.csv"

INFODENGUE_URL = "https://info.dengue.mat.br/api/alertcity"


def buscar_dengue_infodengue(
    inicio: str = PERIODO_INICIO,
    fim: str = PERIODO_FIM,
    geocode: int = REGIAO_GEOCODIGO_IBGE,
) -> pd.DataFrame:
    """Busca casos semanais de dengue na API do InfoDengue e expande para granularidade diária."""
    ano_inicio = pd.Timestamp(inicio).year
    ano_fim = pd.Timestamp(fim).year

    params = {
        "geocode": geocode,
        "disease": "dengue",
        "format": "json",
        "ew_start": 1,
        "ew_end": 52,
        "ey_start": ano_inicio,
        "ey_end": ano_fim,
    }
    resposta = requests.get(INFODENGUE_URL, params=params, timeout=60)
    resposta.raise_for_status()
    registros = resposta.json()

    if not registros:
        raise ValueError("InfoDengue retornou 0 registros — checar geocódigo/parâmetros.")

    semanas = pd.DataFrame(registros)
    semanas["data_inicio_semana"] = pd.to_datetime(semanas["data_iniSE"], unit="ms")
    semanas["casos_media_diaria"] = semanas["casos_est"] / 7.0

    # Expande cada semana em 7 linhas diárias
    linhas_diarias = []
    for _, semana in semanas.iterrows():
        for offset in range(7):
            dia = semana["data_inicio_semana"] + pd.Timedelta(days=offset)
            linhas_diarias.append({"data": dia.date(), "casos_dengue_regiao": semana["casos_media_diaria"]})

    df_diario = pd.DataFrame(linhas_diarias).drop_duplicates(subset="data").sort_values("data")

    # Reindexa exatamente para o período do projeto, preenchendo bordas (se a
    # primeira/última semana epidemiológica não alinhar perfeitamente com
    # PERIODO_INICIO/PERIODO_FIM) com o valor diário mais próximo disponível.
    periodo_completo = pd.date_range(start=inicio, end=fim, freq="D")
    df_diario["data"] = pd.to_datetime(df_diario["data"])
    df_diario = df_diario.set_index("data").reindex(periodo_completo)
    df_diario["casos_dengue_regiao"] = df_diario["casos_dengue_regiao"].ffill().bfill()
    df_diario = df_diario.reset_index().rename(columns={"index": "data"})
    df_diario["data"] = df_diario["data"].dt.date.astype(str)

    return df_diario


def validar_epidemiologia(df: pd.DataFrame, inicio: str, fim: str) -> None:
    """Confere que não há dias faltando/duplicados nem valores nulos ou negativos."""
    esperado = pd.date_range(start=inicio, end=fim, freq="D")
    datas_geradas = pd.to_datetime(df["data"])

    faltando = set(esperado) - set(datas_geradas)
    if faltando:
        raise ValueError(f"{len(faltando)} dia(s) faltando no epidemiologia gerado: {sorted(faltando)[:5]}...")

    if len(df) != len(esperado):
        raise ValueError(f"Esperado {len(esperado)} linhas, obtido {len(df)}.")

    if df["casos_dengue_regiao"].isna().any():
        raise ValueError("Há valores nulos em casos_dengue_regiao.")

    if (df["casos_dengue_regiao"] < 0).any():
        raise ValueError("Valores negativos de casos_dengue_regiao encontrados.")


def main() -> None:
    df = buscar_dengue_infodengue()
    validar_epidemiologia(df, PERIODO_INICIO, PERIODO_FIM)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA, index=False, encoding="utf-8")

    print(f"Epidemiologia gerada: {len(df)} dias ({PERIODO_INICIO} a {PERIODO_FIM}).")
    print(f"Média diária de casos estimados no período: {df['casos_dengue_regiao'].mean():.1f}")
    print(f"Pico diário estimado: {df['casos_dengue_regiao'].max():.1f}")
    print(f"Arquivo salvo em: {SAIDA}")


if __name__ == "__main__":
    main()
