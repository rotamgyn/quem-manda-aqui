"""Base estática por município para o ao vivo: 2º turno de 2022 e 1º turno de 2026."""

from __future__ import annotations

from collections import defaultdict

from qma_comum.municipios import Municipio

from .modelo import Resultado

FAIXAS_PORTE = ((10_000, "ate10k"), (50_000, "10a50k"), (200_000, "50a200k"))  # as do site


def porte(aptos: int) -> str:
    return next((nome for limite, nome in FAIXAS_PORTE if aptos <= limite), "mais200k")


def _partidos(r: Resultado, equivalencias: dict[str, str]) -> dict[str, float]:
    if r.validos == 0:
        return {}
    votos: dict[str, int] = defaultdict(int)
    for c in r.candidatos:
        votos[equivalencias.get(c.partido, c.partido)] += c.votos
    return {p: round(v / r.validos * 100, 2) for p, v in votos.items()}


def _presidente_por_municipio(resultados: list[Resultado]) -> dict[tuple[str, str], Resultado]:
    return {
        (r.uf, r.municipio_tse): r
        for r in resultados
        if r.cargo == "presidente" and r.municipio_tse is not None
    }


def _agregado(r: Resultado, equivalencias: dict[str, str]) -> dict:
    """Votos válidos e votos/percentual por partido (equivalências aplicadas)."""
    votos: dict[str, int] = defaultdict(int)
    for c in r.candidatos:
        votos[equivalencias.get(c.partido, c.partido)] += c.votos
    return {
        "validos": r.validos,
        "votos": dict(votos),
        "partidos": _partidos(r, equivalencias),
    }


def agregados_2022_t2(r2022_t2: list[Resultado], equivalencias: dict[str, str]) -> dict:
    """Agregados de BR e UFs do 2º turno de 2022: presidente por BR/UF, governador por UF."""
    saida: dict[str, dict] = {"presidente": {}, "governador": {}}
    for r in sorted(r2022_t2, key=lambda r: r.uf):
        if r.municipio_tse is None and r.cargo in saida:
            saida[r.cargo][r.uf] = _agregado(r, equivalencias)
    return saida


def gerar_base(
    r2022_t2: list[Resultado],
    r2026_t1: list[Resultado],
    municipios: list[Municipio],
    equivalencias: dict[str, str] | None = None,
) -> dict:
    """Base por município (sem o exterior). 2022 ausente → `t2_2022: null`.

    Os partidos de 2022 passam pelas equivalências; os de 2026 ficam como vieram.
    """
    equivalencias = equivalencias or {}
    a22 = _presidente_por_municipio(r2022_t2)
    a26 = _presidente_por_municipio(r2026_t1)
    saida: dict[str, dict] = {}
    for m in sorted(municipios, key=lambda m: (m.uf, m.tse)):
        if m.uf == "ZZ":
            continue
        r26 = a26.get((m.uf, m.tse))
        r22 = a22.get((m.uf, m.tse))
        aptos = r26.aptos if r26 else 0
        saida[m.tse] = {
            "uf": m.uf,
            "ibge": m.ibge,
            "nome": m.nome,
            "slug": m.slug,
            "porte": porte(aptos),
            "aptos_2026": aptos,
            "t1_2026": (
                {
                    "comparecimento": r26.comparecimento,
                    "validos": r26.validos,
                    "partidos": _partidos(r26, {}),
                }
                if r26
                else None
            ),
            "t2_2022": (
                {"validos": r22.validos, "partidos": _partidos(r22, equivalencias)}
                if r22
                else None
            ),
        }
    return {
        "municipios": saida,
        "agregados_2022_t2": agregados_2022_t2(r2022_t2, equivalencias),
    }
