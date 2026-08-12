"""Testes da integração do dashboard com o pipeline de recomendação (#20)."""

import pandas as pd

from dashboard.app import COLUNAS_OBRIGATORIAS, gerar_dados_painel


def test_gerar_dados_painel_usa_pipeline_real_e_entrega_contrato_completo() -> None:
    """A tela recebe recomendação, riscos e cadastro sem depender de mock."""
    dias = pd.date_range("2025-01-01", periods=45, freq="D")
    consumo = pd.DataFrame(
        {
            "data": dias,
            "medicamento_id": "med_a",
            "consumo_unidades": [10.0 + (indice % 3) for indice in range(len(dias))],
            "estoque_disponivel": [20.0] * len(dias),
            "entradas_unidades": [0.0] * len(dias),
            "ocupacao_leitos_pct": [60.0] * len(dias),
            "atendimentos_ps": [100] * len(dias),
            "temperatura_media": [27.0] * len(dias),
            "chuva_mm": [2.0] * len(dias),
            "casos_dengue_regiao": [5.0] * len(dias),
            "feriado": [False] * len(dias),
        }
    )
    medicamentos = pd.DataFrame(
        {
            "medicamento_id": ["med_a"],
            "nome": ["Medicamento A"],
            "categoria": ["Teste"],
            "prazo_entrega_dias": [7],
        }
    )

    dados = gerar_dados_painel(
        consumo, medicamentos, pd.DataFrame(), pd.DataFrame(), n_estimators=5
    )

    assert set(COLUNAS_OBRIGATORIAS).issubset(dados.columns)
    assert dados.loc[0, "nome"] == "Medicamento A"
    assert dados.loc[0, "categoria"] == "Teste"
    assert dados[list(COLUNAS_OBRIGATORIAS)].notna().all().all()
    assert dados.loc[0, "risco_falta"] in {"baixo", "médio", "alto"}
    assert dados.loc[0, "risco_vencimento"] in {"baixo", "médio", "alto"}
