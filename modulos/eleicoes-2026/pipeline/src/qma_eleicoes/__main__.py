"""CLI do pipeline: `python -m qma_eleicoes gerar [--forcar]`."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from pathlib import Path

from qma_comum.http import baixar_json
from qma_comum.malhas import baixar_malhas
from qma_comum.municipios import (
    Municipio,
    atribuir_slugs,
    gravar_municipios,
    ler_config_municipios,
    validar_universo,
)

from .coleta_2026 import CARGOS, EXTERIOR, coletar_2026
from .comparacao import carregar_equivalencias
from .conferencia import ErroConferencia, conferir
from .config import url_resultado_2026
from .exportar import exportar, meta_de, nomes_ufs
from .leitor_2022 import arquivos_2022, ler_2022
from .modelo import Resultado

log = logging.getLogger("qma_eleicoes")

URL_CONFIG_MUNICIPIOS = "https://resultados.tse.jus.br/oficial/ele2026/6257/config/mun-e006257-cm.json"
OFICIAL_2022_PRESIDENTE_BR = {13: 57_259_504, 22: 51_072_345}  # Lula, Bolsonaro (1º turno)


def _n(v: int) -> str:
    return f"{v:,}".replace(",", ".")


def verificar_totais_2022(r2022: list[Resultado]) -> None:
    """Totais oficiais conhecidos do presidente 2022 (BR, 1º turno)."""
    br = next(
        (r for r in r2022 if r.cargo == "presidente" and r.uf == "BR" and r.municipio_tse is None),
        None,
    )
    if br is None:
        raise ErroConferencia(["2022 presidente BR: resultado nacional ausente"])
    votos = {c.numero: c.votos for c in br.candidatos}
    div = [
        f"2022 presidente BR candidato {n}: lido={_n(votos.get(n, 0))} oficial={_n(ref)}"
        for n, ref in OFICIAL_2022_PRESIDENTE_BR.items()
        if votos.get(n, 0) != ref
    ]
    if div:
        raise ErroConferencia(div)


def verificar_cobertura_2026(municipios: list[Municipio], r2026: list[Resultado]) -> None:
    """Todo município brasileiro precisa ter os cargos esperados."""
    tem = {(r.cargo, r.uf, r.municipio_tse) for r in r2026}
    faltam = [
        f"2026 {cargo} {m.uf} {m.tse} {m.nome}"
        for cargo in CARGOS
        for m in sorted(municipios, key=lambda m: (m.uf, m.tse))
        if m.uf != EXTERIOR and (cargo, m.uf, m.tse) not in tem
    ]
    if faltam:
        raise ErroConferencia(
            [f"{len(faltam)} município(s) sem resultado de 2026 (arquivo ausente):", *faltam[:50]]
        )


def gerar(
    forcar: bool = False,
    raiz: Path = Path("dados"),
    *,
    _baixar_json: Callable = baixar_json,
    _malhas: Callable = baixar_malhas,
    _arquivos_2022: Callable = arquivos_2022,
    _ler_2022: Callable = ler_2022,
    _coletar: Callable = coletar_2026,
    _equivalencias: Callable = carregar_equivalencias,
) -> None:
    raiz = Path(raiz)
    log.info("municípios")
    config = _baixar_json(URL_CONFIG_MUNICIPIOS, forcar=forcar)
    municipios = atribuir_slugs(ler_config_municipios(config))
    validar_universo(municipios)
    gravar_municipios(municipios, raiz / "comum" / "municipios.json")

    log.info("malhas")
    ufs = sorted({m.uf for m in municipios if m.uf != EXTERIOR})
    _malhas(ufs, raiz / "comum" / "malhas")

    log.info("2022 (1º turno)")
    votacao, detalhe = _arquivos_2022()
    r2022 = _ler_2022(votacao, detalhe, turno=1)

    log.info("2026 (1º turno)")
    r2026 = _coletar(municipios, forcar=forcar)

    log.info("conferência")
    verificar_totais_2022(r2022)
    verificar_cobertura_2026(municipios, r2026)
    conferir(r2022)
    conferir(r2026)

    log.info("exportação")
    br = next(r for r in r2026 if r.uf == "BR" and r.cargo == "presidente")
    arquivo_br = _baixar_json(url_resultado_2026("presidente", "br"))
    meta = meta_de(arquivo_br, br)
    exportar(
        municipios, nomes_ufs(config), r2022, r2026, _equivalencias(), meta,
        raiz / "eleicoes-2026",
    )  # fmt: skip
    esperados = sum(1 for m in municipios if m.uf != EXTERIOR) * len(CARGOS)
    log.info(
        "concluído: %d arquivos municipais de 2026 esperados, 0 ausentes (meta: %s)",
        esperados, meta,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="qma_eleicoes")
    sub = parser.add_subparsers(dest="comando", required=True)
    g = sub.add_parser("gerar", help="gera os JSON de dados/eleicoes-2026")
    g.add_argument("--forcar", action="store_true", help="ignora o cache dos arquivos de 2026")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        gerar(forcar=args.forcar)
    except ErroConferencia as e:
        log.error("conferência falhou; nada foi escrito em dados/eleicoes-2026:\n%s", "\n".join(e.divergencias[:30]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
