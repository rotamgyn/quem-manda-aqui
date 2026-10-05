"""Leitor dos CSVs de resultado por município/zona do TSE (eleição de 2022)."""

from __future__ import annotations

import zipfile
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from qma_comum.http import baixar

from .config import CODIGO_CARGO
from .modelo import Cargo, Resultado, Situacao, VotoCandidato

BASE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele"
URL_VOTACAO = f"{BASE_URL}/votacao_candidato_munzona/votacao_candidato_munzona_2022.zip"
URL_DETALHE = f"{BASE_URL}/detalhe_votacao_munzona/detalhe_votacao_munzona_2022.zip"
PASTA_2022 = Path(".cache") / "2022"

_COLS_VOTACAO = [
    "NR_TURNO", "SG_UF", "CD_MUNICIPIO", "CD_CARGO", "NR_CANDIDATO",
    "NM_URNA_CANDIDATO", "SG_PARTIDO", "QT_VOTOS_NOMINAIS_VALIDOS", "DS_SIT_TOT_TURNO",
]  # fmt: skip
_COLS_DETALHE = [
    "NR_TURNO", "SG_UF", "CD_MUNICIPIO", "CD_CARGO", "QT_APTOS", "QT_COMPARECIMENTO",
    "QT_ABSTENCOES", "QT_VOTOS_BRANCOS", "QT_TOTAL_VOTOS_NULOS", "QT_TOTAL_VOTOS_VALIDOS",
]  # fmt: skip
_CARGO_POR_CODIGO: dict[int, Cargo] = {v: k for k, v in CODIGO_CARGO.items()}
_SITUACAO: dict[str, Situacao] = {
    "ELEITO": "eleito",
    "2º TURNO": "2º turno",
    "NÃO ELEITO": "não eleito",
}
_SOMAVEIS = [
    "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES", "QT_VOTOS_BRANCOS",
    "QT_TOTAL_VOTOS_NULOS", "QT_TOTAL_VOTOS_VALIDOS",
]  # fmt: skip
_CHUNK = 500_000


def _ler(csv: Path, colunas: list[str], turno: int) -> Iterable[pd.DataFrame]:
    """Lê em blocos só presidente/governador do turno pedido."""
    blocos = pd.read_csv(
        csv, sep=";", encoding="latin-1", usecols=colunas,
        dtype={"CD_MUNICIPIO": str}, chunksize=_CHUNK,
    )  # fmt: skip
    for bloco in blocos:
        bloco = bloco[bloco["CD_CARGO"].isin(_CARGO_POR_CODIGO) & (bloco["NR_TURNO"] == turno)]
        if not bloco.empty:
            yield bloco.assign(CD_MUNICIPIO=bloco["CD_MUNICIPIO"].str.zfill(5))


def _concat(csvs: Iterable[Path], colunas: list[str], turno: int) -> pd.DataFrame:
    partes = [b for csv in csvs for b in _ler(Path(csv), colunas, turno)]
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame(columns=colunas)


def _situacao(texto: str) -> Situacao:
    return _SITUACAO.get(str(texto).strip().upper(), "")


def _agregar(
    vot: pd.DataFrame,
    det: pd.DataFrame,
    cands: dict[tuple[int, str, int], tuple[str, str, str]],
    turno: int,
    chaves: list[str],
    cargos: tuple[int, ...],
) -> list[Resultado]:
    """Soma zonas/linhas por `chaves` e monta um `Resultado` por grupo."""
    det_g = det[det["CD_CARGO"].isin(cargos)].groupby(chaves)[_SOMAVEIS].sum()
    vot_g = vot[vot["CD_CARGO"].isin(cargos)].groupby([*chaves, "NR_CANDIDATO"])["VOTOS"].sum()
    por_grupo: dict[tuple, list[tuple[int, int]]] = {}
    for chave, votos in vot_g.items():
        por_grupo.setdefault(chave[:-1], []).append((int(chave[-1]), int(votos)))

    resultados = []
    for chave, d in det_g.iterrows():
        chave = chave if isinstance(chave, tuple) else (chave,)
        campos = dict(zip(chaves, chave))
        cod = int(campos["CD_CARGO"])
        uf = campos.get("SG_UF", "BR")
        # Presidente: candidatos são nacionais; governador: valem dentro da UF.
        escopo = "BR" if cod == CODIGO_CARGO["presidente"] else uf
        candidatos = []
        for numero, votos in por_grupo.get(chave, []):
            nome, partido, sit = cands[(cod, escopo, numero)]
            candidatos.append(VotoCandidato(numero, nome, partido, votos, _situacao(sit)))
        candidatos.sort(key=lambda c: (-c.votos, c.numero))
        resultados.append(
            Resultado(
                ano=2022, turno=turno, cargo=_CARGO_POR_CODIGO[cod], uf=uf,
                municipio_tse=campos.get("CD_MUNICIPIO"),
                aptos=int(d["QT_APTOS"]), comparecimento=int(d["QT_COMPARECIMENTO"]),
                abstencao=int(d["QT_ABSTENCOES"]), brancos=int(d["QT_VOTOS_BRANCOS"]),
                nulos=int(d["QT_TOTAL_VOTOS_NULOS"]), validos=int(d["QT_TOTAL_VOTOS_VALIDOS"]),
                pct_secoes_totalizadas=100.0, candidatos=tuple(candidatos),
            )
        )  # fmt: skip
    return resultados


def ler_2022(
    votacao_csvs: Iterable[Path], detalhe_csvs: Iterable[Path], *, turno: int
) -> list[Resultado]:
    """Um `Resultado` por (cargo, UF, município), mais agregados por UF e Brasil.

    Presidente vem só do `_BR.csv` e governador só dos arquivos por UF: esses arquivos
    não repetem cargos entre si. NÃO passe o `_BRASIL.csv` (todos os cargos juntos,
    4,3 GB), que duplicaria tudo. Soma todas as zonas e linhas de voto em trânsito.
    """
    vot = _concat(votacao_csvs, _COLS_VOTACAO, turno)
    det = _concat(detalhe_csvs, _COLS_DETALHE, turno)
    vot = vot.rename(columns={"QT_VOTOS_NOMINAIS_VALIDOS": "VOTOS"})

    pres, gov = CODIGO_CARGO["presidente"], CODIGO_CARGO["governador"]
    escopo = vot["SG_UF"].where(vot["CD_CARGO"] == gov, "BR")
    unicos = vot.assign(ESC=escopo).drop_duplicates(["CD_CARGO", "ESC", "NR_CANDIDATO"])
    cands = {
        (int(c), e, int(n)): (nome, partido, sit)
        for c, e, n, nome, partido, sit in zip(
            unicos["CD_CARGO"], unicos["ESC"], unicos["NR_CANDIDATO"],
            unicos["NM_URNA_CANDIDATO"], unicos["SG_PARTIDO"], unicos["DS_SIT_TOT_TURNO"],
        )
    }  # fmt: skip

    def agregar(chaves: list[str], cargos: tuple[int, ...]) -> list[Resultado]:
        return _agregar(vot, det, cands, turno, chaves, cargos)

    return [
        *agregar(["CD_CARGO", "SG_UF", "CD_MUNICIPIO"], (pres, gov)),
        *agregar(["CD_CARGO", "SG_UF"], (pres, gov)),
        *agregar(["CD_CARGO"], (pres,)),
    ]


def _extrair(zip_path: Path, destino: Path) -> list[Path]:
    """Extrai os CSVs do zip (menos o `_BRASIL.csv`, que repete todos os outros)."""
    destino.mkdir(parents=True, exist_ok=True)
    csvs = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if not info.filename.lower().endswith(".csv") or info.filename.endswith("_BRASIL.csv"):
                continue
            alvo = destino / info.filename
            if not alvo.exists() or alvo.stat().st_size != info.file_size:
                zf.extract(info, destino)
            csvs.append(alvo)
    return sorted(csvs)


def arquivos_2022() -> tuple[list[Path], list[Path]]:
    """Baixa (com cache) e extrai os zips de 2022; devolve (votação, detalhe)."""
    votacao = _extrair(baixar(URL_VOTACAO), PASTA_2022)
    detalhe = _extrair(baixar(URL_DETALHE), PASTA_2022)
    return votacao, detalhe
