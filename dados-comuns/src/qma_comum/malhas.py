"""Malhas do IBGE (TopoJSON) para os mapas: Brasil por UF e cada UF por município."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

from .http import baixar

BASE_IBGE = "https://servicodados.ibge.gov.br/api/v3/malhas"
_PARAMETROS = "formato=application/json&qualidade=minima"
URL_BRASIL_POR_UF = f"{BASE_IBGE}/paises/BR?{_PARAMETROS}&intrarregiao=UF"


def url_malha_uf(uf: str) -> str:
    return f"{BASE_IBGE}/estados/{uf.upper()}?{_PARAMETROS}&intrarregiao=municipio"


def baixar_malhas(
    ufs: list[str],
    destino: Path = Path("dados/comum/malhas"),
    *,
    _baixar: Callable[..., Path] = baixar,
) -> list[Path]:
    """Grava `br-uf.json` e `{uf}.json` (minúsculas) em `destino`; devolve os caminhos."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    pedidos = [(URL_BRASIL_POR_UF, "br-uf.json")]
    pedidos += [(url_malha_uf(uf), f"{uf.lower()}.json") for uf in ufs]
    gravados = []
    for url, nome in pedidos:
        alvo = destino / nome
        shutil.copyfile(_baixar(url), alvo)
        gravados.append(alvo)
    return gravados
