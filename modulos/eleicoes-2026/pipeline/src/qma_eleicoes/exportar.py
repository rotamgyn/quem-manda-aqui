"""Exportação JSON: contrato de dados lido pelo site e pelos planos seguintes."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from qma_comum.municipios import Municipio

from .comparacao import Comparacao, comparar
from .modelo import Cargo, Resultado

EXTERIOR = "ZZ"
FUSO = ZoneInfo("America/Sao_Paulo")


def _arred(x: float | None) -> float | None:
    return None if x is None else round(x, 2)


def _resultado(r: Resultado | None) -> dict | None:
    if r is None:
        return None
    d = asdict(r)
    for dc, c in zip(d["candidatos"], r.candidatos):
        dc["pct"] = _arred(r.pct(c))
    d["pct_secoes_totalizadas"] = _arred(r.pct_secoes_totalizadas)
    return d


def serializar(c: Comparacao, nome: str | None = None) -> dict:
    """`Comparacao` → dict do contrato (com `pct` nos candidatos e valores a 2 casas)."""
    d = asdict(c)
    d["r2022"] = _resultado(c.r2022)
    d["r2026"] = _resultado(c.r2026)
    for p in d["partidos"]:
        for k in ("pct_2022", "pct_2026", "delta_pp"):
            p[k] = _arred(p[k])
    d["volatilidade"] = _arred(c.volatilidade)
    if nome is not None:
        d["nome"] = nome
    return d


def _gravar(caminho: Path, dados) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=None, separators=(",", ":")),
        encoding="utf-8",
    )


def nomes_ufs(config: dict) -> dict[str, str]:
    """`{"GO": "GOIÁS", ...}` a partir de `abr[].ds` do config de municípios."""
    return {u["cd"].upper(): u["ds"] for u in config["abr"]}


def meta_de(arquivo_br: dict, resultado_br: Resultado, agora: datetime | None = None) -> dict:
    agora = agora or datetime.now(FUSO)
    return {
        "gerado_em": agora.astimezone(FUSO).isoformat(timespec="seconds"),
        "fonte_2026_dg_hg": f"{arquivo_br['dg']} {arquivo_br['hg']}",
        "pct_secoes_br": _arred(resultado_br.pct_secoes_totalizadas),
    }


def _indexar(resultados: list[Resultado]) -> dict[tuple, Resultado]:
    return {(r.cargo, r.uf, r.municipio_tse): r for r in resultados}


def _escrever(
    pasta: Path,
    municipios: list[Municipio],
    ufs: dict[str, str],
    r22: dict[tuple, Resultado],
    r26: dict[tuple, Resultado],
    equiv: dict[str, str],
    meta: dict,
) -> None:
    def comp(cargo: Cargo, uf: str, mun: str | None) -> Comparacao | None:
        chave = (cargo, uf, mun)
        if chave not in r22 and chave not in r26:
            return None
        return comparar(r22.get(chave), r26.get(chave), equiv)

    def cargos_de(uf: str) -> tuple[Cargo, ...]:
        return ("presidente",) if uf == EXTERIOR else ("presidente", "governador")

    # Abrangências nacional e estaduais.
    for uf, nome in [("BR", "Brasil"), *sorted(ufs.items())]:
        for cargo in cargos_de(uf) if uf != "BR" else ("presidente",):
            c = comp(cargo, uf, None)
            if c is not None:
                _gravar(pasta / "comparacoes" / f"{uf.lower()}-{cargo}.json", serializar(c, nome))

    # Municípios por UF e ranking.
    ranking = []
    por_uf: dict[str, list[Municipio]] = {}
    for m in municipios:
        por_uf.setdefault(m.uf, []).append(m)
    for uf in sorted(por_uf):
        itens = []
        for m in sorted(por_uf[uf], key=lambda m: m.tse):
            item = {
                "tse": m.tse, "ibge": m.ibge, "nome": m.nome, "slug": m.slug, "capital": m.capital,
            }  # fmt: skip
            comps = {}
            for cargo in cargos_de(uf):
                c = comp(cargo, uf, m.tse)
                if c is None or c.r2026 is None:
                    continue  # exterior só em 2022: sem página
                comps[cargo] = c
                item[cargo] = serializar(c)
            if "presidente" not in comps:
                continue
            itens.append(item)
            pres = comps["presidente"]
            if uf != EXTERIOR and pres.volatilidade is not None:
                ranking.append({
                    "tse": m.tse, "nome": m.nome, "uf": uf, "slug": m.slug,
                    "aptos": pres.r2026.aptos, "volatilidade": _arred(pres.volatilidade),
                    "vencedor_2022": pres.vencedor_2022, "vencedor_2026": pres.vencedor_2026,
                    "virou": pres.virou,
                })  # fmt: skip
        _gravar(pasta / "municipios" / f"{uf.lower()}.json", {"uf": uf, "municipios": itens})

    ranking.sort(key=lambda r: (-r["volatilidade"], r["uf"], r["tse"]))
    _gravar(pasta / "ranking-presidente.json", ranking)
    _gravar(pasta / "meta.json", meta)


def exportar(
    municipios: list[Municipio],
    ufs: dict[str, str],
    r2022: list[Resultado],
    r2026: list[Resultado],
    equivalencias: dict[str, str],
    meta: dict,
    destino: Path = Path("dados/eleicoes-2026"),
) -> None:
    """Escreve em pasta temporária ao lado de `destino` e troca no fim.

    Qualquer falha antes da troca deixa `destino` intacto.
    """
    destino = Path(destino)
    novo = destino.with_name(destino.name + ".novo")
    velho = destino.with_name(destino.name + ".velho")
    for p in (novo, velho):
        shutil.rmtree(p, ignore_errors=True)
    try:
        _escrever(novo, municipios, ufs, _indexar(r2022), _indexar(r2026), equivalencias, meta)
        if destino.exists():
            destino.rename(velho)
        novo.rename(destino)
    except BaseException:
        shutil.rmtree(novo, ignore_errors=True)
        if velho.exists() and not destino.exists():
            velho.rename(destino)
        raise
    shutil.rmtree(velho, ignore_errors=True)
