"""Executa e valida o pipeline completo do MVP (Issue #25).

O fluxo padrão reconstrói os dados desde as fontes externas, gera o dataset
sintético consolidado, treina e serializa o modelo oficial e, por fim, usa o
artefato recarregado para produzir os dados consumidos pelo dashboard.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from dashboard.app import gerar_dados_painel
from src.features.pipeline import gerar_features
from src.models.artefato import CAMINHO_MODELO_PADRAO, carregar_modelo, salvar_modelo
from src.models.modelo_demanda import treinar_modelo


SCRIPTS_COLETA = [
    REPO / "src" / "data_ingestion" / "ingestao_calendario.py",
    REPO / "src" / "data_ingestion" / "ingestao_clima.py",
    REPO / "src" / "data_ingestion" / "ingestao_epidemiologia.py",
]
SCRIPTS_DADOS = [
    REPO / "src" / "data_ingestion" / "gerar_dataset_sintetico.py",
    REPO / "src" / "data_ingestion" / "consolidar_dataset.py",
]
ARQUIVOS_EXTERNOS = [
    REPO / "data" / "external" / "calendario.csv",
    REPO / "data" / "external" / "clima.csv",
    REPO / "data" / "external" / "epidemiologia.csv",
]
ARQUIVO_CONSUMO = REPO / "data" / "processed" / "consumo_medicamentos.csv"
ARQUIVO_MEDICAMENTOS = REPO / "data" / "processed" / "medicamentos_ref.csv"
ARQUIVO_PEDIDOS = REPO / "data" / "processed" / "pedidos_pendentes.csv"
ARQUIVO_LOTES = REPO / "data" / "processed" / "lotes.csv"


def _executar_script(caminho: Path) -> None:
    """Executa uma etapa no mesmo Python do orquestrador e propaga falhas."""
    print(f"\n[PIPELINE] Executando {caminho.relative_to(REPO)}", flush=True)
    subprocess.run([sys.executable, str(caminho)], cwd=REPO, check=True)


def _validar_arquivos(caminhos: list[Path], contexto: str) -> None:
    ausentes = [
        str(caminho.relative_to(REPO))
        for caminho in caminhos
        if not caminho.is_file()
    ]
    if ausentes:
        raise FileNotFoundError(
            f"Arquivos ausentes para {contexto}: {', '.join(ausentes)}."
        )


def executar_pipeline(
    *,
    coletar_externos: bool = True,
    atualizar_dados: bool = True,
    n_estimators: int = 500,
    caminho_modelo: Path = CAMINHO_MODELO_PADRAO,
) -> pd.DataFrame:
    """Executa dados -> features -> modelo -> recomendação -> dashboard."""
    if n_estimators < 1:
        raise ValueError("n_estimators deve ser maior ou igual a 1.")

    if atualizar_dados:
        if coletar_externos:
            for script in SCRIPTS_COLETA:
                _executar_script(script)
        else:
            _validar_arquivos(ARQUIVOS_EXTERNOS, "reutilizar a coleta externa")
            print("[PIPELINE] Coleta externa reutilizada dos CSVs existentes.", flush=True)
        for script in SCRIPTS_DADOS:
            _executar_script(script)

    arquivos_entrada = [
        ARQUIVO_CONSUMO,
        ARQUIVO_MEDICAMENTOS,
        ARQUIVO_PEDIDOS,
        ARQUIVO_LOTES,
    ]
    _validar_arquivos(arquivos_entrada, "treinar e gerar recomendações")

    print("\n[PIPELINE] Gerando features e treinando o modelo oficial", flush=True)
    consumo = pd.read_csv(ARQUIVO_CONSUMO)
    medicamentos = pd.read_csv(ARQUIVO_MEDICAMENTOS)
    pedidos = pd.read_csv(ARQUIVO_PEDIDOS)
    lotes = pd.read_csv(ARQUIVO_LOTES)
    features = gerar_features(consumo)
    modelo = treinar_modelo(features, n_estimators=n_estimators)
    salvar_modelo(modelo, caminho_modelo)

    # Recarregar em vez de reutilizar o objeto em memória valida a fronteira
    # que será percorrida pelo processo separado do Streamlit.
    modelo_recarregado = carregar_modelo(caminho_modelo)
    print(f"[PIPELINE] Artefato validado em {caminho_modelo}", flush=True)

    print(
        "[PIPELINE] Gerando recomendações e validando contrato do dashboard",
        flush=True,
    )
    dados_painel = gerar_dados_painel(
        consumo,
        medicamentos,
        pedidos,
        lotes,
        modelo=modelo_recarregado,
    )
    esperados = set(medicamentos["medicamento_id"])
    recebidos = set(dados_painel["medicamento_id"])
    if recebidos != esperados:
        raise ValueError("O dashboard não recebeu todos os medicamentos do cadastro.")

    print(
        "[PIPELINE] Sucesso: "
        f"{len(consumo):,} registros históricos, "
        f"{len(dados_painel)} medicamentos e "
        f"{int((dados_painel['compra_recomendada'] > 0).sum())} recomendações de compra.",
        flush=True,
    )
    return dados_painel


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa o pipeline completo do MVP.")
    parser.add_argument(
        "--sem-coleta-externa",
        action="store_true",
        help="Reutiliza os CSVs externos existentes, mas regenera os dados sintéticos.",
    )
    parser.add_argument(
        "--usar-dados-processados",
        action="store_true",
        help="Pula toda a geração de dados e usa os CSVs processados existentes.",
    )
    parser.add_argument(
        "--abrir-dashboard",
        action="store_true",
        help="Após validar o pipeline, inicia o servidor Streamlit.",
    )
    return parser.parse_args()


def main() -> None:
    args = _argumentos()
    executar_pipeline(
        coletar_externos=not args.sem_coleta_externa,
        atualizar_dados=not args.usar_dados_processados,
    )
    if args.abrir_dashboard:
        print("\n[PIPELINE] Abrindo dashboard em http://localhost:8501", flush=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(REPO / "dashboard" / "app.py"),
            ],
            cwd=REPO,
            check=True,
        )


if __name__ == "__main__":
    main()
