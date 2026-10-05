"""Coleta dos resultados de 2026 (1º turno): Brasil, UFs e municípios."""

from __future__ import annotations

import logging
from collections.abc import Callable

from qma_comum.http import ErroDownload, baixar_json
from qma_comum.municipios import Municipio

from .config import url_resultado_2026
from .leitor_2026 import ler_resultado_2026
from .modelo import Cargo, Resultado

log = logging.getLogger("qma_eleicoes.coleta")

CARGOS: tuple[Cargo, ...] = ("presidente", "governador")
EXTERIOR = "ZZ"
PROGRESSO_A_CADA = 500


def coletar_2026(
    municipios: list[Municipio],
    *,
    forcar: bool = False,
    _baixar: Callable = baixar_json,
) -> list[Resultado]:
    """Baixa e lê todos os arquivos de resultado.

    Ordem: BR, UFs, municípios. Presidente: BR, cada UF (inclusive ZZ) e cada município (inclusive exterior).
    Governador: cada UF e município, exceto o exterior. 404 num município gera
    aviso; 404 em BR/UF propaga `ErroDownload`.
    """
    ordenados = sorted(municipios, key=lambda m: (m.uf, m.tse))
    ufs = sorted({m.uf for m in ordenados})
    resultados: list[Resultado] = []
    baixados = 0

    def obter(url: str) -> dict:
        nonlocal baixados
        dados = _baixar(url, forcar=forcar)
        baixados += 1
        if baixados % PROGRESSO_A_CADA == 0:
            log.info("%d arquivos processados", baixados)
        return dados

    def ufs_do(cargo: Cargo) -> list[str]:
        return [u for u in ufs if cargo == "presidente" or u != EXTERIOR]

    resultados.append(
        ler_resultado_2026(obter(url_resultado_2026("presidente", "br")), "presidente")
    )
    for cargo in CARGOS:
        for uf in ufs_do(cargo):
            resultados.append(
                ler_resultado_2026(obter(url_resultado_2026(cargo, uf)), cargo)
            )
    for cargo in CARGOS:
        incluir = set(ufs_do(cargo))
        for m in ordenados:
            if m.uf not in incluir:
                continue
            url = url_resultado_2026(cargo, m.uf, m.tse)
            try:
                dados = obter(url)
            except ErroDownload as e:
                if e.status != 404:
                    raise
                log.warning("arquivo inexistente (404), ignorado: %s", url)
                continue
            resultados.append(ler_resultado_2026(dados, cargo, uf=m.uf))
    return resultados
