"""Constantes e URLs do TSE para as eleições de 2026."""

from __future__ import annotations

from .modelo import Cargo

BASE_2026 = "https://resultados.tse.jus.br/oficial/ele2026"
ELEICAO_2026_T1 = {"presidente": "6257", "governador": "6259"}
ELEICAO_2026_T2 = {"presidente": "6258", "governador": "6260"}
CODIGO_CARGO = {"presidente": 1, "governador": 3}
URL_CONFIG_GOVERNADOR_T2 = f"{BASE_2026}/6260/config/mun-e006260-cm.json"


def url_andamento_2026(eleicao: str) -> str:
    """URL do arquivo de andamento (`-ab.json`) por abrangência."""
    return f"{BASE_2026}/{eleicao}/dados/br/br-e{int(eleicao):06d}-ab.json"


def url_resultado_2026(
    cargo: Cargo, uf: str, municipio_tse: str | None = None, eleicao: str | None = None
) -> str:
    """URL do arquivo de resultado; `uf="br"` para o total nacional.

    `eleicao` padrão = 1º turno; use `ELEICAO_2026_T2[cargo]` para o 2º turno.
    """
    ele = eleicao or ELEICAO_2026_T1[cargo]
    uf = uf.lower()
    mun = municipio_tse or ""
    return (
        f"{BASE_2026}/{ele}/dados/{uf}/{uf}{mun}"
        f"-c{CODIGO_CARGO[cargo]:04d}-e{int(ele):06d}-u.json"
    )
