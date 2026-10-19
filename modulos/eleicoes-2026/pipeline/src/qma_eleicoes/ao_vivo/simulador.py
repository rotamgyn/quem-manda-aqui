"""Simulador de apuração: reproduz o 2º turno de 2022 como arquivos no formato TSE (2026).

Serve ao ensaio geral do robô e ao backtest da projeção. Os arquivos usam os códigos e as
URLs do 2º turno de 2026 (6258/6260), com candidatos, números e votos de 2022. Cada município
avança por frações de seção (30% → 70% → 100%); UF e Brasil, em cada passo, são a soma exata
dos estados parciais dos municípios (retrato consistente).
"""

from __future__ import annotations

import random
from collections.abc import Callable, Collection, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta

from qma_comum.http import ErroDownload

from ..config import (
    ELEICAO_2026_T2,
    URL_CONFIG_GOVERNADOR_T2,
    url_andamento_2026,
    url_resultado_2026,
)
from ..modelo import Cargo, Resultado, VotoCandidato

FRACOES = ((3, 10), (7, 10), (1, 1))  # fração de seções apuradas no 1º, 2º e 3º passo do município
INICIO = datetime(2022, 10, 30, 17, 0, 0)  # relógio simulado do passo 0 (fecha as urnas às 17h)
MINUTOS_POR_PASSO = 6
IDG_BASE = 2_000_000
_CODIGO = {"presidente": "1", "governador": "3"}
_ELEICAO_BR = "6258"


@dataclass
class _Municipio:
    cargo: Cargo
    uf: str
    tse: str
    inicio: int  # passo em que aparece com a 1ª fração
    resultado: Resultado


def _div(valor: int, fracao: tuple[int, int]) -> int:
    num, den = fracao
    return (valor * num + den // 2) // den


def _porte_ordem(m: Resultado, capitais: Collection[tuple[str, str]]) -> float:
    """Menor = apura antes: capitais primeiro, depois os menores eleitorados."""
    return -1.0 if (m.uf, m.municipio_tse) in capitais else float(m.aptos)


def _inicios(
    municipais: list[Resultado], passos: int, semente: int, capitais: Collection[tuple[str, str]]
) -> dict[tuple[str, str], int]:
    """Passo de início de cada município (presidente e governador compartilham as seções).

    A ordem vem do porte (capitais e menores primeiro) com um deslocamento por UF sorteado
    pela semente; as posições são normalizadas para ocupar todo o intervalo [0, passos-3],
    de modo que o último passo tenha ao menos um município terminando.
    """
    ufs = sorted({m.uf for m in municipais})
    sorteio = random.Random(semente)
    ordem_uf = ufs[:]
    sorteio.shuffle(ordem_uf)
    deslocamento_uf = {uf: i / max(len(ufs), 1) for i, uf in enumerate(ordem_uf)}

    unicos: dict[tuple[str, str], Resultado] = {}
    for m in municipais:
        unicos.setdefault((m.uf, m.municipio_tse), m)
    maior = max((m.aptos for m in unicos.values()), default=1) or 1
    pontos = {}
    for chave, m in unicos.items():
        ordem = _porte_ordem(m, capitais)
        porte = 0.0 if ordem < 0 else 0.1 + 0.9 * (ordem / maior) ** 0.5
        pontos[chave] = 0.8 * porte + 0.2 * deslocamento_uf[m.uf] + sorteio.random() * 0.01
    ranking = sorted(pontos, key=lambda c: (pontos[c], c))
    ultimo = max(len(ranking) - 1, 1)
    janela = max(passos - len(FRACOES), 0)
    return {chave: (pos * janela) // ultimo for pos, chave in enumerate(ranking)}


class _Elenco:
    """Candidatos de um cargo/escopo (presidente: nacional; governador: por UF)."""

    def __init__(self, resultados: list[Resultado]):
        elenco: dict[int, VotoCandidato] = {}
        for r in resultados:
            for c in r.candidatos:
                elenco.setdefault(c.numero, c)
        self.candidatos = sorted(elenco.values(), key=lambda c: c.numero)


def _estado(r: Resultado, fracao: tuple[int, int]) -> dict:
    """Contagens parciais de um município na fração dada (inteiros, somáveis)."""
    votos = {c.numero: _div(c.votos, fracao) for c in r.candidatos}
    soma_oficial = sum(c.votos for c in r.candidatos)
    return {
        "te": r.aptos,
        "c": _div(r.comparecimento, fracao),
        "a": _div(r.abstencao, fracao),
        "vb": _div(r.brancos, fracao),
        "tvn": _div(r.nulos, fracao),
        # votos válidos não nominais (normalmente 0) acompanham a fração
        "vv": sum(votos.values()) + _div(r.validos - soma_oficial, fracao),
        "votos": votos,
    }


def _somar(estados: list[dict]) -> dict:
    total = {"te": 0, "c": 0, "a": 0, "vb": 0, "tvn": 0, "vv": 0, "votos": {}}
    for e in estados:
        for k in ("te", "c", "a", "vb", "tvn", "vv"):
            total[k] += e[k]
        for n, v in e["votos"].items():
            total["votos"][n] = total["votos"].get(n, 0) + v
    return total


def _pct_texto(progresso: float, completo: bool) -> tuple[str, str]:
    """`pst` ("12,34") e `pstn` ("12.34"): nunca 100 antes de todos os municípios terminarem."""
    if completo:
        return "100,00", "100"
    truncado = min(int(progresso * 10_000) / 100, 99.99)
    return f"{truncado:.2f}".replace(".", ","), f"{truncado:.2f}"


def _arquivo(
    cargo: Cargo,
    tpabr: str,
    cdabr: str,
    estado: dict,
    elenco: _Elenco,
    progresso: float,
    completo: bool,
    k: int,
    idg: int,
) -> dict:
    """Um arquivo `-u.json` no formato do TSE (campos que o leitor e o robô usam)."""
    agora = INICIO + timedelta(minutes=MINUTOS_POR_PASSO * k)
    pst, pstn = _pct_texto(progresso, completo)
    votos = estado["votos"]
    vencedor = None
    if completo and votos:
        ordem = sorted(votos.values(), reverse=True)
        if len(ordem) == 1 or ordem[0] > ordem[1]:
            vencedor = max(votos, key=lambda n: votos[n])
    candidatos = []
    for c in elenco.candidatos:
        eleito = c.numero == vencedor
        candidatos.append(
            {
                "n": str(c.numero), "nm": c.nome_urna, "nmu": c.nome_urna, "dvt": "Válido",
                "e": "s" if eleito else "n",
                "st": ("Eleito" if eleito else "Não eleito") if completo and vencedor else "",
                "vap": str(votos.get(c.numero, 0)),
            }
        )  # fmt: skip
    return {
        "ele": ELEICAO_2026_T2[cargo], "t": "2", "f": "o", "sup": "n", "tpabr": tpabr,
        "cdabr": cdabr, "dg": f"{agora:%d/%m/%Y}", "hg": f"{agora:%H:%M:%S}", "idg": str(idg),
        "dt": f"{agora:%d/%m/%Y}", "ht": f"{agora:%H:%M:%S}", "dv": "s", "tf": "n",
        "and": "f" if completo else "p", "md": "n",
        "s": {"pst": pst, "pstn": pstn},
        "e": {"te": str(estado["te"]), "c": str(estado["c"]), "a": str(estado["a"])},
        "v": {
            "tv": str(estado["c"]), "vb": str(estado["vb"]), "tvn": str(estado["tvn"]),
            "vv": str(estado["vv"]),
        },
        "carg": [
            {
                "cd": _CODIGO[cargo], "nv": "1",
                "agr": [
                    {"n": str(cand["n"]), "tp": "i", "par": [
                        {"n": str(cand["n"]), "sg": c.partido, "cand": [cand]}
                    ]}
                    for cand, c in zip(candidatos, elenco.candidatos)
                ],
            }
        ],
    }  # fmt: skip


def _url_mun(cargo: Cargo, uf: str, tse: str) -> str:
    return url_resultado_2026(cargo, uf.lower(), tse, ELEICAO_2026_T2[cargo])


def _config_governador(municipais: list[_Municipio]) -> dict:
    """`config/mun-e006260-cm.json` simulado: as UFs de 2º turno de governador de 2022."""
    por_uf: dict[str, list[str]] = {}
    for m in municipais:
        if m.cargo == "governador":
            por_uf.setdefault(m.uf, []).append(m.tse)
    return {
        "f": "o",
        "abr": [
            {"cd": uf.lower(), "ds": uf, "mu": [{"cd": t, "nm": t} for t in sorted(codigos)]}
            for uf, codigos in sorted(por_uf.items())
        ],
    }


def gerar_sequencia(
    r2022_t2: list[Resultado],
    *,
    passos: int = 40,
    semente: int = 25,
    capitais: Collection[tuple[str, str]] = (),
) -> Iterator[dict[str, dict]]:
    """Gera `passos` retratos da apuração; cada um é `{url: arquivo}`.

    `capitais`: pares (UF, código TSE) apurados primeiro. Municípios ainda sem apuração não
    têm arquivo no passo (o servidor responde 404, como o TSE). O último passo reproduz
    exatamente o resultado oficial. O gerador é preguiçoso: arquivos de municípios já
    concluídos são reaproveitados (mesmo objeto) e nada além do passo atual é mantido.
    """
    if passos < len(FRACOES):
        raise ValueError(f"passos deve ser >= {len(FRACOES)}")
    municipais_r = [r for r in r2022_t2 if r.municipio_tse is not None]
    inicios = _inicios(municipais_r, passos, semente, capitais)
    municipais = [
        _Municipio(r.cargo, r.uf, r.municipio_tse, inicios[(r.uf, r.municipio_tse)], r)
        for r in municipais_r
    ]
    elenco_pres = _Elenco([m.resultado for m in municipais if m.cargo == "presidente"])
    elenco_gov = {
        uf: _Elenco([m.resultado for m in municipais if m.cargo == "governador" and m.uf == uf])
        for uf in sorted({m.uf for m in municipais if m.cargo == "governador"})
    }
    config = _config_governador(municipais)
    url_ab, url_br = url_andamento_2026(_ELEICAO_BR), url_resultado_2026(
        "presidente", "br", None, _ELEICAO_BR
    )
    ufs_pres = sorted({m.uf for m in municipais if m.cargo == "presidente"})
    ufs_gov = sorted(elenco_gov)
    aptos_uf: dict[tuple[Cargo, str], int] = {}
    for m in municipais:
        aptos_uf[(m.cargo, m.uf)] = aptos_uf.get((m.cargo, m.uf), 0) + m.resultado.aptos

    prontos: dict[tuple[Cargo, str, str], dict] = {}  # municípios em 100%: arquivo reaproveitado
    ultimo_idg: dict[str, int] = {}

    for k in range(passos):
        arquivos: dict[str, dict] = {URL_CONFIG_GOVERNADOR_T2: config}
        idg = IDG_BASE + k
        estados: dict[tuple[Cargo, str], list[dict]] = {}
        progresso: dict[tuple[Cargo, str], float] = {}  # aptos × fração
        mudou: set[tuple[Cargo, str]] = set()
        incompletos: dict[tuple[Cargo, str], int] = {}
        for m in municipais:
            chave_uf = (m.cargo, m.uf)
            j = k - m.inicio
            if j < 0:
                incompletos[chave_uf] = incompletos.get(chave_uf, 0) + 1
                continue
            fracao = FRACOES[min(j, len(FRACOES) - 1)]
            completo = fracao == (1, 1)
            if not completo:
                incompletos[chave_uf] = incompletos.get(chave_uf, 0) + 1
            estado = _estado(m.resultado, fracao)
            estados.setdefault(chave_uf, []).append(estado)
            progresso[chave_uf] = progresso.get(chave_uf, 0.0) + m.resultado.aptos * fracao[0] / fracao[1]
            if j < len(FRACOES):
                mudou.add(chave_uf)
            url = _url_mun(m.cargo, m.uf, m.tse)
            chave_pronto = (m.cargo, m.uf, m.tse)
            if completo and chave_pronto in prontos:
                arquivos[url] = prontos[chave_pronto]
                continue
            elenco = elenco_pres if m.cargo == "presidente" else elenco_gov[m.uf]
            arq = _arquivo(
                m.cargo, "mu", m.tse, estado, elenco, fracao[0] / fracao[1], completo, k, idg
            )
            arquivos[url] = arq
            if completo:
                prontos[chave_pronto] = arq

        def publicar(url: str, arq_fn: Callable[[int], dict], alterado: bool) -> dict:
            """Mantém o `idg` anterior quando o conteúdo não mudou."""
            if alterado or url not in ultimo_idg:
                ultimo_idg[url] = idg
            arq = arq_fn(ultimo_idg[url])
            arquivos[url] = arq
            return arq

        vazio = {"te": 0, "c": 0, "a": 0, "vb": 0, "tvn": 0, "vv": 0, "votos": {}}
        for cargo, ufs in (("presidente", ufs_pres), ("governador", ufs_gov)):
            for uf in ufs:
                chave = (cargo, uf)
                soma = _somar(estados.get(chave, [vazio]))
                soma["te"] = aptos_uf[chave]
                elenco = elenco_pres if cargo == "presidente" else elenco_gov[uf]
                prog = progresso.get(chave, 0.0) / aptos_uf[chave] if aptos_uf[chave] else 0.0
                completo = incompletos.get(chave, 0) == 0
                publicar(
                    url_resultado_2026(cargo, uf.lower(), None, ELEICAO_2026_T2[cargo]),
                    lambda i, c=cargo, u=uf, s=soma, e=elenco, p=prog, f=completo: _arquivo(
                        c, "uf", u.lower(), s, e, p, f, k, i
                    ),
                    chave in mudou,
                )
        # Brasil (presidente): soma das UFs
        estados_br = [e for (c, _), lista in estados.items() if c == "presidente" for e in lista]
        soma_br = _somar(estados_br or [vazio])
        soma_br["te"] = sum(v for (c, _), v in aptos_uf.items() if c == "presidente")
        aptos_br = soma_br["te"] or 1
        prog_br = sum(v for (c, _), v in progresso.items() if c == "presidente") / aptos_br
        completo_br = all(v == 0 for (c, _), v in incompletos.items() if c == "presidente")
        publicar(
            url_br,
            lambda i, s=soma_br, p=prog_br, f=completo_br: _arquivo(
                "presidente", "br", "br", s, elenco_pres, p, f, k, i
            ),
            any(c == "presidente" for c, _ in mudou),
        )
        # andamento (presidente) por abrangência
        abr = []
        for uf in ufs_pres:
            chave = ("presidente", uf)
            prog = progresso.get(chave, 0.0) / aptos_uf[chave]
            fim = incompletos.get(chave, 0) == 0
            pst, pstn = _pct_texto(prog, fim)
            abr.append({"cdabr": uf.lower(), "and": "f" if fim else "p", "s": {"pst": pst, "pstn": pstn}})
        pst, pstn = _pct_texto(prog_br, completo_br)
        abr.insert(0, {"cdabr": "br", "and": "f" if completo_br else "p", "s": {"pst": pst, "pstn": pstn}})
        agora = INICIO + timedelta(minutes=MINUTOS_POR_PASSO * k)
        arquivos[url_ab] = {
            "dg": f"{agora:%d/%m/%Y}", "hg": f"{agora:%H:%M:%S}", "idg": str(idg), "abr": abr,
        }
        yield arquivos


def baixar_simulado(sequencia: Iterator[dict[str, dict]]) -> Callable:
    """`_baixar` do `Coletor` alimentado pela sequência.

    O arquivo de andamento (`-ab.json`) é o primeiro pedido de cada ciclo: a 1ª chamada
    serve o passo 0 e cada chamada seguinte avança um passo (depois do último, repete-o).
    Os demais URLs são servidos do passo corrente; URL sem arquivo → `ErroDownload` 404.
    """
    url_ab = url_andamento_2026(_ELEICAO_BR)
    iniciado = False
    sequencia = iter(sequencia)
    atual = next(sequencia, {})  # passo 0 já carregado: a configuração é lida antes do 1º ciclo

    def baixar(url: str, **_kw) -> dict:
        nonlocal atual, iniciado
        if url == url_ab:
            if iniciado:
                atual = next(sequencia, atual)
            iniciado = True
        if url not in atual:
            raise ErroDownload(url, 404)
        return atual[url]

    return baixar
