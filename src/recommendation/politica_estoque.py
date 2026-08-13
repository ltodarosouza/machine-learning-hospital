"""Políticas reutilizáveis de estoque de segurança da Issue #79.

Os grupos não são configurações manuais por medicamento: o perfil de demanda
vem da categoria que parametriza o gerador sintético e a faixa de prazo vem do
cadastro de fornecedores. Em dados reais, esta classificação deverá ser
substituída por uma regra validada sobre histórico operacional real.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real

import numpy as np
import pandas as pd


PERFIS_VALIDOS = {"continuo", "intermitente", "erratico"}
FAIXAS_PRAZO_VALIDAS = {"curto", "longo"}
LIMIAR_PRAZO_LONGO_DIAS = 7


def classificar_perfil_demanda(categoria: str) -> str:
    """Classifica o perfil sintético por categoria, sem regra por medicamento."""
    if categoria in {"Dor/febre", "Suporte/hidratação"}:
        return "continuo"
    if categoria == "Emergência/controlado":
        return "erratico"
    return "intermitente"


def classificar_faixa_prazo(prazo_entrega_dias: Real) -> str:
    """Agrupa lead times do MVP em curto (5–6) e longo (7–12 dias)."""
    if isinstance(prazo_entrega_dias, (bool, np.bool_)) or not isinstance(prazo_entrega_dias, Real):
        raise TypeError("prazo_entrega_dias deve ser numérico.")
    if not np.isfinite(float(prazo_entrega_dias)) or prazo_entrega_dias <= 0:
        raise ValueError("prazo_entrega_dias deve ser positivo e finito.")
    return "longo" if prazo_entrega_dias >= LIMIAR_PRAZO_LONGO_DIAS else "curto"


@dataclass(frozen=True)
class PoliticaEstoque:
    """Buffers por perfil × faixa de prazo, compartilhados pelos grupos."""

    nome: str
    fatores_por_grupo: Mapping[tuple[str, str], float]

    def __post_init__(self) -> None:
        esperado = {(perfil, faixa) for perfil in PERFIS_VALIDOS for faixa in FAIXAS_PRAZO_VALIDAS}
        if set(self.fatores_por_grupo) != esperado:
            raise ValueError("A política deve definir todos os grupos perfil × prazo.")
        for grupo, fator in self.fatores_por_grupo.items():
            if isinstance(fator, (bool, np.bool_)) or not isinstance(fator, Real):
                raise TypeError(f"Fator do grupo {grupo} deve ser numérico.")
            if not np.isfinite(float(fator)) or fator < 0:
                raise ValueError(f"Fator do grupo {grupo} deve ser finito e não negativo.")

    def fatores_por_medicamento(self, medicamentos_ref: pd.DataFrame) -> pd.DataFrame:
        obrigatorias = {"medicamento_id", "categoria", "prazo_entrega_dias"}
        faltantes = obrigatorias.difference(medicamentos_ref.columns)
        if faltantes:
            raise ValueError(f"medicamentos_ref sem colunas obrigatórias: {sorted(faltantes)}")
        resultado = medicamentos_ref[["medicamento_id", "categoria", "prazo_entrega_dias"]].copy()
        resultado["perfil_demanda"] = resultado["categoria"].map(classificar_perfil_demanda)
        resultado["faixa_prazo"] = resultado["prazo_entrega_dias"].map(classificar_faixa_prazo)
        resultado["fator_seguranca"] = [
            float(self.fatores_por_grupo[(perfil, faixa)])
            for perfil, faixa in zip(resultado["perfil_demanda"], resultado["faixa_prazo"], strict=True)
        ]
        return resultado[["medicamento_id", "perfil_demanda", "faixa_prazo", "fator_seguranca"]]


POLITICA_ATUAL = PoliticaEstoque(
    nome="fixa_020",
    fatores_por_grupo={(perfil, faixa): 0.20 for perfil in PERFIS_VALIDOS for faixa in FAIXAS_PRAZO_VALIDAS},
)

POLITICA_PERFIL_PRAZO_MODERADA = PoliticaEstoque(
    nome="perfil_prazo_moderada",
    fatores_por_grupo={
        ("continuo", "curto"): 0.10,
        ("continuo", "longo"): 0.20,
        ("intermitente", "curto"): 0.20,
        ("intermitente", "longo"): 0.35,
        ("erratico", "curto"): 0.30,
        ("erratico", "longo"): 0.50,
    },
)

POLITICA_PERFIL_PRAZO_CONSERVADORA = PoliticaEstoque(
    nome="perfil_prazo_conservadora",
    fatores_por_grupo={
        ("continuo", "curto"): 0.20,
        ("continuo", "longo"): 0.30,
        ("intermitente", "curto"): 0.35,
        ("intermitente", "longo"): 0.50,
        ("erratico", "curto"): 0.50,
        ("erratico", "longo"): 0.70,
    },
)

POLITICAS_CANDIDATAS = (POLITICA_PERFIL_PRAZO_MODERADA, POLITICA_PERFIL_PRAZO_CONSERVADORA)
