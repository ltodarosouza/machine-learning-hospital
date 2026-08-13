"""Gera o relatório operacional oficial sem números inseridos manualmente."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.data_ingestion.gerar_dataset_sintetico import gerar_lotes_no_corte
from src.evaluation.comparar_modelos import (
    DADOS_MODELAGEM,
    HIPERPARAMETROS_XGBOOST,
    N_ESTIMATORS_PADRAO,
    _commit_atual,
    _hash_arquivo,
    _versoes_dependencias,
    avaliar_baseline_periodo,
    avaliar_modelo_periodo,
)
from src.evaluation.protocolo_validacao_operacional import (
    ConfiguracaoProtocolo,
    avaliar_aprovacao,
    avaliar_candidato_na_janela,
    gerar_janelas_backtest,
    salvar_relatorio_validacao,
)

DADOS_ESTOQUE = RAIZ / "data" / "processed" / "consumo_diario.csv"
DADOS_REFERENCIA = RAIZ / "data" / "processed" / "medicamentos_ref.csv"
DESTINO = RAIZ / "docs" / "avaliacao" / "resultado_exemplo"
QUANTIDADE_JANELAS_OFICIAL = 4


def gerar_validacao_operacional(destino: Path = DESTINO) -> dict[str, Path]:
    """Executa baseline e modelo atual nas mesmas quatro janelas recentes."""
    configuracao = ConfiguracaoProtocolo()
    dados = pd.read_csv(DADOS_MODELAGEM)
    estoque = pd.read_csv(DADOS_ESTOQUE)
    referencia = pd.read_csv(DADOS_REFERENCIA)
    estoque["data"] = pd.to_datetime(estoque["data"])
    janelas = (
        gerar_janelas_backtest(
            dados["data"],
            horizonte_dias=configuracao.horizonte_dias,
            treino_minimo_dias=configuracao.treino_minimo_dias,
            minimo_janelas=configuracao.minimo_janelas,
        )
        .tail(QUANTIDADE_JANELAS_OFICIAL)
        .reset_index(drop=True)
    )
    janelas["janela_id"] = [
        f"janela_{indice + 1:03d}" for indice in range(len(janelas))
    ]

    metricas: list[pd.DataFrame] = []
    for janela in janelas.itertuples(index=False):
        inicio = janela.inicio_avaliacao
        fim = janela.fim_avaliacao
        corte = pd.Timestamp(inicio) - pd.Timedelta(days=1)
        estoque_inicial = (
            estoque[estoque["data"] <= corte]
            .sort_values("data")
            .groupby("medicamento_id")
            .tail(1)
        )
        lotes = gerar_lotes_no_corte(estoque, corte)
        comparacoes = {
            "baseline": avaliar_baseline_periodo(dados, inicio, fim),
            "modelo_atual": avaliar_modelo_periodo(
                dados, inicio, fim, n_estimators=N_ESTIMATORS_PADRAO
            ),
        }
        for candidato, comparacao in comparacoes.items():
            previsoes = comparacao[
                ["medicamento_id", "data_previsao", "demanda_prevista"]
            ].copy()
            consumo_real = comparacao[
                ["medicamento_id", "data_previsao", "consumo_unidades"]
            ].rename(columns={"data_previsao": "data"})
            metricas.append(
                avaliar_candidato_na_janela(
                    previsoes,
                    consumo_real,
                    referencia,
                    estoque_inicial,
                    janela.janela_id,
                    candidato,
                    lotes=lotes,
                )
            )

    tabela_metricas = pd.concat(metricas, ignore_index=True)
    baseline = tabela_metricas[tabela_metricas["candidato"] == "baseline"]
    candidato = tabela_metricas[tabela_metricas["candidato"] == "modelo_atual"]
    decisao = avaliar_aprovacao(
        baseline,
        candidato,
        reducao_minima_custo=configuracao.reducao_minima_custo,
        fracao_minima_janelas_com_meta=configuracao.fracao_minima_janelas_com_meta,
        aumento_relevante_maximo=configuracao.aumento_relevante_maximo,
        minimo_janelas=configuracao.minimo_janelas,
        tolerancia_empate=configuracao.tolerancia_empate,
    )
    metadados = {
        "commit": _commit_atual(),
        "worktree_sujo": _worktree_sujo(),
        "hash_consumo_medicamentos": _hash_arquivo(DADOS_MODELAGEM),
        "hash_consumo_diario": _hash_arquivo(DADOS_ESTOQUE),
        "hash_medicamentos_ref": _hash_arquivo(DADOS_REFERENCIA),
        "versoes": json.dumps(_versoes_dependencias(), sort_keys=True),
        "hiperparametros_modelo": json.dumps(HIPERPARAMETROS_XGBOOST, sort_keys=True),
        "n_estimators": N_ESTIMATORS_PADRAO,
        "hash_codigo_protocolo": _hash_arquivo(
            RAIZ / "src" / "evaluation" / "protocolo_validacao_operacional.py"
        ),
        "hash_executor_protocolo": _hash_arquivo(Path(__file__)),
    }
    return salvar_relatorio_validacao(
        destino, metadados, configuracao, janelas, tabela_metricas, decisao
    )


def _worktree_sujo() -> bool:
    resultado = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(resultado.stdout.strip())


if __name__ == "__main__":
    for nome, caminho in gerar_validacao_operacional().items():
        print(f"{nome}: {caminho}")
