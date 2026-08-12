"""Issue #3 — Geração do dataset sintético de consumo de medicamentos.

Não temos acesso a um sistema hospitalar real, então este script gera
uma série sintética, mas calibrada para ser plausível: reage às
variáveis externas reais já coletadas (clima, dengue, feriados — Issues
#4/#5/#6), tem sazonalidade semanal e por categoria de medicamento, e
inclui uma política de reposição de estoque "ingênua" (a forma como um
hospital decide hoje, sem modelo preditivo) que deliberadamente produz
alguns episódios de ruptura e alguns lotes com risco de vencimento —
sem isso, não haveria nada para o motor de recomendação (Issues #14–16)
melhorar depois.

Todos os números de base (consumo médio por medicamento, preço,
prazo de fornecedor) são **premissas do time**, não dados reais de
nenhum hospital — deixado explícito aqui e em CONTRATOS.md.

Gera as 4 tabelas definidas em docs/arquitetura/CONTRATOS.md seção 1
que cabem no escopo desta Issue (a união com dados externos, tabela
1.2, fica para a Issue #7):
    - data/processed/consumo_diario.csv       (contrato 1.1)
    - data/processed/medicamentos_ref.csv     (contrato 1.3)
    - data/processed/lotes.csv                (contrato 1.4)
    - data/processed/pedidos_pendentes.csv    (contrato 1.5)

Nota sobre local do arquivo: a Issue #3 originalmente sugeria salvar em
`data/raw/`, mas CONTRATOS.md (fechado depois, na Issue #1) define o
local definitivo como `data/processed/` para as tabelas 1.1/1.3/1.4/1.5
— este script segue o contrato, que é a fonte da verdade.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.utils.config import PERIODO_INICIO, PERIODO_FIM

SEED = 42

DIR_PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"
DIR_EXTERNAL = Path(__file__).resolve().parents[2] / "data" / "external"

SAIDA_CONSUMO = DIR_PROCESSED / "consumo_diario.csv"
SAIDA_MEDICAMENTOS_REF = DIR_PROCESSED / "medicamentos_ref.csv"
SAIDA_LOTES = DIR_PROCESSED / "lotes.csv"
SAIDA_PEDIDOS = DIR_PROCESSED / "pedidos_pendentes.csv"

# ---------------------------------------------------------------------------
# 1. Cadastro de medicamentos (contrato 1.3)
#
# categoria "Respiratório"/pediátrico -> sensível a temperatura baixa/chuva.
# categoria "Gastro" (sintomas de dengue: náusea, febre, dor) e dor/febre ->
# sensível a casos de dengue, junto com soros (hidratação).
# Preço e prazo de entrega são estimativas de ordem de grandeza (não são
# preços reais de licitação), suficientes para demonstrar o cálculo de
# economia sem prometer precisão que não temos.
# ---------------------------------------------------------------------------

MEDICAMENTOS_REF = [
    # medicamento_id, nome, categoria, consumo_base_dia, prazo_entrega_dias, preco_unitario_reais, sensivel_clima, sensivel_dengue
    ("paracetamol", "Paracetamol", "Dor/febre", 180, 5, 0.15, False, True),
    ("dipirona", "Dipirona", "Dor/febre", 220, 5, 0.20, False, True),
    ("ibuprofeno", "Ibuprofeno", "Dor/febre", 90, 5, 0.30, False, False),
    ("soro_fisiologico", "Soro Fisiológico 0,9%", "Suporte/hidratação", 140, 6, 4.50, False, True),
    ("soro_ringer", "Soro Ringer Lactato", "Suporte/hidratação", 70, 6, 5.00, False, True),
    ("salbutamol", "Salbutamol (spray/nebulização)", "Respiratório", 60, 7, 18.00, True, False),
    ("predinisolona", "Predinisolona", "Respiratório", 40, 7, 0.90, True, False),
    ("hidrocortisona_inj", "Hidrocortisona injetável", "Respiratório/alergia", 25, 7, 6.00, True, False),
    ("omeprazol_inj", "Omeprazol injetável", "Gastro", 30, 6, 3.00, False, False),
    ("ondansetrona", "Ondansetrona", "Gastro", 35, 6, 4.50, False, True),
    ("metoclopramida", "Metoclopramida", "Gastro", 45, 6, 0.60, False, True),
    ("amoxicilina", "Amoxicilina", "Antibiótico", 50, 7, 0.80, False, False),
    ("azitromicina", "Azitromicina", "Antibiótico", 40, 7, 3.50, False, False),
    ("ceftriaxona_inj", "Ceftriaxona injetável", "Antibiótico", 35, 7, 12.00, False, False),
    ("diclofenaco", "Diclofenaco", "Dor/inflamação", 60, 5, 0.40, False, False),
    ("tramadol", "Tramadol", "Dor", 20, 8, 1.50, False, False),
    ("loratadina", "Loratadina", "Alergia", 30, 6, 0.35, True, False),
    ("soro_antitermico_infantil", "Soro Antitérmico Infantil", "Dor/febre (pediátrico)", 50, 6, 8.00, True, True),
    ("adrenalina_inj", "Adrenalina injetável", "Emergência/controlado", 5, 12, 8.50, False, False),
    ("diazepam", "Diazepam", "Emergência/controlado", 15, 12, 1.20, False, False),
]

COLUNAS_REF = [
    "medicamento_id",
    "nome",
    "categoria",
    "_consumo_base_dia",
    "prazo_entrega_dias",
    "preco_unitario_reais",
    "_sensivel_clima",
    "_sensivel_dengue",
]


def montar_medicamentos_ref() -> pd.DataFrame:
    df = pd.DataFrame(MEDICAMENTOS_REF, columns=COLUNAS_REF)
    return df


def carregar_externos() -> pd.DataFrame:
    """Carrega clima + epidemiologia + calendário (Issues #4/#5/#6), já commitados."""
    clima = pd.read_csv(DIR_EXTERNAL / "clima.csv", parse_dates=["data"])
    epi = pd.read_csv(DIR_EXTERNAL / "epidemiologia.csv", parse_dates=["data"])
    cal = pd.read_csv(DIR_EXTERNAL / "calendario.csv", parse_dates=["data"])

    externos = clima.merge(epi, on="data", how="inner").merge(cal[["data", "feriado"]], on="data", how="inner")
    if len(externos) != len(clima):
        raise ValueError("Merge de dados externos perdeu linhas — checar se os 3 arquivos cobrem o mesmo período.")
    return externos


# ---------------------------------------------------------------------------
# 2. Consumo diário (contrato 1.1)
# ---------------------------------------------------------------------------


def gerar_consumo_diario(externos: pd.DataFrame, medicamentos_ref: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    dias = externos["data"]
    n_dias = len(dias)

    dia_semana = dias.dt.dayofweek  # 0=segunda ... 6=domingo
    # ER tem mais procura no fim de semana (clínicas fechadas) e leve alta na segunda (represamento)
    fator_dia_semana = 1.0 + 0.10 * dia_semana.isin([5, 6]).astype(float) + 0.05 * (dia_semana == 0).astype(float)
    fator_feriado = 1.0 + 0.15 * externos["feriado"].astype(float)

    # Tendência leve de crescimento ao longo do período (mais atendimentos no fim do período)
    progresso = np.linspace(0, 1, n_dias)
    fator_tendencia = 1.0 + 0.08 * progresso

    # Normaliza temperatura/chuva/dengue em torno da própria mediana do período,
    # para os efeitos serem relativos (não dependerem de conhecer a escala exata).
    temp_norm = (externos["temperatura_media"].median() - externos["temperatura_media"]) / externos["temperatura_media"].std()
    chuva_norm = (externos["chuva_mm"] - externos["chuva_mm"].median()) / (externos["chuva_mm"].std() + 1e-6)
    dengue_norm = (externos["casos_dengue_regiao"] - externos["casos_dengue_regiao"].median()) / (
        externos["casos_dengue_regiao"].std() + 1e-6
    )

    fator_clima = 1.0 + 0.12 * temp_norm.clip(-2, 2) + 0.05 * chuva_norm.clip(-2, 2)
    fator_dengue = 1.0 + 0.15 * dengue_norm.clip(-2, 3)

    linhas = []
    for i, item in medicamentos_ref.iterrows():
        rng_item = np.random.default_rng(SEED + i)  # série reprodutível e independente por medicamento

        fator = fator_dia_semana.to_numpy() * fator_feriado.to_numpy() * fator_tendencia
        if item["_sensivel_clima"]:
            fator = fator * fator_clima.to_numpy()
        if item["_sensivel_dengue"]:
            fator = fator * fator_dengue.to_numpy()

        media = item["_consumo_base_dia"] * fator
        # Ruído multiplicativo (log-normal) + Poisson para manter valores inteiros plausíveis
        ruido = rng_item.lognormal(mean=0.0, sigma=0.12, size=n_dias)
        consumo = rng_item.poisson(lam=np.clip(media * ruido, 1, None))

        linhas.append(
            pd.DataFrame(
                {
                    "data": dias.dt.date.astype(str),
                    "medicamento_id": item["medicamento_id"],
                    "consumo_unidades": consumo.astype(float),
                }
            )
        )

    return pd.concat(linhas, ignore_index=True)


# ---------------------------------------------------------------------------
# 3. Simulação de estoque (entradas/saldo) com política de reposição "ingênua"
#    — representa como o hospital decide hoje, sem modelo preditivo. Serve de
#    baseline "real" para o motor de recomendação (Issues #14-16) melhorar.
# ---------------------------------------------------------------------------


def simular_estoque(consumo_diario: pd.DataFrame, medicamentos_ref: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    resultado = []
    for i, item in medicamentos_ref.iterrows():
        rng_item = np.random.default_rng(SEED + 1000 + i)
        serie = consumo_diario[consumo_diario["medicamento_id"] == item["medicamento_id"]].sort_values("data")
        consumo = serie["consumo_unidades"].to_numpy()
        n = len(consumo)

        prazo = int(item["prazo_entrega_dias"])
        media_movel_consumo = pd.Series(consumo).rolling(14, min_periods=1).mean().to_numpy()

        # Ponto de pedido "ingênuo": reordena quando o estoque cobre menos que o
        # prazo de entrega + 3 dias de folga, sem estoque de segurança calculado
        # (é exatamente essa lacuna que o projeto propõe resolver).
        ponto_pedido = media_movel_consumo * (prazo + 3)
        quantidade_pedido_padrao = media_movel_consumo * (prazo + 10)

        estoque = np.zeros(n)
        entradas = np.zeros(n)
        pedidos_em_transito = []  # lista de (dia_chegada, quantidade)

        estoque_atual = media_movel_consumo[0] * (prazo + 10) if n > 0 else 0.0
        for t in range(n):
            chegando_hoje = sum(q for dia, q in pedidos_em_transito if dia == t)
            pedidos_em_transito = [(dia, q) for dia, q in pedidos_em_transito if dia != t]
            entradas[t] = chegando_hoje
            estoque_atual += chegando_hoje

            estoque_atual -= consumo[t]
            # Estoque não pode ser negativo (ruptura = fica em 0, demanda não atendida é perdida)
            estoque_atual = max(estoque_atual, 0.0)
            estoque[t] = estoque_atual

            if estoque_atual < ponto_pedido[t] and not any(True for _ in pedidos_em_transito):
                # imperfeição proposital: às vezes o hospital demora a perceber e atrasa o pedido
                atraso_percepcao = rng_item.integers(0, 3)
                dia_chegada = t + prazo + atraso_percepcao
                if dia_chegada < n:
                    pedidos_em_transito.append((dia_chegada, quantidade_pedido_padrao[t]))

        resultado.append(
            pd.DataFrame(
                {
                    "data": serie["data"].to_numpy(),
                    "medicamento_id": item["medicamento_id"],
                    "consumo_unidades": consumo,
                    "entradas_unidades": entradas,
                    "estoque_disponivel": estoque,
                }
            )
        )

    return pd.concat(resultado, ignore_index=True)


# ---------------------------------------------------------------------------
# 4. Sinais internos agregados (ocupação de leitos, atendimentos no PS)
# ---------------------------------------------------------------------------


def gerar_sinais_internos(externos: pd.DataFrame, consumo_diario: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    consumo_total_dia = consumo_diario.groupby("data")["consumo_unidades"].sum().reset_index()
    consumo_total_dia["data"] = pd.to_datetime(consumo_total_dia["data"])
    consumo_total_dia = consumo_total_dia.sort_values("data")

    # Atendimentos correlacionados com o consumo total agregado (mais atendimento -> mais consumo),
    # escalado para uma faixa plausível de PS de porte médio, com ruído próprio.
    base = 90 + 25 * (
        (consumo_total_dia["consumo_unidades"] - consumo_total_dia["consumo_unidades"].mean())
        / consumo_total_dia["consumo_unidades"].std()
    )
    ruido = rng.normal(0, 6, size=len(base))
    atendimentos = np.clip(base + ruido, 30, None).round().astype(int)

    ocupacao = np.clip(45 + 0.35 * (atendimentos - atendimentos.mean()) + rng.normal(0, 4, size=len(base)), 20, 100)

    return pd.DataFrame(
        {
            "data": consumo_total_dia["data"].dt.date.astype(str),
            "atendimentos_ps": atendimentos,
            "ocupacao_leitos_pct": ocupacao.round(1),
        }
    )


# ---------------------------------------------------------------------------
# 5. Lotes (contrato 1.4) — derivados do estoque final de cada medicamento,
#    com 2 a 3 casos propositalmente "extremos" para dar exemplos reais de
#    risco de vencimento e de ruptura no dashboard.
# ---------------------------------------------------------------------------

# medicamento_id escolhidos deliberadamente para ilustrar os dois riscos do projeto
MEDICAMENTOS_RISCO_VENCIMENTO = {"ceftriaxona_inj", "hidrocortisona_inj"}  # lote grande, validade próxima
MEDICAMENTOS_RISCO_FALTA = {"adrenalina_inj", "salbutamol"}  # estoque baixo relativo ao consumo


def gerar_lotes(estoque_final: pd.DataFrame, medicamentos_ref: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    linhas = []
    fim = pd.Timestamp(PERIODO_FIM)

    for i, item in medicamentos_ref.iterrows():
        rng_item = np.random.default_rng(SEED + 2000 + i)
        med_id = item["medicamento_id"]
        qtd_final = float(estoque_final.loc[estoque_final["medicamento_id"] == med_id, "estoque_disponivel"].iloc[-1])

        if med_id in MEDICAMENTOS_RISCO_FALTA:
            qtd_final = min(qtd_final, item["_consumo_base_dia"] * 1.5)  # força estoque baixo

        n_lotes = rng_item.integers(2, 4)
        pesos = rng_item.dirichlet(np.ones(n_lotes))
        quantidades = np.maximum((qtd_final * pesos).round(), 0)

        for lote_idx in range(n_lotes):
            dias_desde_entrada = int(rng_item.integers(5, 120))
            data_entrada = fim - pd.Timedelta(days=dias_desde_entrada)

            if med_id in MEDICAMENTOS_RISCO_VENCIMENTO and lote_idx == 0:
                dias_ate_validade = int(rng_item.integers(10, 25))  # vence em breve, e é o lote com mais quantidade
                quantidades[0] = max(quantidades[0], item["_consumo_base_dia"] * 20)
            else:
                dias_ate_validade = int(rng_item.integers(180, 720))

            data_validade = fim + pd.Timedelta(days=dias_ate_validade)

            linhas.append(
                {
                    "medicamento_id": med_id,
                    "lote_id": f"{med_id}-L{lote_idx + 1:02d}",
                    "quantidade_atual": float(quantidades[lote_idx]),
                    "data_entrada": data_entrada.date().isoformat(),
                    "data_validade": data_validade.date().isoformat(),
                }
            )

    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# 6. Pedidos pendentes (contrato 1.5) — pedidos "em trânsito" no fim do período
# ---------------------------------------------------------------------------


def gerar_pedidos_pendentes(medicamentos_ref: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    linhas = []
    fim = pd.Timestamp(PERIODO_FIM)

    for i, item in medicamentos_ref.iterrows():
        rng_item = np.random.default_rng(SEED + 3000 + i)
        if rng_item.random() > 0.35:  # nem todo medicamento tem pedido em aberto no corte
            continue

        prazo = int(item["prazo_entrega_dias"])
        dias_desde_pedido = int(rng_item.integers(1, max(prazo - 1, 2)))
        data_pedido = fim - pd.Timedelta(days=dias_desde_pedido)
        data_prevista_entrega = data_pedido + pd.Timedelta(days=prazo)
        quantidade = float(item["_consumo_base_dia"] * rng_item.integers(prazo, prazo + 10))

        linhas.append(
            {
                "medicamento_id": item["medicamento_id"],
                "pedido_id": f"{item['medicamento_id']}-P001",
                "quantidade": quantidade,
                "data_pedido": data_pedido.date().isoformat(),
                "data_prevista_entrega": data_prevista_entrega.date().isoformat(),
            }
        )

    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------


def validar_consumo_diario(df: pd.DataFrame, medicamentos_ref: pd.DataFrame) -> None:
    esperado_dias = pd.date_range(start=PERIODO_INICIO, end=PERIODO_FIM, freq="D")
    ids_esperados = set(medicamentos_ref["medicamento_id"])

    if set(df["medicamento_id"].unique()) != ids_esperados:
        raise ValueError("medicamento_id no consumo_diario não bate com medicamentos_ref.")

    for med_id, grupo in df.groupby("medicamento_id"):
        datas = pd.to_datetime(grupo["data"])
        if len(grupo) != len(esperado_dias) or set(datas) != set(esperado_dias):
            raise ValueError(f"{med_id}: dias faltando ou duplicados no período esperado.")

    if (df["consumo_unidades"] < 0).any():
        raise ValueError("consumo_unidades negativo encontrado.")
    if (df["estoque_disponivel"] < 0).any():
        raise ValueError("estoque_disponivel negativo encontrado.")
    if df[["consumo_unidades", "entradas_unidades", "estoque_disponivel"]].isna().any().any():
        raise ValueError("Valores nulos encontrados em consumo_diario.")


def validar_lotes(df: pd.DataFrame, medicamentos_ref: pd.DataFrame) -> None:
    if not set(df["medicamento_id"]).issubset(set(medicamentos_ref["medicamento_id"])):
        raise ValueError("lotes.csv tem medicamento_id fora da lista de referência.")
    if (df["quantidade_atual"] < 0).any():
        raise ValueError("quantidade_atual negativa em lotes.csv.")
    if (pd.to_datetime(df["data_validade"]) <= pd.to_datetime(df["data_entrada"])).any():
        raise ValueError("Há lote com data_validade anterior/igual à data_entrada.")


def validar_pedidos(df: pd.DataFrame, medicamentos_ref: pd.DataFrame) -> None:
    if not set(df["medicamento_id"]).issubset(set(medicamentos_ref["medicamento_id"])):
        raise ValueError("pedidos_pendentes.csv tem medicamento_id fora da lista de referência.")
    if (pd.to_datetime(df["data_prevista_entrega"]) <= pd.to_datetime(df["data_pedido"])).any():
        raise ValueError("Há pedido com data_prevista_entrega anterior/igual à data_pedido.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    rng = np.random.default_rng(SEED)

    medicamentos_ref = montar_medicamentos_ref()
    externos = carregar_externos()

    consumo_bruto = gerar_consumo_diario(externos, medicamentos_ref, rng)
    consumo_com_estoque = simular_estoque(consumo_bruto, medicamentos_ref, rng)
    sinais_internos = gerar_sinais_internos(externos, consumo_bruto, rng)

    consumo_diario = consumo_com_estoque.merge(sinais_internos, on="data", how="left")
    consumo_diario = consumo_diario[
        ["data", "medicamento_id", "consumo_unidades", "estoque_disponivel", "entradas_unidades", "ocupacao_leitos_pct", "atendimentos_ps"]
    ]

    lotes = gerar_lotes(consumo_com_estoque, medicamentos_ref, rng)
    pedidos = gerar_pedidos_pendentes(medicamentos_ref, rng)

    validar_consumo_diario(consumo_diario, medicamentos_ref)
    validar_lotes(lotes, medicamentos_ref)
    validar_pedidos(pedidos, medicamentos_ref)

    DIR_PROCESSED.mkdir(parents=True, exist_ok=True)
    consumo_diario.to_csv(SAIDA_CONSUMO, index=False, encoding="utf-8")
    medicamentos_ref.drop(columns=["_consumo_base_dia", "_sensivel_clima", "_sensivel_dengue"]).to_csv(
        SAIDA_MEDICAMENTOS_REF, index=False, encoding="utf-8"
    )
    lotes.to_csv(SAIDA_LOTES, index=False, encoding="utf-8")
    pedidos.to_csv(SAIDA_PEDIDOS, index=False, encoding="utf-8")

    print(f"consumo_diario.csv: {len(consumo_diario)} linhas ({len(medicamentos_ref)} medicamentos x {consumo_diario['data'].nunique()} dias)")
    print(f"medicamentos_ref.csv: {len(medicamentos_ref)} linhas")
    print(f"lotes.csv: {len(lotes)} linhas")
    print(f"pedidos_pendentes.csv: {len(pedidos)} linhas")

    total_rupturas = int((consumo_diario["estoque_disponivel"] == 0).sum())
    print(f"Dias-medicamento com estoque zerado (ruptura) no período: {total_rupturas}")


if __name__ == "__main__":
    main()
