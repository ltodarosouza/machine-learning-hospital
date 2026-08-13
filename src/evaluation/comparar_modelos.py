"""Issue #13 — Comparação entre o baseline (Issue #11) e o modelo de ML (Issue #12).

Roda os dois métodos sobre o mesmo período de teste (dados que nenhum
dos dois viu — o modelo é sempre treinado só com `data <= corte`,
nunca com o futuro) e calcula MAE e MAPE, por medicamento e agregado.

Reporta os dois números mesmo quando o modelo de ML **não** vence o
baseline em algum medicamento — essa é uma decisão deliberada: uma
comparação que só mostra os casos favoráveis não serve para decidir
nada, e o objetivo aqui é ter um número honesto para citar depois.

O período de teste é dividido em janelas sucessivas de `horizonte`
dias (mesma lógica de `gerar_previsoes_baseline_periodo`, em
`baseline.py`). Para o modelo de ML, cada janela retreina o modelo do
zero usando só o histórico anterior a ela (`avaliar_validacao_temporal`,
de `modelo_demanda.py`) — mais lento que treinar uma vez só, mas é o
jeito correto de simular "o que o modelo saberia prever, a cada
momento, sem olhar o futuro".
"""

import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.models.baseline import JANELA_PADRAO_DIAS, gerar_previsoes_baseline_periodo
from src.models.modelo_demanda import avaliar_validacao_temporal
from src.utils.config import HORIZONTE_PREVISAO_DIAS, PERIODO_FIM, PERIODO_INICIO

DADOS_MODELAGEM = Path(__file__).resolve().parents[2] / "data" / "processed" / "consumo_medicamentos.csv"
SAIDA_METRICAS = Path(__file__).resolve().parents[2] / "docs" / "arquitetura" / "RESULTADOS_MODELAGEM.md"


def avaliar_baseline_periodo(dados_brutos: pd.DataFrame, data_inicio_teste: str, data_fim_teste: str, horizonte: int = HORIZONTE_PREVISAO_DIAS) -> pd.DataFrame:
    """Previsões do baseline no período de teste, já unidas ao consumo real."""
    previsao = gerar_previsoes_baseline_periodo(dados_brutos, data_inicio_teste, data_fim_teste, horizonte=horizonte)

    real = dados_brutos[["data", "medicamento_id", "consumo_unidades"]].copy()
    real["data_previsao"] = pd.to_datetime(real["data"]).dt.date.astype(str)

    comparacao = previsao.merge(real[["data_previsao", "medicamento_id", "consumo_unidades"]], on=["medicamento_id", "data_previsao"], how="inner")
    comparacao["metodo"] = "baseline"
    return comparacao


def avaliar_modelo_periodo(
    dados_brutos: pd.DataFrame,
    data_inicio_teste: str,
    data_fim_teste: str,
    horizonte: int = HORIZONTE_PREVISAO_DIAS,
    n_estimators: int = 500,
) -> pd.DataFrame:
    """Previsões do modelo de ML no período de teste — retreina a cada janela, sem olhar o futuro."""
    inicio = pd.Timestamp(data_inicio_teste)
    fim = pd.Timestamp(data_fim_teste)

    janelas = []
    corte = inicio - pd.Timedelta(days=1)
    while corte + pd.Timedelta(days=1) <= fim:
        comparacao_janela = avaliar_validacao_temporal(dados_brutos, data_corte=corte, horizonte=horizonte, n_estimators=n_estimators)
        janelas.append(comparacao_janela[["medicamento_id", "data_previsao", "demanda_prevista", "consumo_unidades"]])
        corte += pd.Timedelta(days=horizonte)

    resultado = pd.concat(janelas, ignore_index=True)
    resultado["metodo"] = "modelo_ml"
    return resultado


def calcular_metricas(comparacao: pd.DataFrame) -> pd.DataFrame:
    """MAE e MAPE por medicamento e método. MAPE ignora dias com consumo real 0 (divisão por zero)."""
    comparacao = comparacao.copy()
    comparacao["erro_absoluto"] = (comparacao["consumo_unidades"] - comparacao["demanda_prevista"]).abs()

    com_consumo_positivo = comparacao[comparacao["consumo_unidades"] > 0].copy()
    com_consumo_positivo["erro_percentual"] = (
        com_consumo_positivo["erro_absoluto"] / com_consumo_positivo["consumo_unidades"]
    ) * 100

    mae = comparacao.groupby(["metodo", "medicamento_id"])["erro_absoluto"].mean().rename("mae")
    mape = com_consumo_positivo.groupby(["metodo", "medicamento_id"])["erro_percentual"].mean().rename("mape")

    por_medicamento = pd.concat([mae, mape], axis=1).reset_index()

    agregado = (
        comparacao.groupby("metodo")["erro_absoluto"].mean().rename("mae").reset_index()
    )
    agregado_mape = com_consumo_positivo.groupby("metodo")["erro_percentual"].mean().rename("mape").reset_index()
    agregado = agregado.merge(agregado_mape, on="metodo")
    agregado["medicamento_id"] = "TODOS"

    return pd.concat([por_medicamento, agregado[["metodo", "medicamento_id", "mae", "mape"]]], ignore_index=True)


def _commit_atual() -> str:
    """SHA curto do commit em que o relatório foi gerado — para rastreabilidade (Issue #54)."""
    try:
        resultado = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2], check=True
        )
        return resultado.stdout.strip()
    except Exception:
        return "desconhecido (git indisponível no ambiente)"


def gerar_relatorio_markdown(metricas: pd.DataFrame, data_inicio_teste: str, data_fim_teste: str) -> str:
    agregado = metricas[metricas["medicamento_id"] == "TODOS"].set_index("metodo")
    mae_baseline = agregado.loc["baseline", "mae"]
    mae_modelo = agregado.loc["modelo_ml", "mae"]
    reducao_pct = (1 - mae_modelo / mae_baseline) * 100 if mae_baseline > 0 else float("nan")

    linhas = [
        "# Resultados da comparação baseline vs. modelo de ML (Issue #13)",
        "",
        f"Período de teste: {data_inicio_teste} a {data_fim_teste}. Nenhum dos dois métodos viu dado desse período durante o treino/cálculo — o baseline usa só a janela móvel anterior a cada corte, o modelo é retreinado do zero a cada janela usando só `data <= corte`.",
        "",
        f"Dataset de treino/teste: `data/processed/consumo_medicamentos.csv`, período {PERIODO_INICIO} a {PERIODO_FIM} (ver `src/utils/config.py`). **Este relatório é gerado do zero a cada execução de `comparar_modelos.py`** — os números não são comparáveis com versões anteriores deste arquivo se o dataset ou os hiperparâmetros do modelo mudaram entre execuções (ver histórico de melhorias em `src/models/README.md`).",
        "",
        "## Resultado agregado (todos os 20 medicamentos)",
        "",
        "| Método | MAE (unidades/dia) | MAPE (%) |",
        "|---|---|---|",
        f"| Baseline (média móvel) | {mae_baseline:.2f} | {agregado.loc['baseline', 'mape']:.1f}% |",
        f"| Modelo de ML | {mae_modelo:.2f} | {agregado.loc['modelo_ml', 'mape']:.1f}% |",
        "",
    ]

    if mae_modelo < mae_baseline:
        linhas.append(f"**O modelo de ML reduziu o erro (MAE) em {reducao_pct:.1f}% frente ao baseline.**")
    else:
        linhas.append(
            f"**Neste período de teste, o modelo de ML NÃO superou o baseline** (MAE {mae_modelo:.2f} vs. {mae_baseline:.2f}). "
            "Reportado sem ajuste — ver seção de detalhamento por medicamento abaixo antes de decidir qualquer próximo passo (ex.: mais dado de treino, outro horizonte, outro modelo)."
        )

    linhas += ["", "## Detalhamento por medicamento", ""]
    linhas.append("| Medicamento | MAE baseline | MAE modelo | MAPE baseline | MAPE modelo | Modelo venceu? |")
    linhas.append("|---|---|---|---|---|---|")

    detalhe = metricas[metricas["medicamento_id"] != "TODOS"]
    for medicamento_id in sorted(detalhe["medicamento_id"].unique()):
        linha_medicamento = detalhe[detalhe["medicamento_id"] == medicamento_id].set_index("metodo")
        mae_b = linha_medicamento.loc["baseline", "mae"]
        mae_m = linha_medicamento.loc["modelo_ml", "mae"]
        mape_b = linha_medicamento.loc["baseline", "mape"]
        mape_m = linha_medicamento.loc["modelo_ml", "mape"]
        venceu = "Sim" if mae_m < mae_b else "Não"
        linhas.append(f"| {medicamento_id} | {mae_b:.2f} | {mae_m:.2f} | {mape_b:.1f}% | {mape_m:.1f}% | {venceu} |")

    linhas += [
        "",
        "## Reprodutibilidade",
        "",
        f"- **Commit:** `{_commit_atual()}`",
        f"- **Período avaliado:** {data_inicio_teste} a {data_fim_teste} (dataset completo: {PERIODO_INICIO} a {PERIODO_FIM})",
        f"- **Baseline:** média móvel de {JANELA_PADRAO_DIAS} dias (`src/models/baseline.py::prever_baseline`)",
        "- **Modelo de ML:** XGBoost (`XGBRegressor`, `max_depth=7, learning_rate=0.1, n_estimators=500, subsample=0.8, colsample_bytree=0.8`, `random_state=42`) — ver `src/models/modelo_demanda.py::treinar_modelo`",
        "- **Comando para regenerar este relatório:** `python src/evaluation/comparar_modelos.py`",
    ]

    return "\n".join(linhas) + "\n"


def main() -> None:
    dados_brutos = pd.read_csv(DADOS_MODELAGEM)
    ultima_data = pd.to_datetime(dados_brutos["data"]).max()

    # 4 janelas de HORIZONTE_PREVISAO_DIAS dias (28 dias de teste no total) —
    # suficiente para uma leitura razoável sem deixar o retreino do modelo de
    # ML lento demais (ele é retreinado do zero a cada janela).
    data_fim_teste = ultima_data.date().isoformat()
    data_inicio_teste = (ultima_data - pd.Timedelta(days=4 * HORIZONTE_PREVISAO_DIAS - 1)).date().isoformat()

    print(f"Avaliando baseline vs. modelo de ML, período de teste {data_inicio_teste} a {data_fim_teste}...")

    comparacao_baseline = avaliar_baseline_periodo(dados_brutos, data_inicio_teste, data_fim_teste)
    print(f"Baseline: {len(comparacao_baseline)} previsões avaliadas.")

    comparacao_modelo = avaliar_modelo_periodo(dados_brutos, data_inicio_teste, data_fim_teste)
    print(f"Modelo de ML: {len(comparacao_modelo)} previsões avaliadas.")

    comparacao_completa = pd.concat(
        [
            comparacao_baseline[["metodo", "medicamento_id", "data_previsao", "demanda_prevista", "consumo_unidades"]],
            comparacao_modelo[["metodo", "medicamento_id", "data_previsao", "demanda_prevista", "consumo_unidades"]],
        ],
        ignore_index=True,
    )

    metricas = calcular_metricas(comparacao_completa)
    relatorio = gerar_relatorio_markdown(metricas, data_inicio_teste, data_fim_teste)

    SAIDA_METRICAS.write_text(relatorio, encoding="utf-8")
    print(f"\nRelatório salvo em: {SAIDA_METRICAS}\n")
    print(relatorio)


if __name__ == "__main__":
    main()
