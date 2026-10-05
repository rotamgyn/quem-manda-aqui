"""Tabela de municípios: código TSE, código IBGE, UF e slug de URL."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from pathlib import Path

TOTAL_MUNICIPIOS_BRASIL = 5571


class ErroUniverso(Exception):
    """O conjunto de municípios não bate com o universo esperado."""


@dataclass(frozen=True)
class Municipio:
    tse: str
    ibge: str | None
    nome: str
    uf: str
    capital: bool
    slug: str


def ler_config_municipios(dados: dict) -> list[Municipio]:
    """Lê o formato `abr[].mu[]` de `config/mun-e006257-cm.json`."""
    resultado = []
    for uf in dados["abr"]:
        for mu in uf["mu"]:
            resultado.append(
                Municipio(
                    tse=mu["cd"],
                    ibge=mu.get("cdi") or None,
                    nome=mu["nm"],
                    uf=uf["cd"].upper(),
                    capital=mu.get("c") == "s",
                    slug="",
                )
            )
    return resultado


def slugificar(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    sem_apostrofo = re.sub(r"['’`´]", "", sem_acento.lower())
    return re.sub(r"[^a-z0-9]+", "-", sem_apostrofo).strip("-")


def atribuir_slugs(municipios: Iterable[Municipio]) -> list[Municipio]:
    """Devolve novos Municipio com slug único por UF.

    Em homônimos, o de menor código TSE fica com o slug simples e os demais
    recebem o sufixo `-{tse}` (independe da ordem de entrada).
    """
    municipios = list(municipios)
    slugs: dict[int, str] = {}
    usados: set[tuple[str, str]] = set()
    for i in sorted(range(len(municipios)), key=lambda i: municipios[i].tse):
        m = municipios[i]
        slug = slugificar(m.nome)
        if (m.uf, slug) in usados:
            slug = f"{slug}-{m.tse}"
        usados.add((m.uf, slug))
        slugs[i] = slug
    return [replace(m, slug=slugs[i]) for i, m in enumerate(municipios)]


def gravar_municipios(
    municipios: Iterable[Municipio], destino: Path = Path("dados/comum/municipios.json")
) -> None:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps([asdict(m) for m in municipios], ensure_ascii=False, indent=1)
    destino.write_text(texto + "\n", encoding="utf-8")


def validar_universo(municipios: Iterable[Municipio]) -> None:
    brasil = [m for m in municipios if m.uf != "ZZ"]
    if len(brasil) != TOTAL_MUNICIPIOS_BRASIL:
        raise ErroUniverso(
            f"esperados {TOTAL_MUNICIPIOS_BRASIL} municípios, encontrados {len(brasil)}"
        )
    sem_ibge = [m.tse for m in brasil if not m.ibge]
    if sem_ibge:
        raise ErroUniverso(f"{len(sem_ibge)} municípios sem código IBGE: {sem_ibge[:5]}")
    vistos: set[str] = set()
    duplicados = sorted({m.ibge for m in brasil if m.ibge in vistos or vistos.add(m.ibge)})
    if duplicados:
        raise ErroUniverso(f"códigos IBGE duplicados: {duplicados[:5]}")
