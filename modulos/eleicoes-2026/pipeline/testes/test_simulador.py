import json
import random

import pytest

from qma_comum.http import ErroDownload
from qma_eleicoes.ao_vivo.simulador import baixar_simulado, gerar_sequencia
from qma_eleicoes.config import (
    URL_CONFIG_GOVERNADOR_T2,
    url_andamento_2026,
    url_resultado_2026,
)
from qma_eleicoes.leitor_2026 import ler_resultado_2026
from qma_eleicoes.modelo import Resultado, VotoCandidato

LULA, BOLSONARO = 60_345_999, 58_206_354
UFS = {"AL": 12, "SP": 30, "ZZ": 4}  # UF → nº de municípios
GOVERNADOR = {"AL", "SP"}
URL_BR = url_resultado_2026("presidente", "br", None, "6258")
URL_AB = url_andamento_2026("6258")


def _resultado(cargo, uf, tse, lula, bolso):
    nulos, brancos = (lula + bolso) // 30, (lula + bolso) // 60
    validos = lula + bolso
    comp = validos + nulos + brancos
    return Resultado(
        ano=2022, turno=2, cargo=cargo, uf=uf, municipio_tse=tse, aptos=comp + comp // 5,
        comparecimento=comp, abstencao=comp // 5, brancos=brancos, nulos=nulos,
        validos=validos, pct_secoes_totalizadas=100.0,
        candidatos=(
            VotoCandidato(13, "LULA", "PT", lula, "eleito"),
            VotoCandidato(22, "JAIR BOLSONARO", "PL", bolso, "não eleito"),
        ),
    )  # fmt: skip


@pytest.fixture(scope="module")
def r2022():
    """Municípios sintéticos cujo total nacional é o oficial de 2022 (Lula × Bolsonaro)."""
    sorteio = random.Random(7)
    munis = [(uf, f"{i + 1:05d}") for uf, n in UFS.items() for i in range(n)]
    pesos = [sorteio.randint(1, 100) for _ in munis]
    lulas, bolsos = [], []
    for total, saida in ((LULA, lulas), (BOLSONARO, bolsos)):
        soma = sum(pesos)
        saida.extend(total * p // soma for p in pesos)
        saida[-1] += total - sum(saida)
    r = [_resultado("presidente", uf, t, lu, bo) for (uf, t), lu, bo in zip(munis, lulas, bolsos)]
    r += [
        _resultado("governador", uf, t, lu // 2 + 1, bo // 2 + 1)
        for (uf, t), lu, bo in zip(munis, lulas, bolsos)
        if uf in GOVERNADOR
    ]
    return r


@pytest.fixture(scope="module")
def passos(r2022):
    return list(gerar_sequencia(r2022, passos=12, semente=1, capitais={("SP", "00001")}))


def _votos(arquivo, cargo="presidente"):
    return {c.numero: c.votos for c in ler_resultado_2026(arquivo, cargo, uf="XX").candidatos}


def _municipal(url):
    return len(url.rsplit("/", 1)[1].split("-")[0]) > 2 and "-ab." not in url


def test_ultimo_passo_igual_resultado_oficial_2022(passos, r2022):
    br = passos[-1][URL_BR]
    assert _votos(br) == {13: LULA, 22: BOLSONARO}
    resultado = ler_resultado_2026(br, "presidente")
    assert resultado.pct_secoes_totalizadas == 100
    assert {c.numero: c.situacao for c in resultado.candidatos} == {13: "eleito", 22: "não eleito"}
    for uf in GOVERNADOR:  # UF de governador fecha com a soma dos municípios oficiais
        oficial = sum(r.validos for r in r2022 if r.cargo == "governador" and r.uf == uf)
        arq = passos[-1][url_resultado_2026("governador", uf.lower(), None, "6260")]
        assert ler_resultado_2026(arq, "governador").validos == oficial


def test_idg_cresce(passos):
    ultimo: dict[str, tuple[str, str]] = {}
    for passo in passos:
        for url, arq in passo.items():
            if "idg" not in arq:
                continue
            ignorar = ("idg", "dg", "hg", "dt", "ht")
            conteudo = json.dumps({k: v for k, v in arq.items() if k not in ignorar})
            if url in ultimo:
                idg_ant, conteudo_ant = ultimo[url]
                if conteudo != conteudo_ant:
                    assert int(arq["idg"]) > int(idg_ant), url
                else:
                    assert arq["idg"] == idg_ant, url
            ultimo[url] = (arq["idg"], conteudo)
    for url in (URL_BR, URL_AB):  # Brasil e andamento mudam em todo passo
        idgs = [int(p[url]["idg"]) for p in passos]
        assert idgs == sorted(set(idgs))


def test_formato_lido_por_ler_resultado_2026(passos):
    lidos = 0
    for url, arq in passos[len(passos) // 2].items():
        if "-u.json" not in url:
            continue
        cargo = "presidente" if "-c0001-" in url else "governador"
        r = ler_resultado_2026(arq, cargo, uf=url.rsplit("/", 2)[-2].upper())
        assert r.turno == 2 and r.ano == 2026
        assert {c.numero for c in r.candidatos} == {13, 22}
        assert r.aptos >= r.comparecimento
        lidos += 1
    assert lidos > 10


def test_parciais_somam_e_progresso_ponderado(passos):
    for passo in passos[:-1]:
        soma = {13: 0, 22: 0}
        for url, arq in passo.items():
            if "-c0001-" in url and _municipal(url):
                for n, v in _votos(arq).items():
                    soma[n] += v
        assert _votos(passo[URL_BR]) == soma
        assert ler_resultado_2026(passo[URL_BR], "presidente").pct_secoes_totalizadas < 100


def test_situacao_vazia_ate_100(passos):
    for passo in passos[:-1]:
        cands = [c for a in passo[URL_BR]["carg"][0]["agr"] for p in a["par"] for c in p["cand"]]
        assert all(c["st"] == "" for c in cands)


def test_ab_e_configuracao_do_governador(passos):
    cfg = passos[0][URL_CONFIG_GOVERNADOR_T2]
    assert {u["cd"] for u in cfg["abr"] if u["mu"]} == {"al", "sp"}
    assert {a["cdabr"] for a in passos[3][URL_AB]["abr"]} == {"br", "al", "sp", "zz"}
    pst = [float(p[URL_AB]["abr"][0]["s"]["pst"].replace(",", ".")) for p in passos]
    assert pst == sorted(pst) and pst[0] < 100 and pst[-2] < 100 and pst[-1] == 100


def test_capital_apura_primeiro(passos):
    capital = url_resultado_2026("presidente", "sp", "00001", "6258")
    assert capital in passos[0]


def test_semente_determinista_e_muda_ordem(r2022):
    a = list(gerar_sequencia(r2022, passos=8, semente=3))
    b = list(gerar_sequencia(r2022, passos=8, semente=3))
    c = list(gerar_sequencia(r2022, passos=8, semente=4))
    assert [sorted(p) for p in a] == [sorted(p) for p in b]
    assert [sorted(p) for p in a] != [sorted(p) for p in c]


def test_baixar_simulado_avanca_um_passo_por_andamento(r2022):
    baixar = baixar_simulado(gerar_sequencia(r2022, passos=6, semente=1))
    baixar(URL_CONFIG_GOVERNADOR_T2, forcar=True)  # lida antes do 1º ciclo
    ids = []
    for _ in range(8):
        ids.append(baixar(URL_AB, forcar=True)["idg"])
        assert baixar(URL_BR, forcar=True)["idg"] is not None
    assert len(set(ids[:6])) == 6 and ids[:6] == sorted(ids[:6])
    assert ids[6:] == [ids[5]] * 2  # depois do último passo, repete


def test_url_desconhecida_ou_municipio_sem_apuracao_da_404(r2022):
    baixar = baixar_simulado(gerar_sequencia(r2022, passos=6, semente=1))
    baixar(URL_AB, forcar=True)
    inexistente = url_resultado_2026("presidente", "sp", "99999", "6258")
    for url in ("https://exemplo.invalido/x.json", inexistente):
        with pytest.raises(ErroDownload) as e:
            baixar(url, forcar=True)
        assert e.value.status == 404


def test_poucos_passos_rejeitado(r2022):
    with pytest.raises(ValueError):
        list(gerar_sequencia(r2022, passos=2))
