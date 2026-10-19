"""Monta os JSONs do ao vivo (estado e municípios por UF) a partir do estado do coletor."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from ..comparacao import comparar
from ..modelo import Cargo, Resultado, VotoCandidato

Chave = tuple[Cargo, str, str | None]


def _pct(votos: int, validos: int) -> float | None:
    return round(votos / validos * 100, 2) if validos else None


def _numero(texto: str | float) -> float:
    return float(texto.replace(",", ".")) if isinstance(texto, str) else float(texto)


def _votos_por_partido(r: Resultado) -> dict[str, int]:
    votos: dict[str, int] = defaultdict(int)
    for c in r.candidatos:
        votos[c.partido] += c.votos
    return dict(votos)


def _r2022(cargo: Cargo, uf: str, agregado: dict | None) -> Resultado | None:
    """Reconstrói o Resultado de 2022 (UF/BR) a partir dos agregados da base."""
    if not agregado or not agregado.get("validos"):
        return None
    candidatos = tuple(
        VotoCandidato(0, p, p, v, "") for p, v in sorted(agregado["votos"].items())
    )
    return Resultado(
        ano=2022, turno=2, cargo=cargo, uf=uf, municipio_tse=None, aptos=0, comparecimento=0,
        abstencao=0, brancos=0, nulos=0, validos=agregado["validos"],
        pct_secoes_totalizadas=100.0, candidatos=candidatos,
    )  # fmt: skip


def _comparacao(cargo: Cargo, uf: str, r: Resultado, base: dict) -> dict | None:
    agregado = base.get("agregados_2022_t2", {}).get(cargo, {}).get(uf.upper())
    r22 = _r2022(cargo, uf, agregado)
    if r22 is None or r.validos == 0:
        return None
    comp = comparar(r22, r, {})
    return {
        "partidos": [
            {
                "partido": l.partido,
                "pct_2022": None if l.pct_2022 is None else round(l.pct_2022, 2),
                "pct_2026": None if l.pct_2026 is None else round(l.pct_2026, 2),
                "delta_pp": None if l.delta_pp is None else round(l.delta_pp, 2),
            }
            for l in comp.partidos
        ]
    }


def _ao_vivo(cargo: Cargo, uf: str, r: Resultado, horario: str | None, base: dict) -> dict:
    return {
        "horario_tse": horario,
        "pct_secoes": r.pct_secoes_totalizadas,
        "candidatos": [
            {
                "numero": c.numero,
                "nome_urna": c.nome_urna,
                "partido": c.partido,
                "votos": c.votos,
                "pct": _pct(c.votos, r.validos),
            }
            for c in r.candidatos
        ],
        "comparecimento": r.comparecimento,
        "abstencao": r.abstencao,
        "brancos": r.brancos,
        "nulos": r.nulos,
        "comparacao_2022": _comparacao(cargo, uf, r, base),
    }


def _vencedor(votos: dict[str, int]) -> str | None:
    ordem = sorted(votos.items(), key=lambda x: -x[1])
    if not ordem or ordem[0][1] <= 0 or (len(ordem) > 1 and ordem[1][1] == ordem[0][1]):
        return None
    return ordem[0][0]


def _municipio(tse: str, info: dict, r: Resultado | None, horario: str | None) -> dict:
    item = {
        "tse": tse,
        "ibge": info["ibge"],
        "pct_secoes": r.pct_secoes_totalizadas if r else 0,
        "status": "aguardando",
        "vencedor": None,
        "partidos": None,
        "validos": None,  # votos válidos já apurados no município (base da projeção)
        "delta_vs_2022": None,
        "horario_tse": horario if r else None,
    }
    if r is None or r.pct_secoes_totalizadas <= 0 or r.validos == 0:
        return item
    votos = _votos_por_partido(r)
    item["status"] = "completo" if r.pct_secoes_totalizadas >= 100 else "parcial"
    item["vencedor"] = _vencedor(votos)
    item["partidos"] = {p: _pct(v, r.validos) for p, v in votos.items()}
    item["validos"] = r.validos
    anterior = (info.get("t2_2022") or {}).get("partidos")
    if anterior:
        item["delta_vs_2022"] = {
            p: round(v / r.validos * 100 - anterior[p], 2) for p, v in votos.items() if p in anterior
        }
    return item


def montar(
    resultados: dict[Chave, Resultado],
    horarios: dict[Chave, str],
    base: dict,
    *,
    agora: datetime,
    andamento: dict[str, dict] | None = None,
) -> dict[str, dict | list]:
    """Caminho (relativo à raiz publicada) → conteúdo JSON. Totais oficiais, nunca somados."""
    estado: dict = {
        "atualizado_em": agora.isoformat(timespec="seconds"),
        "andamento": {
            abr.lower(): _numero(v["pst"]) for abr, v in sorted((andamento or {}).items())
        },
        "presidente": {"br": None, "ufs": {}},
        "governador": {},
    }
    for (cargo, uf, tse), r in sorted(resultados.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if tse is not None:
            continue
        item = _ao_vivo(cargo, uf, r, horarios.get((cargo, uf, tse)), base)
        if cargo == "governador":
            estado["governador"][uf.lower()] = item
        elif uf == "BR":
            estado["presidente"]["br"] = item
        else:
            estado["presidente"]["ufs"][uf.lower()] = item

    saida: dict[str, dict | list] = {"ao-vivo/estado.json": estado}
    for uf, lista in sorted(municipios_por_uf(resultados, horarios, base).items()):
        saida[f"ao-vivo/municipios/{uf}.json"] = lista
    return saida


def municipios_por_uf(
    resultados: dict[Chave, Resultado], horarios: dict[Chave, str], base: dict
) -> dict[str, list[dict]]:
    """Itens municipais (presidente) por UF minúscula, na ordem do código TSE."""
    por_uf: dict[str, list[dict]] = defaultdict(list)
    for tse, info in sorted(base["municipios"].items()):
        chave = ("presidente", info["uf"], tse)
        por_uf[info["uf"].lower()].append(
            _municipio(tse, info, resultados.get(chave), horarios.get(chave))
        )
    return dict(por_uf)
