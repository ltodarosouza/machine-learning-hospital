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
ATENDIMENTOS_BASE_DIA = 95.0

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
# 1.5. Estados latentes persistentes de surto (Issue #58)
#
# Antes desta issue, a única fonte de variação de curto prazo era ruído
# i.i.d. (log-normal independente por dia). Isso significa que o previsor
# teoricamente ótimo já era a própria média-base — nenhum modelo de ML
# consegue prever ruído i.i.d. por construção, o que limitava estruturalmente
# o quanto o modelo (Issue #12) conseguia bater o baseline (Issue #13).
#
# Aqui adicionamos um processo latente com memória: uma cadeia de Markov de
# 3 estados (normal / elevado / surto) que simula surtos com duração real de
# alguns dias a algumas semanas — não um sorteio novo a cada dia. Dois
# processos independentes são gerados (não por medicamento, mas
# compartilhados por categoria sensível, como um "surto" de verdade afetaria
# vários medicamentos ao mesmo tempo): um para itens sensíveis a
# clima/respiratório, outro para itens sensíveis a dengue/arboviroses,
# reaproveitando `_sensivel_clima`/`_sensivel_dengue` já existentes.
#
# Isso não elimina o ruído diário (dado real também tem imprevisibilidade),
# só deixa de ser a única fonte de variação de curto prazo.
# ---------------------------------------------------------------------------

ESTADOS_SURTO = ("normal", "elevado", "surto")
MULTIPLICADOR_SURTO = {"normal": 1.0, "elevado": 1.35, "surto": 1.9}

# Matriz de transição (linha = estado atual, coluna = próximo estado).
# Calibrada para que episódios de "elevado"/"surto" durem tipicamente entre
# 1 e 4 semanas (não 1 dia isolado) antes de voltar ao normal — ver
# test_gerador_sintetico.py::test_estado_surto_tem_duracao_de_dias_nao_de_um_dia
# para a verificação empírica da duração média.
TRANSICAO_SURTO = np.array(
    [
        [0.97, 0.025, 0.005],  # normal -> normal / elevado / surto
        [0.08, 0.85, 0.07],  # elevado -> normal / elevado / surto
        [0.05, 0.15, 0.80],  # surto -> normal / elevado / surto
    ]
)


def gerar_estado_surto(n_dias: int, rng: np.random.Generator) -> np.ndarray:
    """Cadeia de Markov de 3 estados simulando surtos com duração de dias/semanas."""
    estados = np.zeros(n_dias, dtype=int)
    estado_atual = 0  # começa "normal"
    for t in range(n_dias):
        estados[t] = estado_atual
        estado_atual = rng.choice(3, p=TRANSICAO_SURTO[estado_atual])
    return estados


def fator_surto(estados: np.ndarray) -> np.ndarray:
    """Converte a sequência de estados (índices 0/1/2) no multiplicador correspondente."""
    multiplicadores = np.array([MULTIPLICADOR_SURTO[estado] for estado in ESTADOS_SURTO])
    return multiplicadores[estados]


# ---------------------------------------------------------------------------
# 2. Consumo diário (contrato 1.1)
# ---------------------------------------------------------------------------


def _calcular_fatores_contexto(externos: pd.DataFrame) -> dict[str, np.ndarray]:
    """Calcula os fatores externos e os surtos compartilhados pelo gerador.

    Este contexto é usado tanto para gerar os atendimentos quanto para
    definir a propensão por categoria de medicamento. Ele não depende do
    consumo, mantendo a ordem causal do processo sintético.
    """
    n_dias = len(externos)
    dias = externos["data"]

    dia_semana = dias.dt.dayofweek
    fator_dia_semana = 1.0 + 0.10 * dia_semana.isin([5, 6]).astype(float) + 0.05 * (dia_semana == 0).astype(float)
    fator_feriado = 1.0 + 0.15 * externos["feriado"].astype(float)
    fator_tendencia = 1.0 + 0.08 * np.linspace(0, 1, n_dias)

    temp_norm = (externos["temperatura_media"].median() - externos["temperatura_media"]) / externos["temperatura_media"].std()
    chuva_norm = (externos["chuva_mm"] - externos["chuva_mm"].median()) / (externos["chuva_mm"].std() + 1e-6)
    dengue_norm = (externos["casos_dengue_regiao"] - externos["casos_dengue_regiao"].median()) / (
        externos["casos_dengue_regiao"].std() + 1e-6
    )

    fator_clima = 1.0 + 0.12 * temp_norm.clip(-2, 2) + 0.05 * chuva_norm.clip(-2, 2)
    fator_dengue = 1.0 + 0.15 * dengue_norm.clip(-2, 3)

    estado_surto_respiratorio = gerar_estado_surto(n_dias, np.random.default_rng(SEED + 9000))
    estado_surto_dengue = gerar_estado_surto(n_dias, np.random.default_rng(SEED + 9001))

    return {
        "fator_dia_semana": fator_dia_semana.to_numpy(),
        "fator_feriado": fator_feriado.to_numpy(),
        "fator_tendencia": fator_tendencia,
        "fator_clima": fator_clima.to_numpy(),
        "fator_dengue": fator_dengue.to_numpy(),
        "fator_surto_respiratorio": fator_surto(estado_surto_respiratorio),
        "fator_surto_dengue": fator_surto(estado_surto_dengue),
    }


def gerar_consumo_diario(
    externos: pd.DataFrame,
    medicamentos_ref: pd.DataFrame,
    rng: np.random.Generator,
    sinais_internos: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Gera o consumo depois que os atendimentos do PS já foram observados.

    ``sinais_internos`` é opcional apenas para manter compatibilidade com
    chamadas antigas: quando omitido, ele é gerado primeiro a partir dos
    dados externos, nunca a partir do consumo.
    """
    dias = externos["data"]
    n_dias = len(dias)

    if sinais_internos is None:
        sinais_internos = gerar_sinais_internos(externos, rng)
    sinais_por_data = sinais_internos.copy()
    sinais_por_data["data"] = pd.to_datetime(sinais_por_data["data"])
    sinais_por_data = sinais_por_data.set_index("data").reindex(pd.DatetimeIndex(dias))
    if sinais_por_data["atendimentos_ps"].isna().any():
        raise ValueError("sinais_internos não cobre todas as datas dos dados externos.")
    fator_atendimentos = sinais_por_data["atendimentos_ps"].to_numpy() / ATENDIMENTOS_BASE_DIA
    fatores = _calcular_fatores_contexto(externos)

    linhas = []
    for i, item in medicamentos_ref.iterrows():
        rng_item = np.random.default_rng(SEED + i)  # série reprodutível e independente por medicamento

        # O volume geral vem dos atendimentos gerados antes do consumo. Os
        # fatores abaixo representam a composição específica de cada categoria.
        fator = fator_atendimentos.copy()
        if item["_sensivel_clima"]:
            fator = fator * fatores["fator_clima"] * fatores["fator_surto_respiratorio"]
        if item["_sensivel_dengue"]:
            fator = fator * fatores["fator_dengue"] * fatores["fator_surto_dengue"]

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


def simular_estoque(
    consumo_diario: pd.DataFrame,
    medicamentos_ref: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Simula saldo e torna auditavel a censura causada por uma ruptura.

    ``consumo_unidades`` e a demanda latente gerada antes da politica de
    estoque: e o alvo que o modelo deve prever. A dispensacao, por outro lado,
    nunca pode ultrapassar o saldo disponivel apos as entradas do dia.
    """
    resultado = []
    for i, item in medicamentos_ref.iterrows():
        rng_item = np.random.default_rng(SEED + 1000 + i)
        serie = consumo_diario[consumo_diario["medicamento_id"] == item["medicamento_id"]].sort_values("data")
        demanda = serie["consumo_unidades"].to_numpy()
        n = len(demanda)

        prazo = int(item["prazo_entrega_dias"])
        media_movel_consumo = pd.Series(demanda).rolling(14, min_periods=1).mean().to_numpy()

        # Ponto de pedido "ingênuo": reordena quando o estoque cobre menos que o
        # prazo de entrega + 3 dias de folga, sem estoque de segurança calculado
        # (é exatamente essa lacuna que o projeto propõe resolver).
        ponto_pedido = media_movel_consumo * (prazo + 3)
        quantidade_pedido_padrao = media_movel_consumo * (prazo + 10)

        estoque = np.zeros(n)
        entradas = np.zeros(n)
        dispensacao = np.zeros(n)
        demanda_nao_atendida = np.zeros(n)
        pedidos_em_transito = []  # lista de (dia_chegada, quantidade)

        estoque_atual = media_movel_consumo[0] * (prazo + 10) if n > 0 else 0.0
        for t in range(n):
            chegando_hoje = sum(q for dia, q in pedidos_em_transito if dia == t)
            pedidos_em_transito = [(dia, q) for dia, q in pedidos_em_transito if dia != t]
            entradas[t] = chegando_hoje
            estoque_atual += chegando_hoje

            dispensacao[t] = min(demanda[t], estoque_atual)
            demanda_nao_atendida[t] = demanda[t] - dispensacao[t]
            estoque_atual -= dispensacao[t]
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
                    "consumo_unidades": demanda,
                    "dispensacao_unidades": dispensacao,
                    "demanda_nao_atendida": demanda_nao_atendida,
                    "entradas_unidades": entradas,
                    "estoque_disponivel": estoque,
                }
            )
        )

    return pd.concat(resultado, ignore_index=True)


# ---------------------------------------------------------------------------
# 4. Sinais internos agregados (ocupação de leitos, atendimentos no PS)
# ---------------------------------------------------------------------------


def gerar_sinais_internos(externos: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Gera atendimentos e ocupação a partir de sinais disponíveis antes do consumo."""
    fatores = _calcular_fatores_contexto(externos)
    fator_surto_atendimentos = (
        0.65 * fatores["fator_surto_respiratorio"] + 0.35 * fatores["fator_surto_dengue"]
    )
    fator_externo = (
        fatores["fator_dia_semana"]
        * fatores["fator_feriado"]
        * fatores["fator_tendencia"]
        * (1.0 + 0.08 * (fatores["fator_clima"] - 1.0))
        * (1.0 + 0.08 * (fatores["fator_dengue"] - 1.0))
    )
    media_atendimentos = ATENDIMENTOS_BASE_DIA * fator_externo * fator_surto_atendimentos
    ruido = rng.normal(0, 5, size=len(externos))
    atendimentos = np.clip(media_atendimentos + ruido, 30, None).round().astype(int)

    ocupacao = np.clip(45 + 0.35 * (atendimentos - atendimentos.mean()) + rng.normal(0, 4, size=len(atendimentos)), 20, 100)

    return pd.DataFrame(
        {
            "data": externos["data"].dt.date.astype(str),
            "atendimentos_ps": atendimentos,
            "ocupacao_leitos_pct": ocupacao.round(1),
        }
    )


# ---------------------------------------------------------------------------
# 5. Lotes (contrato 1.4) — derivados do estoque final de cada medicamento.
#
# Invariante (Issue #53, formalizada em CONTRATOS.md seção 1.4): a soma de
# `quantidade_atual` dos lotes de um medicamento deve ser igual a
# `estoque_disponivel` do último dia em `consumo_diario.csv`, a menos de
# arredondamento (tolerância: no máximo 1 unidade, por causa da conversão de
# `qtd_final` — que pode não ser inteiro — para quantidades inteiras por
# lote). Antes desta correção, dois grupos de medicamentos tinham a
# quantidade dos lotes **sobrescrita** para criar exemplos "dramáticos" de
# risco de vencimento/falta, o que quebrava essa invariante (Issue #53,
# reportada por hguimaa) — a versão atual nunca inventa quantidade: os casos
# de risco de vencimento continuam existindo, mas concentrando uma fração do
# estoque real num lote de validade curta, em vez de inflar o total.
# ---------------------------------------------------------------------------

# medicamento_id escolhido deliberadamente para ilustrar risco de vencimento
# com dado consistente: concentra a maior parte do estoque REAL desse
# medicamento num lote com validade curta (poucos dias), o suficiente para
# não dar tempo de ser consumido no ritmo normal — sem inventar quantidade.
MEDICAMENTOS_RISCO_VENCIMENTO = {"ceftriaxona_inj", "hidrocortisona_inj"}


def _distribuir_quantidade_inteira(total: float, pesos: np.ndarray) -> np.ndarray:
    """Distribui `round(total)` unidades entre `pesos`, com soma exatamente igual ao total (método do maior resto).

    Evita o problema de arredondar cada fatia isoladamente (que pode fazer a
    soma final divergir do total em várias unidades, dependendo do número de
    lotes) — aqui o desvio máximo possível é 1 unidade, só por causa do
    arredondamento do próprio `total` (que normalmente já é ~inteiro).
    """
    total_inteiro = int(round(total))
    se_total_zero = total_inteiro <= 0
    if se_total_zero:
        return np.zeros(len(pesos))

    brutos = total_inteiro * pesos
    base = np.floor(brutos).astype(int)
    resto = total_inteiro - base.sum()
    if resto > 0:
        ordem_maior_resto = np.argsort(-(brutos - base))
        for idx in ordem_maior_resto[:resto]:
            base[idx] += 1
    return base.astype(float)


def gerar_lotes(estoque_final: pd.DataFrame, medicamentos_ref: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    linhas = []
    fim = pd.Timestamp(PERIODO_FIM)

    for i, item in medicamentos_ref.iterrows():
        rng_item = np.random.default_rng(SEED + 2000 + i)
        med_id = item["medicamento_id"]
        qtd_final = float(estoque_final.loc[estoque_final["medicamento_id"] == med_id, "estoque_disponivel"].iloc[-1])

        n_lotes = int(rng_item.integers(2, 4))

        if med_id in MEDICAMENTOS_RISCO_VENCIMENTO and n_lotes > 1:
            # concentra a maior parte do estoque real num único lote (validade curta),
            # em vez de espalhar uniformemente — sem alterar o total.
            fracao_concentrada = rng_item.uniform(0.8, 0.95)
            pesos = np.full(n_lotes, (1 - fracao_concentrada) / (n_lotes - 1))
            pesos[0] = fracao_concentrada
        else:
            pesos = rng_item.dirichlet(np.ones(n_lotes))

        quantidades = _distribuir_quantidade_inteira(qtd_final, pesos)

        for lote_idx in range(n_lotes):
            dias_desde_entrada = int(rng_item.integers(5, 120))
            data_entrada = fim - pd.Timedelta(days=dias_desde_entrada)

            if med_id in MEDICAMENTOS_RISCO_VENCIMENTO and lote_idx == 0:
                # validade curta o bastante para não dar tempo de consumir no ritmo
                # normal: calculada a partir do próprio consumo-base do medicamento
                # (não um número redondo qualquer), com folga de 30% para continuar
                # valendo mesmo com a demanda mais alta do fim do período (tendência
                # de crescimento). Clipada entre 2 e 10 dias para continuar plausível.
                quantidade_lote = quantidades[0]
                consumo_base_dia = max(item["_consumo_base_dia"], 1.0)
                dias_para_estourar_o_risco = quantidade_lote / (consumo_base_dia * 1.3)
                dias_ate_validade = int(np.clip(dias_para_estourar_o_risco, 2, 10))
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
    if (df["dispensacao_unidades"] < 0).any():
        raise ValueError("dispensacao_unidades negativa encontrada.")
    if (df["demanda_nao_atendida"] < 0).any():
        raise ValueError("demanda_nao_atendida negativa encontrada.")
    if not np.allclose(
        df["consumo_unidades"],
        df["dispensacao_unidades"] + df["demanda_nao_atendida"],
    ):
        raise ValueError(
            "consumo_unidades deve ser igual a dispensacao_unidades mais demanda_nao_atendida."
        )
    if (df["dispensacao_unidades"] > df["consumo_unidades"]).any():
        raise ValueError("dispensacao_unidades nao pode superar a demanda latente.")
    if (df["estoque_disponivel"] < 0).any():
        raise ValueError("estoque_disponivel negativo encontrado.")
    colunas_numericas = [
        "consumo_unidades",
        "dispensacao_unidades",
        "demanda_nao_atendida",
        "entradas_unidades",
        "estoque_disponivel",
    ]
    if df[colunas_numericas].isna().any().any():
        raise ValueError("Valores nulos encontrados em consumo_diario.")


TOLERANCIA_INVENTARIO_UNIDADES = 1.0  # ver CONTRATOS.md secao 1.4


def validar_lotes(df: pd.DataFrame, medicamentos_ref: pd.DataFrame, consumo_diario: pd.DataFrame) -> None:
    if not set(df["medicamento_id"]).issubset(set(medicamentos_ref["medicamento_id"])):
        raise ValueError("lotes.csv tem medicamento_id fora da lista de referência.")
    if (df["quantidade_atual"] < 0).any():
        raise ValueError("quantidade_atual negativa em lotes.csv.")
    if (pd.to_datetime(df["data_validade"]) <= pd.to_datetime(df["data_entrada"])).any():
        raise ValueError("Há lote com data_validade anterior/igual à data_entrada.")

    # Invariante de inventário (Issue #53): soma dos lotes == estoque_disponivel
    # do último dia, por medicamento, a menos da tolerância de arredondamento.
    soma_lotes = df.groupby("medicamento_id")["quantidade_atual"].sum()
    ultimo_estoque = (
        consumo_diario.sort_values("data").groupby("medicamento_id")["estoque_disponivel"].last()
    )
    divergencia = (soma_lotes - ultimo_estoque).abs().dropna()
    inconsistentes = divergencia[divergencia > TOLERANCIA_INVENTARIO_UNIDADES]
    if not inconsistentes.empty:
        raise ValueError(
            "Soma dos lotes diverge de estoque_disponivel além da tolerância "
            f"({TOLERANCIA_INVENTARIO_UNIDADES} unidade) para: {inconsistentes.to_dict()}"
        )


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

    sinais_internos = gerar_sinais_internos(externos, rng)
    consumo_bruto = gerar_consumo_diario(externos, medicamentos_ref, rng, sinais_internos)
    consumo_com_estoque = simular_estoque(consumo_bruto, medicamentos_ref, rng)

    consumo_diario = consumo_com_estoque.merge(sinais_internos, on="data", how="left")
    consumo_diario = consumo_diario[
        [
            "data",
            "medicamento_id",
            "consumo_unidades",
            "dispensacao_unidades",
            "demanda_nao_atendida",
            "estoque_disponivel",
            "entradas_unidades",
            "ocupacao_leitos_pct",
            "atendimentos_ps",
        ]
    ]

    lotes = gerar_lotes(consumo_com_estoque, medicamentos_ref, rng)
    pedidos = gerar_pedidos_pendentes(medicamentos_ref, rng)

    validar_consumo_diario(consumo_diario, medicamentos_ref)
    validar_lotes(lotes, medicamentos_ref, consumo_diario)
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
    print(
        "Unidades de demanda nao atendida no periodo: "
        f"{consumo_diario['demanda_nao_atendida'].sum():.0f}"
    )


if __name__ == "__main__":
    main()
