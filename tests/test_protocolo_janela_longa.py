"""Testes do protocolo de janela longa (Issue #84)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.evaluation.protocolo_janela_longa import (
    NOME_CANDIDATO_PADRAO,
    PASSO_RETREINO_DIAS,
    VERSAO_PROTOCOLO,
    configuracao_janela_longa,
    gerar_janelas_longas,
    revalidar,
)
from src.evaluation.protocolo_validacao_operacional import ConfiguracaoProtocolo

REPO = Path(__file__).resolve().parents[1]


def test_configuracao_janela_longa_usa_versao_propria_e_nao_altera_limites_de_aprovacao() -> None:
    padrao = ConfiguracaoProtocolo()
    janela_longa = configuracao_janela_longa()

    assert janela_longa.versao == VERSAO_PROTOCOLO
    assert janela_longa.versao != padrao.versao
    assert janela_longa.horizonte_dias > padrao.horizonte_dias
    # Critério de aprovação não muda -- só a janela, como documentado na issue.
    assert janela_longa.reducao_minima_custo == padrao.reducao_minima_custo
    assert janela_longa.fracao_minima_janelas_com_meta == padrao.fracao_minima_janelas_com_meta
    assert janela_longa.aumento_relevante_maximo == padrao.aumento_relevante_maximo


def test_configuracao_janela_longa_aceita_overrides() -> None:
    configuracao = configuracao_janela_longa(horizonte_dias=14, minimo_janelas=4)

    assert configuracao.horizonte_dias == 14
    assert configuracao.minimo_janelas == 4


def test_passo_retreino_nao_muda_o_contrato_de_horizonte_do_mvp() -> None:
    from src.utils.config import HORIZONTE_PREVISAO_DIAS

    assert PASSO_RETREINO_DIAS == HORIZONTE_PREVISAO_DIAS


def test_gerar_janelas_longas_usa_horizonte_da_configuracao() -> None:
    configuracao = configuracao_janela_longa(treino_minimo_dias=10, horizonte_dias=14, minimo_janelas=4)
    dados = pd.DataFrame({"data": pd.date_range("2024-01-01", periods=70, freq="D")})

    janelas = gerar_janelas_longas(dados, configuracao)

    assert len(janelas) == 4
    duracoes = (pd.to_datetime(janelas["fim_avaliacao"]) - pd.to_datetime(janelas["inicio_avaliacao"])).dt.days + 1
    assert (duracoes == 14).all()
    assert list(janelas["janela_id"]) == [f"janela_{i + 1:03d}" for i in range(4)]


@pytest.mark.slow
def test_revalidar_produz_as_duas_decisoes_com_status_valido(tmp_path) -> None:
    # `gerar_lotes_no_corte` (usado internamente) reconstrói lotes para o
    # catálogo oficial completo de 20 medicamentos, então este teste precisa
    # do dataset real, não de um dataset sintético menor — mantém
    # `n_estimators` mínimo e uma janela de treino curta para ficar rápido.
    dados = pd.read_csv(REPO / "data" / "processed" / "consumo_medicamentos.csv")
    estoque = pd.read_csv(REPO / "data" / "processed" / "consumo_diario.csv")
    estoque["data"] = pd.to_datetime(estoque["data"])
    referencia = pd.read_csv(REPO / "data" / "processed" / "medicamentos_ref.csv")

    configuracao = configuracao_janela_longa(treino_minimo_dias=40, horizonte_dias=10, minimo_janelas=4)

    resultados = revalidar(
        dados,
        estoque,
        referencia,
        destino=tmp_path,
        nome_candidato=NOME_CANDIDATO_PADRAO,
        quantile_alpha=0.8,
        n_estimators=5,
        configuracao=configuracao,
    )

    assert set(resultados) == {"vs_baseline", "vs_modelo_atual"}
    for caminhos in resultados.values():
        assert caminhos["decisao"].exists()
        assert caminhos["relatorio"].exists()
        import json

        decisao = json.loads(caminhos["decisao"].read_text(encoding="utf-8"))
        assert decisao["status"] in {"aprovado", "rejeitado", "dados_insuficientes"}
        assert decisao["candidato"] == NOME_CANDIDATO_PADRAO

    # vs_modelo_atual usa o modelo atual no papel de baseline -- documentado nos metadados.
    relatorio_vs_modelo_atual = resultados["vs_modelo_atual"]["relatorio"].read_text(encoding="utf-8")
    assert "modelo atual (XGBoost simétrico em produção)" in relatorio_vs_modelo_atual
