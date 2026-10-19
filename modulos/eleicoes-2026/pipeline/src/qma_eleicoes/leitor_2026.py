"""Leitor do JSON de resultados do TSE (formato 2026, arquivos `-u.json`)."""

from __future__ import annotations

from .config import CODIGO_CARGO
from .modelo import Cargo, Resultado, Situacao, VotoCandidato


def _num(texto: str) -> float:
    return float(texto.replace(",", "."))


def _situacao(cand: dict) -> Situacao:
    # `e == "s"` significa "classificado" (eleito OU 2º turno); só `st` distingue.
    st = (cand.get("st") or "").casefold().strip()
    if "2º turno" in st:
        return "2º turno"
    if "não eleito" in st:
        return "não eleito"
    if st.startswith("eleito"):
        return "eleito"
    return ""


def _valido(cand: dict) -> bool:
    """`dvt` diferente de "Válido" (ex.: "Anulado", "Anulado sub judice") → fora dos válidos.

    Arquivos sem votos (algumas cidades do exterior) não trazem `dvt`: conta como válido.
    """
    dvt = cand.get("dvt")
    return dvt is None or dvt.strip().casefold() == "válido"


def ler_resultado_2026(dados: dict, cargo: Cargo, uf: str | None = None) -> Resultado:
    """Converte o JSON do TSE em `Resultado`. `uf` é obrigatório em arquivos municipais."""
    tpabr, cdabr = dados["tpabr"], dados["cdabr"]
    municipio_tse = None
    if tpabr == "br":
        sigla = "BR"
    elif tpabr == "uf":
        sigla = cdabr.upper()
    elif tpabr == "mu":
        if not uf:
            raise ValueError("uf é obrigatório para arquivos municipais (tpabr == 'mu')")
        sigla, municipio_tse = uf.upper(), cdabr
    else:
        raise ValueError(f"abrangência desconhecida: {tpabr!r}")

    codigo = str(CODIGO_CARGO[cargo])
    bloco = next((c for c in dados["carg"] if c["cd"] == codigo), None)
    if bloco is None:
        raise ValueError(f"cargo {cargo!r} (cd={codigo}) ausente no arquivo")

    candidatos: list[VotoCandidato] = []
    anulados: list[VotoCandidato] = []
    for agr in bloco["agr"]:
        for p in agr["par"]:
            for c in p["cand"]:
                voto = VotoCandidato(
                    numero=int(c["n"]),
                    nome_urna=c["nmu"],
                    partido=p["sg"],
                    votos=int(c["vap"]),
                    situacao=_situacao(c),
                )
                (candidatos if _valido(c) else anulados).append(voto)
    candidatos.sort(key=lambda c: c.votos, reverse=True)
    anulados.sort(key=lambda c: c.votos, reverse=True)

    return Resultado(
        ano=2026,
        turno=int(dados["t"]),
        cargo=cargo,
        uf=sigla,
        municipio_tse=municipio_tse,
        aptos=int(dados["e"]["te"]),
        comparecimento=int(dados["e"]["c"]),
        abstencao=int(dados["e"]["a"]),
        brancos=int(dados["v"]["vb"]),
        nulos=int(dados["v"]["tvn"]),
        validos=int(dados["v"]["vv"]),
        pct_secoes_totalizadas=_num(dados["s"]["pstn"]),
        candidatos=tuple(candidatos),
        anulados=tuple(anulados),
    )
