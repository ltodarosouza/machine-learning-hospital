"""Suite canonica do contrato e das validacoes do motor de recomendacao."""

import numpy as np
import pandas as pd
import pytest

from src.recommendation.motor_recomendacao import COLUNAS_SAIDA, gerar_recomendacoes


def _previsoes(valores=(10.0,), medicamento="med_a"):
    return pd.DataFrame(
        {
            "medicamento_id": [medicamento] * len(valores),
            "data_previsao": pd.date_range("2026-01-01", periods=len(valores)),
            "demanda_prevista": valores,
        }
    )


def _seguranca(valor=2.0, medicamento="med_a"):
    return pd.DataFrame({"medicamento_id": [medicamento], "estoque_seguranca": [valor]})


def _estoque(valor=3.0, medicamento="med_a"):
    return pd.DataFrame(
        {
            "medicamento_id": [medicamento],
            "data": ["2025-12-31"],
            "estoque_disponivel": [valor],
        }
    )


def _pedidos(valores=(), medicamento="med_a"):
    return pd.DataFrame(
        {"medicamento_id": [medicamento] * len(valores), "quantidade": valores}
    )


def _executar_motor(
    previsoes: pd.DataFrame,
    seguranca: pd.DataFrame,
    estoque: pd.DataFrame,
    pedidos: pd.DataFrame,
    **opcionais,
) -> pd.DataFrame:
    """Chama a API publica por nome para tornar a ordem canonica explicita."""
    return gerar_recomendacoes(
        previsoes=previsoes,
        estoque_atual=estoque,
        estoque_seguranca=seguranca,
        pedidos_pendentes=pedidos,
        **opcionais,
    )


def test_api_publica_usa_ordem_documentada_dos_estoques():
    resultado = gerar_recomendacoes(_previsoes(), _estoque(), _seguranca(), _pedidos())

    assert resultado.loc[0, "compra_recomendada"] == 9


def test_estoque_insuficiente_resulta_em_recomendacao_positiva():
    resultado = _executar_motor(
        _previsoes((20,)), _seguranca(2), _estoque(3), _pedidos()
    )

    assert resultado.loc[0, "compra_recomendada"] == 19
    assert "Demanda prevista para o horizonte: 20" in resultado.loc[0, "justificativa"]


def test_estoque_suficiente_resulta_exatamente_em_zero_e_nunca_negativo():
    resultado = _executar_motor(
        _previsoes((5,)), _seguranca(2), _estoque(10), _pedidos()
    )

    assert resultado.loc[0, "compra_recomendada"] == 0
    assert (resultado["compra_recomendada"] >= 0).all()


def test_demanda_zero_sem_estoque_nao_recomenda_compra():
    resultado = _executar_motor(
        _previsoes((0,)), _seguranca(0), _estoque(0), _pedidos()
    )

    assert resultado.loc[0, "compra_recomendada"] == 0


def test_pedidos_confirmados_reduzem_recomendacao():
    sem_pedido = _executar_motor(
        _previsoes((20,)), _seguranca(), _estoque(), _pedidos()
    )
    com_pedido = _executar_motor(
        _previsoes((20,)), _seguranca(), _estoque(), _pedidos((4,))
    )

    assert sem_pedido.loc[0, "compra_recomendada"] == 19
    assert com_pedido.loc[0, "compra_recomendada"] == 15


def test_medicamento_sem_pedido_assume_zero():
    resultado = _executar_motor(_previsoes((10,)), _seguranca(), _estoque(), _pedidos())

    assert resultado.loc[0, "compra_recomendada"] == 9
    assert "pedidos confirmados: 0" in resultado.loc[0, "justificativa"]


def test_multiplos_dias_e_pedidos_sao_agregados_e_usa_estoque_mais_recente():
    estoque = pd.DataFrame(
        {
            "medicamento_id": ["med_a", "med_a"],
            "data": ["2025-12-30", "2025-12-31"],
            "estoque_disponivel": [100, 4],
        }
    )
    resultado = _executar_motor(
        _previsoes((5, 6, 7)), _seguranca(2), estoque, _pedidos((3, 4))
    )

    assert resultado.loc[0, "compra_recomendada"] == 9


def test_multiplos_medicamentos_nao_sao_misturados():
    previsoes = pd.concat(
        [_previsoes((10, 10), "med_a"), _previsoes((30, 30), "med_b")]
    )
    seguranca = pd.concat([_seguranca(2, "med_a"), _seguranca(5, "med_b")])
    estoque = pd.concat([_estoque(3, "med_a"), _estoque(10, "med_b")])
    pedidos = pd.concat([_pedidos((4,), "med_a"), _pedidos((20,), "med_b")])

    resultado = _executar_motor(previsoes, seguranca, estoque, pedidos).set_index(
        "medicamento_id"
    )

    assert resultado.loc["med_a", "compra_recomendada"] == 15
    assert resultado.loc["med_b", "compra_recomendada"] == 35


def test_estoque_seguranca_maior_aumenta_recomendacao():
    sem_buffer = _executar_motor(
        _previsoes((20,)), _seguranca(0), _estoque(5), _pedidos((3,))
    )
    com_buffer = _executar_motor(
        _previsoes((20,)), _seguranca(7), _estoque(5), _pedidos((3,))
    )

    assert sem_buffer.loc[0, "compra_recomendada"] == 12
    assert com_buffer.loc[0, "compra_recomendada"] == 19
    assert (
        com_buffer.loc[0, "compra_recomendada"]
        > sem_buffer.loc[0, "compra_recomendada"]
    )


def test_rejeita_coluna_obrigatoria_ausente_e_valor_invalido():
    with pytest.raises(ValueError, match="colunas obrigatorias"):
        _executar_motor(
            _previsoes().drop(columns="demanda_prevista"),
            _seguranca(),
            _estoque(),
            _pedidos(),
        )

    previsoes = _previsoes((-1,))
    with pytest.raises(ValueError, match="valores negativos"):
        _executar_motor(previsoes, _seguranca(), _estoque(), _pedidos())


def test_nao_modifica_dataframes_recebidos():
    entradas = [_previsoes((10, 12)), _seguranca(), _estoque(), _pedidos((1, 2))]
    copias = [entrada.copy(deep=True) for entrada in entradas]

    _executar_motor(*entradas)

    for entrada, copia in zip(entradas, copias, strict=True):
        pd.testing.assert_frame_equal(entrada, copia)


def test_rejeita_duplicidades_ambiguas_e_falta_de_cobertura():
    previsoes_duplicadas = pd.concat([_previsoes((10,)), _previsoes((20,))])
    with pytest.raises(ValueError, match="duplicadas"):
        _executar_motor(previsoes_duplicadas, _seguranca(), _estoque(), _pedidos())

    with pytest.raises(ValueError, match="sem dados para medicamentos previstos"):
        _executar_motor(
            _previsoes(), _seguranca(medicamento="outro"), _estoque(), _pedidos()
        )


@pytest.mark.parametrize(
    "valor", [float("nan"), float("inf"), float("-inf"), "invalido", True]
)
@pytest.mark.parametrize(
    "entrada,coluna",
    [
        ("previsoes", "demanda_prevista"),
        ("seguranca", "estoque_seguranca"),
        ("estoque", "estoque_disponivel"),
        ("pedidos", "quantidade"),
    ],
)
def test_rejeita_valores_numericos_invalidos(valor, entrada, coluna):
    entradas = {
        "previsoes": _previsoes(),
        "seguranca": _seguranca(),
        "estoque": _estoque(),
        "pedidos": _pedidos((1,)),
    }
    entradas[entrada][coluna] = pd.Series(
        [valor] * len(entradas[entrada]), dtype=object
    )

    erro = TypeError if valor is True else ValueError
    with pytest.raises(erro, match=coluna):
        _executar_motor(
            entradas["previsoes"],
            entradas["seguranca"],
            entradas["estoque"],
            entradas["pedidos"],
        )


@pytest.mark.parametrize(
    "pedidos",
    [
        pd.DataFrame(),
        pd.DataFrame(
            columns=[
                "medicamento_id",
                "pedido_id",
                "quantidade",
                "data_pedido",
                "data_prevista_entrega",
            ]
        ),
    ],
)
def test_aceita_representacoes_de_nenhum_pedido(pedidos):
    resultado = _executar_motor(_previsoes(), _seguranca(), _estoque(), pedidos)

    assert resultado.loc[0, "compra_recomendada"] == 9
    assert "pedidos confirmados: 0" in resultado.loc[0, "justificativa"]


def test_desconta_apenas_pedido_com_entrega_dentro_do_horizonte():
    previsoes = _previsoes((10, 10, 10))
    pedidos = pd.DataFrame(
        {
            "medicamento_id": ["med_a", "med_a"],
            "pedido_id": ["dentro", "depois"],
            "quantidade": [4, 100],
            "data_pedido": ["2025-12-29", "2025-12-29"],
            "data_prevista_entrega": ["2026-01-02", "2026-01-10"],
        }
    )

    resultado = _executar_motor(previsoes, _seguranca(), _estoque(), pedidos)

    assert resultado.loc[0, "compra_recomendada"] == 25
    assert "pedidos confirmados: 4" in resultado.loc[0, "justificativa"]


def test_nao_desconta_pedido_criado_depois_da_data_de_referencia():
    pedidos = pd.DataFrame(
        {
            "medicamento_id": ["med_a"],
            "pedido_id": ["futuro"],
            "quantidade": [100],
            "data_pedido": ["2026-01-01"],
            "data_prevista_entrega": ["2026-01-02"],
        }
    )

    resultado = _executar_motor(
        _previsoes((10, 10, 10)), _seguranca(), _estoque(), pedidos
    )

    assert resultado.loc[0, "compra_recomendada"] == 29


def test_rejeita_datas_inconsistentes_do_pedido():
    pedidos = pd.DataFrame(
        {
            "medicamento_id": ["med_a"],
            "quantidade": [1],
            "data_pedido": ["2026-01-03"],
            "data_prevista_entrega": ["2026-01-02"],
        }
    )

    with pytest.raises(ValueError, match="data_pedido"):
        _executar_motor(_previsoes((10, 10, 10)), _seguranca(), _estoque(), pedidos)


def test_ignora_estoque_posterior_ao_inicio_da_previsao():
    estoque = pd.DataFrame(
        {
            "medicamento_id": ["med_a", "med_a"],
            "data": ["2025-12-31", "2026-01-02"],
            "estoque_disponivel": [3, 100],
        }
    )

    resultado = _executar_motor(_previsoes(), _seguranca(), estoque, pd.DataFrame())

    assert resultado.loc[0, "compra_recomendada"] == 9


def test_rejeita_quando_nao_ha_estoque_ate_data_de_referencia():
    with pytest.raises(ValueError, match="data de referencia"):
        _executar_motor(
            _previsoes(),
            _seguranca(),
            _estoque().assign(data="2026-01-02"),
            pd.DataFrame(),
        )


@pytest.mark.parametrize("campo", ["data_previsao", "data"])
@pytest.mark.parametrize("valor", ["data-invalida", None])
def test_rejeita_datas_invalidas_ou_ausentes(campo, valor):
    previsoes = _previsoes()
    estoque = _estoque()
    alvo = previsoes if campo == "data_previsao" else estoque
    alvo[campo] = pd.Series([valor], dtype=object)

    with pytest.raises(ValueError, match=campo):
        _executar_motor(previsoes, _seguranca(), estoque, pd.DataFrame())


def test_aceita_datas_com_timezone_sem_vazamento_temporal():
    previsoes = _previsoes().assign(
        data_previsao=[pd.Timestamp("2026-01-01", tz="America/Fortaleza")]
    )
    estoque = _estoque().assign(data=[pd.Timestamp("2025-12-31", tz="UTC")])

    resultado = _executar_motor(previsoes, _seguranca(), estoque, pd.DataFrame())

    assert resultado.loc[0, "compra_recomendada"] == 9


def test_elimina_residuo_numerico_proximo_de_zero():
    resultado = _executar_motor(
        _previsoes((0.1 + 0.2,)), _seguranca(0), _estoque(0.3), pd.DataFrame()
    )

    assert resultado.loc[0, "compra_recomendada"] == 0


def test_integracao_modelo_estoque_seguranca_e_motor():
    from src.features.pipeline import gerar_features
    from src.models.modelo_demanda import prever_demanda, treinar_modelo
    from src.recommendation.estoque_seguranca import calcular_estoque_seguranca

    historico = pd.DataFrame(
        {
            "data": pd.date_range("2025-10-01", periods=70),
            "medicamento_id": ["med_a"] * 70,
            "consumo_unidades": [10 + indice % 5 for indice in range(70)],
            "feriado": [False] * 70,
            "temperatura_media": [27.0] * 70,
            "chuva_mm": [0.0] * 70,
            "casos_dengue_regiao": [5.0] * 70,
        }
    )
    features = gerar_features(historico)
    modelo = treinar_modelo(features, n_estimators=5)
    corte = historico["data"].max()
    previsoes = prever_demanda(modelo, features, corte)
    referencia = pd.DataFrame({"medicamento_id": ["med_a"], "prazo_entrega_dias": [7]})
    seguranca = calcular_estoque_seguranca(historico, referencia)
    estoque = pd.DataFrame(
        {"medicamento_id": ["med_a"], "data": [corte], "estoque_disponivel": [20]}
    )

    resultado = _executar_motor(previsoes, seguranca, estoque, pd.DataFrame())

    assert list(resultado.columns) == COLUNAS_SAIDA
    assert resultado.loc[0, "medicamento_id"] == "med_a"
    assert resultado.loc[0, "compra_recomendada"] >= 0


@pytest.mark.parametrize("entrada", ["previsoes", "seguranca", "estoque", "pedidos"])
@pytest.mark.parametrize("identificador", [1, True, " med_a", "med_a "])
def test_rejeita_identificadores_fora_do_contrato(entrada, identificador):
    entradas = {
        "previsoes": _previsoes(),
        "seguranca": _seguranca(),
        "estoque": _estoque(),
        "pedidos": _pedidos((1,)),
    }
    entradas[entrada]["medicamento_id"] = [identificador]

    with pytest.raises((TypeError, ValueError), match="medicamento_id"):
        _executar_motor(
            entradas["previsoes"],
            entradas["seguranca"],
            entradas["estoque"],
            entradas["pedidos"],
        )


def test_rejeita_horizontes_diferentes_entre_medicamentos():
    previsoes = pd.concat(
        [
            _previsoes((10, 10), "med_a"),
            _previsoes((20,), "med_b"),
        ]
    )
    seguranca = pd.concat(
        [_seguranca(medicamento="med_a"), _seguranca(medicamento="med_b")]
    )
    estoque = pd.concat([_estoque(medicamento="med_a"), _estoque(medicamento="med_b")])

    with pytest.raises(ValueError, match="mesmas datas de horizonte"):
        _executar_motor(previsoes, seguranca, estoque, pd.DataFrame())


def test_rejeita_overflow_na_agregacao_de_demanda_e_pedidos():
    with pytest.raises(ValueError, match="demanda agregada"):
        _executar_motor(
            _previsoes((1e308, 1e308)), _seguranca(0), _estoque(0), pd.DataFrame()
        )

    with pytest.raises(ValueError, match="pedidos agregados"):
        _executar_motor(
            _previsoes((10,)), _seguranca(), _estoque(), _pedidos((1e308, 1e308))
        )


def test_filtra_pedido_futuro_mesmo_sem_data_prevista_entrega():
    pedidos = pd.DataFrame(
        {
            "medicamento_id": ["med_a"],
            "quantidade": [100],
            "data_pedido": ["2026-01-01"],
        }
    )

    resultado = _executar_motor(_previsoes(), _seguranca(), _estoque(), pedidos)

    assert resultado.loc[0, "compra_recomendada"] == 9


@pytest.mark.parametrize("campo", ["data_previsao", "data"])
@pytest.mark.parametrize("valor", [True, 0, 1.5])
def test_rejeita_numero_ou_booleano_como_data(campo, valor):
    previsoes = _previsoes()
    estoque = _estoque()
    alvo = previsoes if campo == "data_previsao" else estoque
    alvo[campo] = pd.Series([valor], dtype=object)

    with pytest.raises(TypeError, match=campo):
        _executar_motor(previsoes, _seguranca(), estoque, pd.DataFrame())


def test_calculo_vetorizado_em_escala_preserva_grupos_e_fronteiras_temporais():
    rng = np.random.default_rng(20260812)
    medicamentos = [f"med_{indice:02d}" for indice in range(30)]
    datas_previsao = pd.date_range("2026-02-01", periods=7)
    linhas_previsao = []
    linhas_seguranca = []
    linhas_estoque = []
    linhas_pedidos = []
    esperados = {}

    for medicamento in medicamentos:
        demandas = rng.uniform(0, 50, size=7)
        seguranca = float(rng.uniform(0, 20))
        estoque_atual = float(rng.uniform(0, 100))
        pedidos_no_horizonte = rng.uniform(0, 15, size=2)
        for data, demanda in zip(datas_previsao, demandas, strict=True):
            linhas_previsao.append((medicamento, data, demanda))
        linhas_seguranca.append((medicamento, seguranca))
        linhas_estoque.extend(
            [
                (medicamento, "2026-01-30", estoque_atual + 10),
                (medicamento, "2026-01-31", estoque_atual),
                (medicamento, "2026-02-02", 9999),
            ]
        )
        linhas_pedidos.extend(
            [
                (
                    medicamento,
                    f"{medicamento}-1",
                    pedidos_no_horizonte[0],
                    "2026-02-02",
                ),
                (
                    medicamento,
                    f"{medicamento}-2",
                    pedidos_no_horizonte[1],
                    "2026-02-07",
                ),
                (medicamento, f"{medicamento}-3", 9999, "2026-02-08"),
            ]
        )
        esperados[medicamento] = max(
            demandas.sum() + seguranca - estoque_atual - pedidos_no_horizonte.sum(), 0
        )

    previsoes = pd.DataFrame(
        linhas_previsao,
        columns=["medicamento_id", "data_previsao", "demanda_prevista"],
    )
    segurancas = pd.DataFrame(
        linhas_seguranca, columns=["medicamento_id", "estoque_seguranca"]
    )
    estoques = pd.DataFrame(
        linhas_estoque, columns=["medicamento_id", "data", "estoque_disponivel"]
    )
    pedidos = pd.DataFrame(
        linhas_pedidos,
        columns=["medicamento_id", "pedido_id", "quantidade", "data_prevista_entrega"],
    )

    resultado = _executar_motor(previsoes, segurancas, estoques, pedidos).set_index(
        "medicamento_id"
    )

    assert len(resultado) == len(medicamentos)
    for medicamento, esperado in esperados.items():
        assert resultado.loc[medicamento, "compra_recomendada"] == pytest.approx(
            esperado
        )
