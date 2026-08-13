"""Comando único: retreina o modelo oficial e gera, numa só execução, os
dois relatórios que importam para decidir se o modelo está ajudando —
precisão (MAE/MAPE, baseline vs. XGBoost) e impacto operacional simulado
(ruptura, compras emergenciais, economia em R$). Opcionalmente abre o
dashboard ao final.

    python scripts/relatorio_final.py
    python scripts/relatorio_final.py --regenerar-dados
    python scripts/relatorio_final.py --abrir-dashboard

Existia antes um jeito de fazer isso: rodar `comparar_modelos.py` e
`impacto_simulado.py` na mão, em separado, sem garantia de que os dois
refletiam o mesmo código/dataset no momento em que alguém olhava os
relatórios (foi exatamente o que gerou o problema da Issue #54, e quase
gerou confusão de novo quando o time regenerou o dataset 4 vezes seguidas
sem re-treinar o modelo). Este script existe para isso não acontecer de
novo: um comando, os dois relatórios sempre do mesmo estado do repositório.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts.rodar_pipeline_completo import executar_pipeline
from src.evaluation import comparar_modelos
from src.evaluation.impacto_simulado import gerar_relatorio_trimestral, simular_periodo
from src.utils.config import PERIODO_FIM

CAMINHO_RELATORIO_IMPACTO = REPO / "docs" / "arquitetura" / "RESULTADOS_IMPACTO_SIMULADO.md"

ARQUIVO_CONSUMO_MEDICAMENTOS = REPO / "data" / "processed" / "consumo_medicamentos.csv"
ARQUIVO_CONSUMO_DIARIO = REPO / "data" / "processed" / "consumo_diario.csv"
ARQUIVO_MEDICAMENTOS_REF = REPO / "data" / "processed" / "medicamentos_ref.csv"


def _limites_dos_ultimos_meses(fim_periodo: str, n_meses: int = 3) -> dict[str, tuple[str, str]]:
    """Últimos `n_meses` meses fechados, terminando no fim do dataset (PERIODO_FIM).

    Não hardcoda "outubro a dezembro de 2025": deriva do período real do
    dataset, então continua correto se alguém estender `PERIODO_FIM` de novo
    (já aconteceu 2 vezes neste projeto).
    """
    fim = pd.Timestamp(fim_periodo)
    limites: dict[str, tuple[str, str]] = {}
    cursor_fim = fim
    for _ in range(n_meses):
        inicio_mes = cursor_fim.replace(day=1)
        limites[f"{inicio_mes.month:02d}"] = (inicio_mes.date().isoformat(), cursor_fim.date().isoformat())
        cursor_fim = inicio_mes - pd.Timedelta(days=1)
    return dict(sorted(limites.items()))


def gerar_relatorio_impacto() -> str:
    """Gera o relatório de impacto simulado (Issue #17) sobre os últimos 3 meses do dataset."""
    dados = pd.read_csv(ARQUIVO_CONSUMO_MEDICAMENTOS)
    estoque = pd.read_csv(ARQUIVO_CONSUMO_DIARIO)
    estoque["data"] = pd.to_datetime(estoque["data"])
    referencia = pd.read_csv(ARQUIVO_MEDICAMENTOS_REF)
    resultados_mensais = {
        mes: simular_periodo(dados, estoque, referencia, inicio, fim)
        for mes, (inicio, fim) in _limites_dos_ultimos_meses(PERIODO_FIM).items()
    }
    relatorio = gerar_relatorio_trimestral(resultados_mensais)
    CAMINHO_RELATORIO_IMPACTO.write_text(relatorio, encoding="utf-8")
    return relatorio


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retreina o modelo e gera os relatórios de precisão e impacto.")
    parser.add_argument(
        "--regenerar-dados",
        action="store_true",
        help="Regenera todo o dataset (coleta externa + sintético) antes de retreinar. Por padrão, reusa data/processed/ existente.",
    )
    parser.add_argument(
        "--abrir-dashboard",
        action="store_true",
        help="Ao final, inicia o servidor Streamlit com o modelo recém-treinado.",
    )
    return parser.parse_args()


def main() -> None:
    args = _argumentos()

    print("=" * 70)
    print("ETAPA 1/3 — Treinando o modelo oficial")
    print("=" * 70)
    executar_pipeline(
        coletar_externos=args.regenerar_dados,
        atualizar_dados=args.regenerar_dados,
    )

    print("\n" + "=" * 70)
    print("ETAPA 2/3 — Relatório de precisão (baseline vs. modelo de ML)")
    print("=" * 70)
    comparar_modelos.main()

    print("\n" + "=" * 70)
    print("ETAPA 3/3 — Relatório de impacto simulado (ruptura, compras emergenciais, economia)")
    print("=" * 70)
    relatorio_impacto = gerar_relatorio_impacto()
    print(relatorio_impacto)
    print(f"Relatório salvo em: {CAMINHO_RELATORIO_IMPACTO}")

    print("\n" + "=" * 70)
    print("CONCLUÍDO")
    print("=" * 70)
    print(f"- Precisão: {comparar_modelos.SAIDA_METRICAS.relative_to(REPO)}")
    print(f"- Impacto:  {CAMINHO_RELATORIO_IMPACTO.relative_to(REPO)}")

    if args.abrir_dashboard:
        print("\nAbrindo dashboard em http://localhost:8501 ...")
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(REPO / "dashboard" / "app.py")],
            cwd=REPO,
            check=True,
        )


if __name__ == "__main__":
    main()
