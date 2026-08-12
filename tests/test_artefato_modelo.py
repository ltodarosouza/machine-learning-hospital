"""Issue #52 — Regressão: o artefato treinado pelo comando documentado
(`python src/models/modelo_demanda.py`) precisa carregar num processo novo.

Antes da correção, `ModeloDemanda` era definida dentro de
`src/models/modelo_demanda.py`. Rodar esse arquivo como script faz o
Python tratá-lo como o módulo `__main__`, e a classe definida ali é
picklada com `__module__ == "__main__"`. Um processo novo (este teste,
por exemplo), que importa `src.models.modelo_demanda` normalmente, não
encontra `ModeloDemanda` em `__main__` e a carga falha com
`AttributeError`.

Este teste roda o comando exatamente como documentado, via subprocesso
(processo 1 = treina e salva, "contaminado" pelo contexto `__main__`),
e depois carrega e usa o artefato no processo do pytest (processo 2).
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MODELO_DEMANDA_SCRIPT = REPO_ROOT / "src" / "models" / "modelo_demanda.py"


@pytest.mark.slow
def test_artefato_do_comando_documentado_carrega_em_processo_novo() -> None:
    resultado = subprocess.run(
        [sys.executable, str(MODELO_DEMANDA_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert resultado.returncode == 0, (
        f"O comando documentado falhou.\nstdout:\n{resultado.stdout}\nstderr:\n{resultado.stderr}"
    )

    # Processo 2: este é o processo do pytest, que nunca executou
    # modelo_demanda.py como __main__ — só o importou normalmente.
    from src.models.modelo_demanda import (
        DADOS_MODELAGEM,
        HORIZONTE_PREVISAO_DIAS,
        avaliar_validacao_temporal,  # noqa: F401  (garante que o módulo carrega por completo)
        prever_demanda,
        validar_saida_modelo,
    )
    from src.models.artefato import CAMINHO_MODELO_PADRAO, carregar_modelo
    from src.features.pipeline import gerar_features
    import pandas as pd

    assert CAMINHO_MODELO_PADRAO.exists(), "O comando documentado deveria ter salvo o artefato no caminho padrão."

    modelo = carregar_modelo(CAMINHO_MODELO_PADRAO)  # é aqui que o AttributeError ocorria antes da correção

    bruto = pd.read_csv(DADOS_MODELAGEM)
    features = gerar_features(bruto)
    corte = pd.to_datetime(bruto["data"]).max() - pd.Timedelta(days=HORIZONTE_PREVISAO_DIAS)

    previsao = prever_demanda(modelo, features, corte)
    validar_saida_modelo(previsao, set(bruto["medicamento_id"].unique()))
