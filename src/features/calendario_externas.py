"""Issue #9 — Features de calendário e variáveis externas.

Recebe o dataset processado (schema de docs/arquitetura/CONTRATOS.md
seção 1 — ex.: data/processed/consumo_medicamentos.csv) e devolve o
mesmo dataframe com colunas de features adicionadas, todas prefixadas
com `feat_` (contrato seção 2). Não faz nenhum tratamento de dados
faltantes/outliers — isso é escopo da Issue #10, que junta esta
saída com a de `series_temporais.py` (Issue #8) num pipeline único.

Features geradas:
    - feat_dia_semana: dia da semana (0=segunda ... 6=domingo)
    - feat_fim_de_semana: sábado ou domingo (o PS tem mais procura
      nesses dias, conforme já calibrado na geração do dataset sintético)
    - feat_mes: mês (1-12), para sazonalidade anual
    - feat_feriado: cópia de `feriado` com o prefixo padrão de feature,
      para todo input do modelo ficar consistente (feat_*)
    - feat_casos_dengue_lag7: casos de dengue de 7 dias atrás. Dengue
      tem efeito na demanda com atraso (o paciente procura o hospital
      alguns dias depois do início dos sintomas, não no mesmo dia do
      "caso" registrado) — por isso defasado, diferente de
      temperatura/chuva, que assumimos com efeito mais imediato.
    - feat_temperatura_media_norm, feat_chuva_mm_norm,
      feat_casos_dengue_regiao_norm: variáveis externas normalizadas por
      z-score causal, com histórico anterior de cada medicamento.

Nota sobre `feat_casos_dengue_lag7` e o normalizador: como usam janela/
estatística sobre o passado, os primeiros dias de cada medicamento ficam com
`feat_casos_dengue_lag7` nulo (sem 7 dias anteriores disponíveis) — é
esperado, tratado na Issue #10, não aqui.
"""

import pandas as pd

PREFIXO_FEATURE = "feat_"

COLUNAS_CALENDARIO = ["feat_dia_semana", "feat_fim_de_semana", "feat_mes", "feat_feriado"]
COLUNAS_LAG_EXTERNAS = ["feat_casos_dengue_lag7"]
COLUNAS_NORMALIZADAS = ["feat_temperatura_media_norm", "feat_chuva_mm_norm", "feat_casos_dengue_regiao_norm"]

LAG_DENGUE_DIAS = 7


def gerar_features_calendario(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona as features de calendário (dia da semana, fim de semana, mês, feriado)."""
    resultado = df.copy()
    data = pd.to_datetime(resultado["data"])

    resultado["feat_dia_semana"] = data.dt.dayofweek
    resultado["feat_fim_de_semana"] = data.dt.dayofweek.isin([5, 6])
    resultado["feat_mes"] = data.dt.month
    resultado["feat_feriado"] = resultado["feriado"].astype(bool)

    return resultado


def gerar_features_externas_defasadas(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona o lag de casos de dengue, calculado por medicamento_id (cada um tem 1 linha/dia)."""
    resultado = df.copy()
    resultado = resultado.sort_values(["medicamento_id", "data"])

    resultado["feat_casos_dengue_lag7"] = resultado.groupby("medicamento_id")["casos_dengue_regiao"].shift(LAG_DENGUE_DIAS)

    return resultado


def gerar_features_normalizadas(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza externas sem olhar o futuro (z-score causal por medicamento).

    Para cada data, média e desvio-padrão usam exclusivamente as observações
    anteriores do medicamento. Sem variabilidade histórica suficiente, a
    feature recebe zero.
    """
    resultado = df.copy().sort_values(["medicamento_id", "data"]).copy()

    for coluna, nome_feature in [
        ("temperatura_media", "feat_temperatura_media_norm"),
        ("chuva_mm", "feat_chuva_mm_norm"),
        ("casos_dengue_regiao", "feat_casos_dengue_regiao_norm"),
    ]:
        historico = resultado.groupby("medicamento_id", sort=False)[coluna].shift(1)
        media_anterior = historico.groupby(resultado["medicamento_id"], sort=False).transform(
            lambda serie: serie.expanding().mean()
        )
        desvio_anterior = historico.groupby(resultado["medicamento_id"], sort=False).transform(
            lambda serie: serie.expanding().std(ddof=0)
        )
        resultado[nome_feature] = ((resultado[coluna] - media_anterior) / desvio_anterior).where(
            desvio_anterior.gt(0), 0.0
        )
    return resultado


def gerar_features_calendario_externas(df: pd.DataFrame) -> pd.DataFrame:
    """Pipeline desta Issue: calendário + lag de dengue + normalização das externas."""
    resultado = gerar_features_calendario(df)
    resultado = gerar_features_externas_defasadas(resultado)
    resultado = gerar_features_normalizadas(resultado)
    return resultado


def validar_features_calendario_externas(df_saida: pd.DataFrame, df_entrada: pd.DataFrame) -> None:
    """Confere que as colunas de entrada foram preservadas e as novas features existem com tipo esperado."""
    for coluna in df_entrada.columns:
        if coluna not in df_saida.columns:
            raise ValueError(f"Coluna de entrada perdida no pipeline de features: {coluna}")

    todas_features = COLUNAS_CALENDARIO + COLUNAS_LAG_EXTERNAS + COLUNAS_NORMALIZADAS
    for coluna in todas_features:
        if coluna not in df_saida.columns:
            raise ValueError(f"Feature esperada não encontrada: {coluna}")

    if len(df_saida) != len(df_entrada):
        raise ValueError(f"Número de linhas mudou: entrada {len(df_entrada)}, saída {len(df_saida)}.")

    if not df_saida["feat_dia_semana"].between(0, 6).all():
        raise ValueError("feat_dia_semana fora do intervalo 0-6.")
    if not df_saida["feat_mes"].between(1, 12).all():
        raise ValueError("feat_mes fora do intervalo 1-12.")

    # feat_casos_dengue_lag7 só deve ser nulo nos primeiros LAG_DENGUE_DIAS dias de cada medicamento
    nulos_por_medicamento = df_saida.groupby("medicamento_id")["feat_casos_dengue_lag7"].apply(lambda s: s.isna().sum())
    if not (nulos_por_medicamento == LAG_DENGUE_DIAS).all():
        raise ValueError("Quantidade de nulos em feat_casos_dengue_lag7 diferente do esperado (deveria ser exatamente o tamanho do lag, por medicamento).")


def main() -> None:
    from pathlib import Path

    caminho_dados = Path(__file__).resolve().parents[2] / "data" / "processed" / "consumo_medicamentos.csv"
    df = pd.read_csv(caminho_dados)

    saida = gerar_features_calendario_externas(df)
    validar_features_calendario_externas(saida, df)

    print(f"Features de calendário/externas geradas: {len(saida)} linhas, {saida.shape[1]} colunas (entrada tinha {df.shape[1]}).")
    print(f"Novas colunas: {[c for c in saida.columns if c not in df.columns]}")
    print(saida[["data", "medicamento_id"] + COLUNAS_CALENDARIO + COLUNAS_LAG_EXTERNAS + COLUNAS_NORMALIZADAS].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
