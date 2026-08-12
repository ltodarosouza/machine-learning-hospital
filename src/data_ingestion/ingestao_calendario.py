"""Issue #6 — Ingestão de calendário de feriados.

Gera uma linha por dia, para todo o período do projeto (ver
src/utils/config.py), com uma flag indicando se o dia é feriado
nacional ou estadual (Paraíba). Usa a biblioteca `holidays`, que não
depende de rede (mais estável que scraping/API para essa fonte).

Saída: data/external/calendario.csv, seguindo o contrato definido em
docs/arquitetura/CONTRATOS.md, seção 1.2 (colunas `data`, `feriado`).
Inclui também `nome_feriado` como coluna extra (não faz parte do
contrato mínimo, mas é útil para debug e para a justificativa textual
da recomendação mais adiante).
"""

from pathlib import Path

import holidays
import pandas as pd

import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.config import PERIODO_INICIO, PERIODO_FIM, REGIAO_UF

SAIDA = Path(__file__).resolve().parents[2] / "data" / "external" / "calendario.csv"


def gerar_calendario(inicio: str = PERIODO_INICIO, fim: str = PERIODO_FIM, uf: str = REGIAO_UF) -> pd.DataFrame:
    """Gera o dataframe diário de calendário/feriados para o período do projeto."""
    datas = pd.date_range(start=inicio, end=fim, freq="D")

    anos = sorted({d.year for d in datas})
    feriados_br = holidays.Brazil(years=anos, subdiv=uf)

    linhas = []
    for data in datas:
        data_ts = data.date()
        nome = feriados_br.get(data_ts)
        linhas.append(
            {
                "data": data_ts.isoformat(),
                "feriado": nome is not None,
                "nome_feriado": nome if nome is not None else "",
            }
        )

    df = pd.DataFrame(linhas)
    return df


def validar_calendario(df: pd.DataFrame, inicio: str, fim: str) -> None:
    """Confere que não há dias faltando nem duplicados no período esperado."""
    esperado = pd.date_range(start=inicio, end=fim, freq="D")
    datas_geradas = pd.to_datetime(df["data"])

    faltando = set(esperado) - set(datas_geradas)
    if faltando:
        raise ValueError(f"{len(faltando)} dia(s) faltando no calendário gerado: {sorted(faltando)[:5]}...")

    duplicadas = datas_geradas[datas_geradas.duplicated()]
    if not duplicadas.empty:
        raise ValueError(f"Datas duplicadas encontradas: {duplicadas.tolist()}")

    if len(df) != len(esperado):
        raise ValueError(f"Esperado {len(esperado)} linhas, gerado {len(df)}.")


def main() -> None:
    df = gerar_calendario()
    validar_calendario(df, PERIODO_INICIO, PERIODO_FIM)

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA, index=False, encoding="utf-8")

    total_feriados = int(df["feriado"].sum())
    print(f"Calendário gerado: {len(df)} dias ({PERIODO_INICIO} a {PERIODO_FIM}).")
    print(f"Total de feriados no período: {total_feriados}.")
    print(f"Arquivo salvo em: {SAIDA}")


if __name__ == "__main__":
    main()
