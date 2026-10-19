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
SO_2026 = ("SP", "73709")  # município que não existe nos dados de 2022
MUNIS_2026 = {(uf, f"{i + 1:05d}") for uf, n in UFS.items() for i in range(n)} | {SO_2026}
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
    return list(
        gerar_sequencia(
            r2022, passos=12, semente=1, capitais={("SP", "00001")}, municipios_2026=MUNIS_2026
        )
    )


def _votos(arquivo, cargo="presidente"):
    return {c.numero: c.votos for c in ler_resultado_2026(arquivo, cargo, uf="XX").candidatos}


def _municipal(arq):
    return arq.get("tpabr") == "mu"


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
            if "-c0001-" in url and _municipal(arq):
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


def test_url_desconhecida_da_404(r2022):
    baixar = baixar_simulado(gerar_sequencia(r2022, passos=6, semente=1))
    baixar(URL_AB, forcar=True)
    with pytest.raises(ErroDownload) as e:
        baixar("https://exemplo.invalido/x.json", forcar=True)
    assert e.value.status == 404


def test_brasil_e_uf_existem_no_passo_0_com_pct_menor_que_100(passos):
    for url in (URL_BR, url_resultado_2026("presidente", "sp", None, "6258")):
        r = ler_resultado_2026(passos[0][url], "presidente")
        assert r.pct_secoes_totalizadas < 100


def _nao_iniciados(passo):
    """URLs de presidente municipais de 2026 sem apuração no passo (só no mapa dos zerados)."""
    todas = (url_resultado_2026("presidente", uf.lower(), t, "6258") for uf, t in sorted(MUNIS_2026))
    return [u for u in todas if u not in dict.keys(passo)]


def test_municipio_nao_iniciado_tem_arquivo_zerado_constante(passos):
    urls = _nao_iniciados(passos[0])
    assert len(urls) > 20
    url = urls[0]
    arq = passos[0][url]
    r = ler_resultado_2026(arq, "presidente", uf="XX")
    assert r.pct_secoes_totalizadas == 0 and r.comparecimento == 0
    assert [c.votos for c in r.candidatos] == [0, 0]
    assert arq["and"] == "n" and arq["s"]["pstn"] == "0"
    assert all(c["st"] == "" for a in arq["carg"][0]["agr"] for p in a["par"] for c in p["cand"])
    # constante enquanto não apurado: mesmo idg/dg/hg em todos os passos
    for passo in passos:
        if url not in dict.keys(passo):
            assert (passo[url]["idg"], passo[url]["dg"], passo[url]["hg"]) == (
                arq["idg"], arq["dg"], arq["hg"]
            )
    # e quando começa a apurar, o idg sobe
    iniciado = next(p[url] for p in passos if url in dict.keys(p))
    assert int(iniciado["idg"]) > int(arq["idg"])


def test_municipio_so_de_2026_tem_arquivo_zerado_em_todos_os_passos(passos):
    for cargo, cod in (("presidente", "6258"), ("governador", "6260")):
        url = url_resultado_2026(cargo, "sp", SO_2026[1], cod)
        arquivos = {json.dumps(p[url], sort_keys=True) for p in passos}
        assert len(arquivos) == 1
        r = ler_resultado_2026(passos[-1][url], cargo, uf="SP")
        assert r.pct_secoes_totalizadas == 0 and r.validos == 0


def test_coletor_e_montar_veem_aguardando_sem_erros(r2022):
    from datetime import datetime

    from qma_comum.municipios import Municipio
    from qma_eleicoes.ao_vivo.coleta import Coletor
    from qma_eleicoes.ao_vivo.montar import montar

    munis = [Municipio(t, None, t, uf, False, t) for uf, t in sorted(MUNIS_2026)]
    baixar = baixar_simulado(
        gerar_sequencia(r2022, passos=12, semente=1, municipios_2026=MUNIS_2026)
    )
    coletor = Coletor(munis, ["AL", "SP"], _baixar=baixar, max_por_ciclo=10_000)
    rel = coletor.ciclo()
    assert rel.erros == []
    base = {
        "municipios": {
            m.tse: {"uf": m.uf, "ibge": m.tse, "nome": m.nome, "slug": m.slug, "t2_2022": None}
            for m in munis
        },
        "agregados_2022_t2": {"presidente": {}, "governador": {}},
    }
    arquivos = montar(coletor.resultados, coletor.horarios, base, agora=datetime(2026, 10, 25, 18), andamento=coletor.andamento)  # fmt: skip
    so = next(m for m in arquivos["ao-vivo/municipios/sp.json"] if m["tse"] == SO_2026[1])
    assert so["status"] == "aguardando" and so["pct_secoes"] == 0
    assert any(r.pct_secoes_totalizadas == 0 for r in coletor.resultados.values())


def test_inicio_simulado_define_dg_hg(r2022):
    from datetime import datetime

    passo = next(gerar_sequencia(r2022, passos=6, inicio=datetime(2026, 10, 25, 17, 0)))
    assert passo[URL_BR]["dg"] == "25/10/2026" and passo[URL_BR]["hg"] == "17:00:00"


def test_poucos_passos_rejeitado(r2022):
    with pytest.raises(ValueError):
        list(gerar_sequencia(r2022, passos=2))
