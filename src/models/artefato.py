"""Issue #52 — Artefato serializável do modelo de demanda.

Isolado em módulo próprio (nunca executado como script/``__main__``) de
propósito: quando ``python src/models/modelo_demanda.py`` é rodado
diretamente, o Python trata esse arquivo como o módulo ``__main__`` — e
qualquer classe definida *ali* é picklada com ``__module__ == "__main__"``.
Um processo novo, que importa `src.models.modelo_demanda` normalmente
(não como `__main__`), procura a classe em `__main__` e falha com
``AttributeError: module '__main__' has no attribute 'ModeloDemanda'``.

Isso já aconteceu neste projeto: `models_output/modelo_demanda.joblib`,
gerado pelo comando documentado, não carregava fora do processo que o
treinou (Issue #52).

A correção é estrutural, não uma regra a lembrar: qualquer classe que
precise ser serializada com `joblib`/`pickle` deve morar num módulo que
**nunca** é o ponto de entrada do programa. Este arquivo é só importado,
nunca `python src/models/artefato.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
from sklearn.pipeline import Pipeline

CAMINHO_MODELO_PADRAO = Path(__file__).resolve().parents[2] / "models_output" / "modelo_demanda.joblib"


@dataclass
class ModeloDemanda:
    """Artefato necessário para gerar previsões reproduzíveis."""

    pipeline: Pipeline
    colunas_preditivas: list[str]
    desvio_residual_por_medicamento: dict[str, float]


def salvar_modelo(modelo: ModeloDemanda, caminho: Path = CAMINHO_MODELO_PADRAO) -> None:
    """Persiste o artefato treinado; o diretório de saída não é versionado."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, caminho)


def carregar_modelo(caminho: Path = CAMINHO_MODELO_PADRAO) -> ModeloDemanda:
    """Carrega um artefato salvo por :func:`salvar_modelo`, em qualquer processo."""
    return joblib.load(caminho)
