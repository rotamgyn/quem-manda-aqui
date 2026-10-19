"""Comparação 2022 × 2026 por partido: deltas, volatilidade de Pedersen e virada."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .modelo import Cargo, Resultado

# <raiz do repositório>/dados-comuns/partidos-equivalencias.csv
EQUIVALENCIAS_PADRAO = (
    Path(__file__).resolve().parents[5] / "dados-comuns" / "partidos-equivalencias.csv"
)


@dataclass(frozen=True)
class LinhaPartido:
    partido: str
    pct_2022: float | None
    pct_2026: float | None
    delta_pp: float | None
    # Siglas originais de 2022 somadas nesta linha (ex.: PRD ← PATRIOTA + PTB); () sem 2022.
    siglas_2022: tuple[str, ...] = ()


@dataclass(frozen=True)
class Comparacao:
    cargo: Cargo
    uf: str
    municipio_tse: str | None
    r2022: Resultado | None
    r2026: Resultado | None
    partidos: tuple[LinhaPartido, ...]
    volatilidade: float | None
    vencedor_2022: str | None
    vencedor_2026: str | None
    virou: bool | None
    apuracao_completa: bool


def carregar_equivalencias(caminho: Path | str = EQUIVALENCIAS_PADRAO) -> dict[str, str]:
    """Lê o CSV `sigla_origem,sigla_destino,nota` (UTF-8): sigla 2022 → sigla atual."""
    with open(caminho, encoding="utf-8", newline="") as f:
        return {
            linha["sigla_origem"].strip(): linha["sigla_destino"].strip()
            for linha in csv.DictReader(f)
        }


def _votos_por_partido(r: Resultado | None, equiv: dict[str, str]) -> dict[str, int]:
    votos: dict[str, int] = defaultdict(int)
    if r is not None:
        for c in r.candidatos:
            votos[equiv.get(c.partido, c.partido)] += c.votos
    return votos


def _siglas_por_partido(r: Resultado | None, equiv: dict[str, str]) -> dict[str, tuple[str, ...]]:
    siglas: dict[str, set[str]] = defaultdict(set)
    if r is not None:
        for c in r.candidatos:
            siglas[equiv.get(c.partido, c.partido)].add(c.partido)
    return {p: tuple(sorted(s)) for p, s in siglas.items()}


def _percentuais(r: Resultado | None, votos: dict[str, int]) -> dict[str, float] | None:
    """None quando não há resultado ou não há votos válidos."""
    if r is None or r.validos == 0:
        return None
    return {p: v / r.validos * 100 for p, v in votos.items()}


def _vencedor(votos: dict[str, int], pcts: dict[str, float] | None) -> str | None:
    """Partido com mais votos; empate no topo ou sem votos → None."""
    if pcts is None or not votos:
        return None
    ordem = sorted(votos.items(), key=lambda x: -x[1])
    if ordem[0][1] <= 0 or (len(ordem) > 1 and ordem[1][1] == ordem[0][1]):
        return None
    return ordem[0][0]


def comparar(
    r2022: Resultado | None, r2026: Resultado | None, equivalencias: dict[str, str]
) -> Comparacao:
    base = r2026 or r2022
    if base is None:
        raise ValueError("comparar exige ao menos um resultado (2022 ou 2026)")

    v22 = _votos_por_partido(r2022, equivalencias)
    v26 = _votos_por_partido(r2026, {})
    p22 = _percentuais(r2022, v22)
    p26 = _percentuais(r2026, v26)
    s22 = _siglas_por_partido(r2022, equivalencias)

    linhas = []
    for partido in set(v22) | set(v26):
        a = p22.get(partido) if p22 else None
        b = p26.get(partido) if p26 else None
        delta = b - a if a is not None and b is not None else None
        linhas.append(LinhaPartido(partido, a, b, delta, s22.get(partido, ())))
    linhas.sort(
        key=lambda l: (l.pct_2026 is None, -(l.pct_2026 or 0), -(l.pct_2022 or 0), l.partido)
    )

    volatilidade = None
    if p22 is not None and p26 is not None:
        volatilidade = 0.5 * sum(
            abs(p26.get(p, 0.0) - p22.get(p, 0.0)) for p in set(p22) | set(p26)
        )

    ven22 = _vencedor(v22, p22)
    ven26 = _vencedor(v26, p26)
    virou = None if ven22 is None or ven26 is None else ven22 != ven26

    return Comparacao(
        cargo=base.cargo,
        uf=base.uf,
        municipio_tse=base.municipio_tse,
        r2022=r2022,
        r2026=r2026,
        partidos=tuple(linhas),
        volatilidade=volatilidade,
        vencedor_2022=ven22,
        vencedor_2026=ven26,
        virou=virou,
        apuracao_completa=r2026 is not None and r2026.pct_secoes_totalizadas >= 100,
    )
