"""Integração entre features, artefato, recomendação e dashboard (#25)."""

from pathlib import Path

from scripts.rodar_pipeline_completo import executar_pipeline


def test_pipeline_processado_entrega_dashboard_completo(tmp_path: Path) -> None:
    """O artefato recarregado deve chegar ao contrato final da interface."""
    dados = executar_pipeline(
        atualizar_dados=False,
        n_estimators=5,
        caminho_modelo=tmp_path / "modelo.joblib",
    )

    assert len(dados) == 20
    assert dados["medicamento_id"].nunique() == 20
    assert dados["compra_recomendada"].ge(0).all()
    assert dados[["risco_falta", "risco_vencimento", "justificativa"]].notna().all().all()
