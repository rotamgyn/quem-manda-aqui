"""Constantes e URLs do TSE para as eleições de 2026."""

from __future__ import annotations

from .modelo import Cargo

BASE_2026 = "https://resultados.tse.jus.br/oficial/ele2026"
ELEICAO_2026_T1 = {"presidente": "6257", "governador": "6259"}
CODIGO_CARGO = {"presidente": 1, "governador": 3}


def url_resultado_2026(cargo: Cargo, uf: str, municipio_tse: str | None = None) -> str:
    """URL do arquivo de resultado; `uf="br"` para o total nacional."""
    ele = ELEICAO_2026_T1[cargo]
    uf = uf.lower()
    mun = municipio_tse or ""
    return (
        f"{BASE_2026}/{ele}/dados/{uf}/{uf}{mun}"
        f"-c{CODIGO_CARGO[cargo]:04d}-e{int(ele):06d}-u.json"
    )
