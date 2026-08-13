"""Protocolo de validação com janela de avaliação estendida (Issue #84).

A Issue #78 descobriu por que a decisão do protocolo v1.0.0 (Issue #77)
tinha pouco poder de detecção para mudanças de previsão: a janela de
avaliação (7 dias) é menor que o prazo de entrega mínimo do MVP (5-12
dias), então quase nenhum pedido feito durante a janela chega a tempo de
afetar a própria janela avaliada — a ruptura observada acaba dominada pelo
estoque inicial (idêntico para qualquer candidato), não pela previsão.

Este módulo estende a *janela de avaliação* (quantos dias o `avaliar_aprovacao`
enxerga de uma vez, sem resetar o estoque) para 28 dias, mantendo o *passo de
retreino* do modelo em 7 dias — o contrato de horizonte do MVP
(`HORIZONTE_PREVISAO_DIAS`) não muda, só o comprimento da janela de decisão
do protocolo. Dentro de cada janela de 28 dias, o modelo é retreinado a cada
7 dias (`avaliar_baseline_periodo`/`avaliar_modelo_periodo`/
`avaliar_candidato_periodo`, todos de `comparar_modelos.py`/
`avaliacao_previsao_assimetrica.py`, sem alteração), mas o estoque e os
lotes só são reconstruídos uma vez no início da janela — o pedido de uma
semana tem chance real de chegar e afetar semanas seguintes da mesma janela.

Reaproveita `ConfiguracaoProtocolo`, `gerar_janelas_backtest`,
`calcular_metricas_janela` e `avaliar_aprovacao` do protocolo v1.0.0 **sem
nenhuma alteração** — só muda `horizonte_dias` (o tamanho da janela de
avaliação) e como as previsões/impacto são calculados dentro de cada
janela. Versão do protocolo usada aqui: `1.1.0-janela-longa`, documentada em
`docs/avaliacao/PROTOCOLO_VALIDACAO_OPERACIONAL.md`. Não reescreve nenhuma
decisão da versão 1.0.0.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.data_ingestion.gerar_dataset_sintetico import gerar_lotes_no_corte
from src.evaluation.avaliacao_previsao_assimetrica import avaliar_candidato_periodo
from src.evaluation.comparar_modelos import (
    DADOS_MODELAGEM,
    N_ESTIMATORS_PADRAO,
    _commit_atual,
    _hash_arquivo,
    _versoes_dependencias,
    avaliar_baseline_periodo,
    avaliar_modelo_periodo,
)
from src.evaluation.impacto_simulado import simular_impacto
from src.evaluation.protocolo_validacao_operacional import (
    ConfiguracaoProtocolo,
    avaliar_aprovacao,
    calcular_metricas_janela,
    gerar_janelas_backtest,
    salvar_relatorio_validacao,
)
from src.models.modelo_demanda import HIPERPARAMETROS_XGBOOST
from src.utils.config import HORIZONTE_PREVISAO_DIAS

RAIZ = Path(__file__).resolve().parents[2]
DADOS_ESTOQUE = RAIZ / "data" / "processed" / "consumo_diario.csv"
DADOS_REFERENCIA = RAIZ / "data" / "processed" / "medicamentos_ref.csv"
DESTINO = RAIZ / "docs" / "avaliacao" / "revalidacao_janela_longa"

VERSAO_PROTOCOLO = "1.1.0-janela-longa"
DIAS_JANELA_AVALIACAO = 28  # 4x o passo de retreino — dá tempo do prazo de entrega (5-12 dias) atuar.
PASSO_RETREINO_DIAS = HORIZONTE_PREVISAO_DIAS  # contrato do MVP não muda: modelo continua previsto a 7 dias.
QUANTIDADE_JANELAS = 4
NOME_CANDIDATO_PADRAO = "quantile_080"
QUANTILE_ALPHA_PADRAO = 0.8


def configuracao_janela_longa(**overrides: Any) -> ConfiguracaoProtocolo:
    """`ConfiguracaoProtocolo` v1.1.0-janela-longa: mesmos limites de aprovação, janela maior.

    Reaproveita a mesma dataclass do protocolo v1.0.0 (Issue #77) — só o
    campo `versao` e `horizonte_dias` mudam por padrão. Os limites de
    aprovação (redução mínima, consistência, aumento relevante máximo)
    continuam os mesmos, de propósito: esta issue muda a janela, não o
    critério de aprovação.
    """
    parametros: dict[str, Any] = {
        "versao": VERSAO_PROTOCOLO,
        "horizonte_dias": DIAS_JANELA_AVALIACAO,
        "treino_minimo_dias": 365,
        "minimo_janelas": QUANTIDADE_JANELAS,
    }
    parametros.update(overrides)
    return ConfiguracaoProtocolo(**parametros)


def gerar_janelas_longas(dados: pd.DataFrame, configuracao: ConfiguracaoProtocolo) -> pd.DataFrame:
    """Últimas `configuracao.minimo_janelas` janelas de `configuracao.horizonte_dias` dias.

    Mesma função `gerar_janelas_backtest` do protocolo v1.0.0, sem alteração
    — só passa `horizonte_dias` maior. Renumera `janela_id` para começar do
    princípio no recorte escolhido, como já faz `avaliacao_previsao_assimetrica.gerar_janelas_oficiais`.
    """
    janelas = (
        gerar_janelas_backtest(
            dados["data"],
            horizonte_dias=configuracao.horizonte_dias,
            treino_minimo_dias=configuracao.treino_minimo_dias,
            minimo_janelas=configuracao.minimo_janelas,
        )
        .tail(configuracao.minimo_janelas)
        .reset_index(drop=True)
    )
    janelas["janela_id"] = [f"janela_{indice + 1:03d}" for indice in range(len(janelas))]
    return janelas


def _previsao_metodo(
    dados: pd.DataFrame,
    inicio: str,
    fim: str,
    metodo: str,
    quantile_alpha: float | None,
    n_estimators: int,
) -> pd.DataFrame:
    if metodo == "baseline":
        previsao = avaliar_baseline_periodo(dados, inicio, fim, horizonte=PASSO_RETREINO_DIAS)
    elif metodo == "modelo_atual":
        previsao = avaliar_modelo_periodo(dados, inicio, fim, horizonte=PASSO_RETREINO_DIAS, n_estimators=n_estimators)
    else:
        if quantile_alpha is None:
            raise ValueError(f"quantile_alpha é obrigatório para o método '{metodo}'.")
        previsao = avaliar_candidato_periodo(
            dados, inicio, fim, quantile_alpha, horizonte=PASSO_RETREINO_DIAS, n_estimators=n_estimators
        )
    return previsao[["medicamento_id", "data_previsao", "demanda_prevista", "consumo_unidades"]]


def avaliar_candidato_na_janela_longa(
    dados: pd.DataFrame,
    estoque: pd.DataFrame,
    referencia: pd.DataFrame,
    janela: Any,
    metodo: str,
    quantile_alpha: float | None = None,
    n_estimators: int = N_ESTIMATORS_PADRAO,
) -> pd.DataFrame:
    """Métricas de uma janela longa para um método — retreina a cada 7 dias, sem resetar estoque.

    Ao contrário de `avaliacao_previsao_assimetrica.coletar_resultados`
    (janelas oficiais do protocolo v1.0.0, que reconstroem o estoque a cada
    7 dias), aqui `estoque_inicial`/`lotes` são calculados **uma única vez**
    no início da janela de `configuracao.horizonte_dias` dias — a previsão é
    retreinada a cada 7 dias (`PASSO_RETREINO_DIAS`, contrato do MVP
    inalterado) mas o impacto é simulado numa passada só sobre a janela
    inteira, dando tempo real do pedido chegar.
    """
    inicio, fim = janela.inicio_avaliacao, janela.fim_avaliacao
    previsao = _previsao_metodo(dados, inicio, fim, metodo, quantile_alpha, n_estimators)

    corte = pd.Timestamp(inicio) - pd.Timedelta(days=1)
    estoque_inicial = estoque[estoque["data"] <= corte].sort_values("data").groupby("medicamento_id").tail(1)
    lotes = gerar_lotes_no_corte(estoque, corte)

    previsoes_candidato = previsao[["medicamento_id", "data_previsao", "demanda_prevista"]]
    consumo_real = previsao[["medicamento_id", "data_previsao", "consumo_unidades"]].rename(
        columns={"data_previsao": "data"}
    )
    impacto = simular_impacto(previsoes_candidato, consumo_real, referencia, estoque_inicial, lotes=lotes)

    comparacao = previsao[["medicamento_id", "demanda_prevista", "consumo_unidades"]]
    return calcular_metricas_janela(comparacao, impacto, janela.janela_id, metodo)


def coletar_metricas(
    dados: pd.DataFrame,
    estoque: pd.DataFrame,
    referencia: pd.DataFrame,
    janelas: pd.DataFrame,
    nome_candidato: str = NOME_CANDIDATO_PADRAO,
    quantile_alpha: float = QUANTILE_ALPHA_PADRAO,
    n_estimators: int = N_ESTIMATORS_PADRAO,
) -> pd.DataFrame:
    """Métricas de todas as janelas longas, para baseline, modelo atual e o candidato."""
    metodos = ["baseline", "modelo_atual", nome_candidato]
    linhas = []
    for janela in janelas.itertuples(index=False):
        for metodo in metodos:
            alpha = quantile_alpha if metodo == nome_candidato else None
            linhas.append(
                avaliar_candidato_na_janela_longa(dados, estoque, referencia, janela, metodo, alpha, n_estimators)
            )
    return pd.concat(linhas, ignore_index=True)


def _metadados(nome_candidato: str, n_estimators: int, papel_referencia: str) -> dict[str, Any]:
    return {
        "commit": _commit_atual(),
        "hash_consumo_medicamentos": _hash_arquivo(DADOS_MODELAGEM),
        "hash_consumo_diario": _hash_arquivo(DADOS_ESTOQUE),
        "hash_medicamentos_ref": _hash_arquivo(DADOS_REFERENCIA),
        "versoes": json.dumps(_versoes_dependencias(), sort_keys=True),
        "hiperparametros_modelo": json.dumps(HIPERPARAMETROS_XGBOOST, sort_keys=True),
        "n_estimators": n_estimators,
        "candidato_avaliado": nome_candidato,
        "papel_de_baseline_nesta_decisao": papel_referencia,
        "dias_janela_avaliacao": DIAS_JANELA_AVALIACAO,
        "passo_retreino_dias": PASSO_RETREINO_DIAS,
    }


def revalidar(
    dados: pd.DataFrame,
    estoque: pd.DataFrame,
    referencia: pd.DataFrame,
    destino: Path = DESTINO,
    nome_candidato: str = NOME_CANDIDATO_PADRAO,
    quantile_alpha: float = QUANTILE_ALPHA_PADRAO,
    n_estimators: int = N_ESTIMATORS_PADRAO,
    configuracao: ConfiguracaoProtocolo | None = None,
) -> dict[str, dict[str, Path]]:
    """Revalida `nome_candidato` sob o protocolo de janela longa — duas decisões auditáveis.

    Gera dois relatórios completos (janelas.csv/metricas.csv/configuracao.json/
    decisao.json/RELATORIO_VALIDACAO_OPERACIONAL.md, via `salvar_relatorio_validacao`,
    sem alteração), porque o protocolo v1.0.0 exige exatamente dois candidatos
    por decisão (`baseline` + um candidato):

    - `vs_baseline/`: candidato contra a média móvel — vocabulário literal
      do protocolo.
    - `vs_modelo_atual/`: candidato contra o modelo atual (XGBoost
      simétrico), com as métricas do modelo atual ocupando o papel de
      "baseline" que o protocolo exige — é a pergunta operacional real desta
      issue (substituiria o que está em produção?), documentada em
      `papel_de_baseline_nesta_decisao` nos metadados para não confundir com
      o baseline literal do protocolo.
    """
    configuracao = configuracao_janela_longa() if configuracao is None else configuracao
    janelas = gerar_janelas_longas(dados, configuracao)
    metricas = coletar_metricas(dados, estoque, referencia, janelas, nome_candidato, quantile_alpha, n_estimators)

    limites = dict(
        reducao_minima_custo=configuracao.reducao_minima_custo,
        fracao_minima_janelas_com_meta=configuracao.fracao_minima_janelas_com_meta,
        aumento_relevante_maximo=configuracao.aumento_relevante_maximo,
        minimo_janelas=configuracao.minimo_janelas,
        tolerancia_empate=configuracao.tolerancia_empate,
    )
    metricas_baseline = metricas[metricas["candidato"] == "baseline"]
    metricas_modelo_atual = metricas[metricas["candidato"] == "modelo_atual"].copy()
    metricas_candidato = metricas[metricas["candidato"] == nome_candidato]

    resultados: dict[str, dict[str, Path]] = {}

    decisao_vs_baseline = avaliar_aprovacao(metricas_baseline, metricas_candidato, **limites)
    resultados["vs_baseline"] = salvar_relatorio_validacao(
        destino / "vs_baseline",
        _metadados(nome_candidato, n_estimators, papel_referencia="baseline (média móvel, literal do protocolo)"),
        configuracao,
        janelas,
        pd.concat([metricas_baseline, metricas_candidato], ignore_index=True),
        decisao_vs_baseline,
    )

    metricas_modelo_atual_como_baseline = metricas_modelo_atual.assign(candidato="baseline")
    decisao_vs_modelo_atual = avaliar_aprovacao(
        metricas_modelo_atual_como_baseline, metricas_candidato, **limites
    )
    resultados["vs_modelo_atual"] = salvar_relatorio_validacao(
        destino / "vs_modelo_atual",
        _metadados(nome_candidato, n_estimators, papel_referencia="modelo atual (XGBoost simétrico em produção)"),
        configuracao,
        janelas,
        pd.concat([metricas_modelo_atual_como_baseline, metricas_candidato], ignore_index=True),
        decisao_vs_modelo_atual,
    )

    return resultados


def main() -> None:
    dados = pd.read_csv(DADOS_MODELAGEM)
    estoque = pd.read_csv(DADOS_ESTOQUE)
    estoque["data"] = pd.to_datetime(estoque["data"])
    referencia = pd.read_csv(DADOS_REFERENCIA)

    resultados = revalidar(dados, estoque, referencia)

    for decisao_nome, caminhos in resultados.items():
        decisao = json.loads(caminhos["decisao"].read_text(encoding="utf-8"))
        print(f"{decisao_nome}: status={decisao['status']}, aprovado={decisao['aprovado']}")
        print(f"  relatorio: {caminhos['relatorio']}")


if __name__ == "__main__":
    main()
