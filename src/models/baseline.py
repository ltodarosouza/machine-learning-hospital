"""Issue #11 — Baseline de previsão (sem machine learning).

Representa "como o hospital decide hoje": uma média móvel simples do
consumo recente, projetada como previsão flat para os próximos dias.
Não usa nenhuma variável externa (clima, dengue, feriado) nem histórico
além da janela recente — é intencionalmente simples, para servir de
ponto de comparação honesto contra o modelo de ML (Issue #12). Se o
modelo de ML não vencer isso, isso é informação real que deve ser
reportada (ver Issue #13), não escondida.

Saída segue o contrato de docs/arquitetura/CONTRATOS.md seção 3:
`medicamento_id`, `data_previsao`, `demanda_prevista`,
`intervalo_inferior`, `intervalo_superior`.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.config import HORIZONTE_PREVISAO_DIAS

DADOS_MODELAGEM = Path(__file__).resolve().parents[2] / "data" / "processed" / "consumo_medicamentos.csv"

JANELA_PADRAO_DIAS = 14
Z_INTERVALO = 1.0  # largura do intervalo em desvios-padrão (simples, não é um IC estatístico formal)

COLUNAS_SAIDA = ["medicamento_id", "data_previsao", "demanda_prevista", "intervalo_inferior", "intervalo_superior"]


def prever_baseline(
    historico: pd.DataFrame,
    data_corte: str,
    janela: int = JANELA_PADRAO_DIAS,
    horizonte: int = HORIZONTE_PREVISAO_DIAS,
) -> pd.DataFrame:
    """Prevê a demanda dos próximos `horizonte` dias como a média móvel dos últimos `janela` dias.

    `historico` precisa ter, no mínimo, as colunas `data` e `medicamento_id` e
    `consumo_unidades` (schema de data/processed/consumo_medicamentos.csv).
    A previsão usa só dado com `data <= data_corte` — nunca olha o "futuro".
    """
    data_corte_ts = pd.Timestamp(data_corte)
    hist = historico.copy()
    hist["data"] = pd.to_datetime(hist["data"])

    janela_dados = hist[(hist["data"] <= data_corte_ts) & (hist["data"] > data_corte_ts - pd.Timedelta(days=janela))]
    if janela_dados.empty:
        raise ValueError(f"Sem histórico suficiente antes de {data_corte} para calcular o baseline.")

    resumo = janela_dados.groupby("medicamento_id")["consumo_unidades"].agg(["mean", "std"]).reset_index()
    resumo["std"] = resumo["std"].fillna(0.0)  # medicamento com só 1 dia na janela: sem variância calculável

    datas_previsao = pd.date_range(start=data_corte_ts + pd.Timedelta(days=1), periods=horizonte, freq="D")

    linhas = []
    for _, item in resumo.iterrows():
        for data_prev in datas_previsao:
            linhas.append(
                {
                    "medicamento_id": item["medicamento_id"],
                    "data_previsao": data_prev.date().isoformat(),
                    "demanda_prevista": max(item["mean"], 0.0),
                    "intervalo_inferior": max(item["mean"] - Z_INTERVALO * item["std"], 0.0),
                    "intervalo_superior": item["mean"] + Z_INTERVALO * item["std"],
                }
            )

    return pd.DataFrame(linhas, columns=COLUNAS_SAIDA)


def gerar_previsoes_baseline_periodo(
    historico: pd.DataFrame,
    data_inicio_previsoes: str,
    data_fim_previsoes: str,
    janela: int = JANELA_PADRAO_DIAS,
    horizonte: int = HORIZONTE_PREVISAO_DIAS,
) -> pd.DataFrame:
    """Gera previsões em janelas sucessivas de `horizonte` dias, cobrindo um período de teste inteiro.

    Pensado para a Issue #13 (avaliação): permite comparar `demanda_prevista`
    contra `consumo_unidades` real em vários pontos do tempo, não só um.
    Os cortes de previsão avançam em passos de `horizonte` dias (janelas não
    sobrepostas) entre `data_inicio_previsoes` e `data_fim_previsoes`.
    """
    inicio = pd.Timestamp(data_inicio_previsoes)
    fim = pd.Timestamp(data_fim_previsoes)

    previsoes = []
    corte = inicio - pd.Timedelta(days=1)
    while corte + pd.Timedelta(days=1) <= fim:
        previsao = prever_baseline(historico, data_corte=corte.date().isoformat(), janela=janela, horizonte=horizonte)
        previsoes.append(previsao)
        corte += pd.Timedelta(days=horizonte)

    return pd.concat(previsoes, ignore_index=True)


def validar_saida_baseline(previsao: pd.DataFrame, medicamentos_esperados: set, horizonte: int = HORIZONTE_PREVISAO_DIAS) -> None:
    if list(previsao.columns) != COLUNAS_SAIDA:
        raise ValueError(f"Colunas da previsão não batem com o contrato: {list(previsao.columns)}")

    if set(previsao["medicamento_id"].unique()) != medicamentos_esperados:
        raise ValueError("medicamento_id da previsão não bate com o esperado.")

    contagem_por_medicamento = previsao.groupby("medicamento_id").size()
    if not (contagem_por_medicamento == horizonte).all():
        raise ValueError(f"Cada medicamento deveria ter {horizonte} linhas de previsão (uma por dia do horizonte).")

    if previsao["demanda_prevista"].isna().any():
        raise ValueError("demanda_prevista com valores nulos.")
    if (previsao["demanda_prevista"] < 0).any():
        raise ValueError("demanda_prevista negativa.")
    if (previsao["intervalo_inferior"] > previsao["demanda_prevista"]).any():
        raise ValueError("intervalo_inferior maior que demanda_prevista em alguma linha.")
    if (previsao["intervalo_superior"] < previsao["demanda_prevista"]).any():
        raise ValueError("intervalo_superior menor que demanda_prevista em alguma linha.")


def main() -> None:
    historico = pd.read_csv(DADOS_MODELAGEM)
    medicamentos = set(historico["medicamento_id"].unique())

    ultima_data = pd.Timestamp(historico["data"].max())
    data_corte_demo = (ultima_data - pd.Timedelta(days=HORIZONTE_PREVISAO_DIAS)).date().isoformat()

    previsao_demo = prever_baseline(historico, data_corte=data_corte_demo)
    validar_saida_baseline(previsao_demo, medicamentos)

    print(f"Baseline de demonstração: previsão a partir do corte {data_corte_demo}, horizonte {HORIZONTE_PREVISAO_DIAS} dias.")
    print(f"{len(previsao_demo)} linhas geradas ({len(medicamentos)} medicamentos x {HORIZONTE_PREVISAO_DIAS} dias). Validação passou.")
    print(previsao_demo.head(HORIZONTE_PREVISAO_DIAS).to_string(index=False))


if __name__ == "__main__":
    main()
