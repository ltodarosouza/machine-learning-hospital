"""Issue #7 — Consolidação do dataset processado final.

Une as saídas das Issues #3 (consumo sintético), #4 (clima), #5
(epidemiologia) e #6 (calendário) em dois arquivos, seguindo
docs/arquitetura/CONTRATOS.md seção 1:

    1. data/external/externos_diarios.csv (contrato 1.2)
       — clima + epidemiologia + calendário, unidos por `data`.

    2. data/processed/consumo_medicamentos.csv ("dataset de modelagem")
       — consumo_diario.csv (contrato 1.1) + externos_diarios.csv (1.2),
       unidos por `data`. É este arquivo que as Issues #8-#13
       (features e modelagem) devem consumir.

Também gera data/processed/sample_consumo_medicamentos.csv, uma
amostra pequena (commitada) para quem for mexer em features/modelo/
dashboard poder testar sem rodar o pipeline inteiro.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.config import PERIODO_INICIO, PERIODO_FIM

DIR_EXTERNAL = Path(__file__).resolve().parents[2] / "data" / "external"
DIR_PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"

SAIDA_EXTERNOS = DIR_EXTERNAL / "externos_diarios.csv"
SAIDA_CONSOLIDADO = DIR_PROCESSED / "consumo_medicamentos.csv"
SAIDA_AMOSTRA = DIR_PROCESSED / "sample_consumo_medicamentos.csv"

COLUNAS_CONTRATO_1_1 = ["data", "medicamento_id", "consumo_unidades", "estoque_disponivel", "entradas_unidades", "ocupacao_leitos_pct", "atendimentos_ps"]
COLUNAS_CONTRATO_1_2 = ["data", "temperatura_media", "chuva_mm", "casos_dengue_regiao", "feriado"]


def montar_externos_diarios() -> pd.DataFrame:
    clima = pd.read_csv(DIR_EXTERNAL / "clima.csv", parse_dates=["data"])
    epi = pd.read_csv(DIR_EXTERNAL / "epidemiologia.csv", parse_dates=["data"])
    cal = pd.read_csv(DIR_EXTERNAL / "calendario.csv", parse_dates=["data"])[["data", "feriado"]]

    externos = clima.merge(epi, on="data", how="inner").merge(cal, on="data", how="inner")
    externos = externos[["data", "temperatura_media", "chuva_mm", "casos_dengue_regiao", "feriado"]]
    externos["data"] = externos["data"].dt.date.astype(str)
    return externos


def montar_consumo_medicamentos(externos_diarios: pd.DataFrame) -> pd.DataFrame:
    consumo = pd.read_csv(DIR_PROCESSED / "consumo_diario.csv")
    consolidado = consumo.merge(externos_diarios, on="data", how="left")
    return consolidado[COLUNAS_CONTRATO_1_1 + COLUNAS_CONTRATO_1_2[1:]]


def validar(externos: pd.DataFrame, consolidado: pd.DataFrame) -> None:
    esperado_dias = pd.date_range(start=PERIODO_INICIO, end=PERIODO_FIM, freq="D")

    # externos_diarios: 1 linha por dia, sem furos nem duplicidade
    datas_externos = pd.to_datetime(externos["data"])
    if len(externos) != len(esperado_dias) or set(datas_externos) != set(esperado_dias):
        raise ValueError("externos_diarios.csv: dias faltando ou duplicados no período esperado.")
    if externos.isna().any().any():
        raise ValueError("externos_diarios.csv: valores nulos encontrados.")

    # consolidado: 1 linha por (data, medicamento_id), sem furos nem duplicidade, sem merge perdido
    if consolidado.duplicated(subset=["data", "medicamento_id"]).any():
        raise ValueError("consumo_medicamentos.csv: linhas duplicadas em (data, medicamento_id).")
    if consolidado[COLUNAS_CONTRATO_1_2[1:]].isna().any().any():
        raise ValueError("consumo_medicamentos.csv: merge com dados externos deixou nulos — checar cobertura de datas.")
    for coluna in COLUNAS_CONTRATO_1_1:
        if coluna not in consolidado.columns:
            raise ValueError(f"consumo_medicamentos.csv: coluna do contrato ausente: {coluna}")


def gerar_amostra(consolidado: pd.DataFrame, n_medicamentos: int = 3, n_dias: int = 30) -> pd.DataFrame:
    """Amostra pequena e commitável: poucos medicamentos, poucos dias, mas com todas as colunas do contrato."""
    medicamentos_amostra = sorted(consolidado["medicamento_id"].unique())[:n_medicamentos]
    dias_amostra = sorted(consolidado["data"].unique())[:n_dias]
    amostra = consolidado[
        consolidado["medicamento_id"].isin(medicamentos_amostra) & consolidado["data"].isin(dias_amostra)
    ]
    return amostra.sort_values(["medicamento_id", "data"])


def main() -> None:
    externos = montar_externos_diarios()
    consolidado = montar_consumo_medicamentos(externos)
    validar(externos, consolidado)
    amostra = gerar_amostra(consolidado)

    DIR_EXTERNAL.mkdir(parents=True, exist_ok=True)
    DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
    externos.to_csv(SAIDA_EXTERNOS, index=False, encoding="utf-8")
    consolidado.to_csv(SAIDA_CONSOLIDADO, index=False, encoding="utf-8")
    amostra.to_csv(SAIDA_AMOSTRA, index=False, encoding="utf-8")

    print(f"externos_diarios.csv: {len(externos)} linhas -> {SAIDA_EXTERNOS}")
    print(f"consumo_medicamentos.csv: {len(consolidado)} linhas -> {SAIDA_CONSOLIDADO}")
    print(f"sample_consumo_medicamentos.csv: {len(amostra)} linhas -> {SAIDA_AMOSTRA}")


if __name__ == "__main__":
    main()
