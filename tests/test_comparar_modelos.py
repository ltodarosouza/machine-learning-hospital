"""Testes de reprodutibilidade e coerência do relatório de avaliação (Issue #75).

Existem porque uma versão anterior do projeto (PR #73) citou, em texto
escrito à mão, uma contagem de "medicamentos vencedores" que não batia com
a própria tabela do relatório gerado — e porque `n_jobs=-1` fazia o XGBoost
produzir resultados diferentes em máquinas com números de núcleos diferentes,
o que por sua vez mudava essa contagem entre execuções "iguais".
"""

import pandas as pd
import pytest

from src.evaluation.comparar_modelos import _hash_arquivo, contar_vencedores, gerar_relatorio_markdown
from src.models.modelo_demanda import HIPERPARAMETROS_XGBOOST


def _metricas(mae_por_medicamento: dict[str, tuple[float, float]]) -> pd.DataFrame:
    """mae_por_medicamento: {medicamento_id: (mae_baseline, mae_modelo)}."""
    linhas = []
    for medicamento, (mae_baseline, mae_modelo) in mae_por_medicamento.items():
        linhas.append({"metodo": "baseline", "medicamento_id": medicamento, "mae": mae_baseline, "mape": 10.0})
        linhas.append({"metodo": "modelo_ml", "medicamento_id": medicamento, "mae": mae_modelo, "mape": 10.0})

    agregado_baseline = sum(v[0] for v in mae_por_medicamento.values()) / len(mae_por_medicamento)
    agregado_modelo = sum(v[1] for v in mae_por_medicamento.values()) / len(mae_por_medicamento)
    linhas.append({"metodo": "baseline", "medicamento_id": "TODOS", "mae": agregado_baseline, "mape": 10.0})
    linhas.append({"metodo": "modelo_ml", "medicamento_id": "TODOS", "mae": agregado_modelo, "mape": 10.0})
    return pd.DataFrame(linhas)


def test_contar_vencedores_bate_com_a_tabela() -> None:
    metricas = _metricas(
        {
            "med_a": (10.0, 8.0),  # modelo vence
            "med_b": (5.0, 6.0),  # baseline vence
            "med_c": (7.0, 7.0),  # empate — não conta como vitória (comparação estrita)
        }
    )
    vencedores, total = contar_vencedores(metricas)
    assert vencedores == 1
    assert total == 3


def test_relatorio_cita_a_mesma_contagem_da_tabela_quando_modelo_vence() -> None:
    metricas = _metricas({"med_a": (10.0, 8.0), "med_b": (10.0, 9.0)})
    relatorio = gerar_relatorio_markdown(metricas, "2025-01-01", "2025-01-07")

    vencedores, total = contar_vencedores(metricas)
    assert vencedores == 2
    assert f"vencendo em {vencedores} de {total} medicamentos" in relatorio

    linhas_sim = [linha for linha in relatorio.splitlines() if linha.startswith("|") and linha.strip().endswith("| Sim |")]
    assert len(linhas_sim) == vencedores


def test_relatorio_cita_a_mesma_contagem_da_tabela_quando_modelo_perde() -> None:
    metricas = _metricas({"med_a": (5.0, 9.0), "med_b": (5.0, 8.0)})
    relatorio = gerar_relatorio_markdown(metricas, "2025-01-01", "2025-01-07")

    vencedores, total = contar_vencedores(metricas)
    assert vencedores == 0
    assert f"vencendo em apenas {vencedores} de {total} medicamentos" in relatorio
    assert "NÃO superou o baseline" in relatorio


def test_hiperparametros_usam_n_jobs_1_para_reprodutibilidade_entre_maquinas() -> None:
    """Regressão: `n_jobs=-1` faz o XGBoost variar por número de núcleos da
    máquina (verificado empiricamente: previsões chegaram a divergir ~60
    unidades entre `n_jobs=-1` e `n_jobs=1` no mesmo dado/seed) — foi a causa
    raiz da divergência de contagem de vencedores reportada na Issue #75."""
    assert HIPERPARAMETROS_XGBOOST["n_jobs"] == 1


def test_hash_arquivo_e_deterministico_e_sensivel_ao_conteudo(tmp_path) -> None:
    arquivo = tmp_path / "dado.csv"
    arquivo.write_text("a,b\n1,2\n", encoding="utf-8")

    hash_1 = _hash_arquivo(arquivo)
    hash_2 = _hash_arquivo(arquivo)
    assert hash_1 == hash_2
    assert len(hash_1) == 8

    arquivo.write_text("a,b\n1,3\n", encoding="utf-8")
    hash_3 = _hash_arquivo(arquivo)
    assert hash_3 != hash_1
