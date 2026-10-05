from pathlib import Path

import pytest

from qma_eleicoes.leitor_2022 import arquivos_2022, ler_2022

AMOSTRAS = Path(__file__).parent / "amostras"
VOTACAO = AMOSTRAS / "votacao_2022_recorte.csv"
DETALHE = AMOSTRAS / "detalhe_2022_recorte.csv"


def _ler(turno: int):
    return ler_2022([VOTACAO], [DETALHE], turno=turno)


def _achar(resultados, cargo, uf, municipio):
    (r,) = [
        r
        for r in resultados
        if (r.cargo, r.uf, r.municipio_tse) == (cargo, uf, municipio)
    ]
    return r


def _votos(resultado, numero):
    (c,) = [c for c in resultado.candidatos if c.numero == numero]
    return c


def test_soma_zonas_e_transito():
    # Lula em Arapiraca no 1º turno: duas zonas + uma linha de voto em trânsito
    # (a amostra inclui uma linha "S" sintética de 10 votos).
    r = _achar(_ler(1), "presidente", "AL", "27057")
    assert _votos(r, 13).votos == 59441
    assert _votos(r, 22).votos == 48456
    assert r.candidatos[0].numero == 13  # ordenado por votos


def test_ignora_deputados():
    resultados = _ler(1)
    assert {r.cargo for r in resultados} == {"presidente", "governador"}
    gov = _achar(resultados, "governador", "AL", "27057")
    assert 77777 not in {c.numero for c in gov.candidatos}


def test_codigo_municipio_com_5_digitos():
    # votação traz 5231 sem aspas, detalhe traz "05231".
    r = _achar(_ler(1), "presidente", "PA", "05231")
    assert _votos(r, 13).votos == 16767
    assert r.aptos == 33876


def test_turno_filtrado():
    r1 = _achar(_ler(1), "presidente", "AL", "27057")
    r2 = _achar(_ler(2), "presidente", "AL", "27057")
    assert (r1.turno, r2.turno) == (1, 2)
    assert _votos(r2, 13).votos == 61009
    assert {c.numero for c in r2.candidatos} == {13, 22}
    assert {c.numero for c in r1.candidatos} == {12, 13, 22}


def test_validos_do_detalhe():
    r = _achar(_ler(1), "presidente", "AL", "27057")
    assert r.validos == 116937
    assert (r.aptos, r.comparecimento, r.abstencao) == (150978, 122165, 28825)
    assert (r.brancos, r.nulos) == (2016, 3212)
    assert r.pct_secoes_totalizadas == 100.0
    assert (r.ano, r.cargo) == (2022, "presidente")


def test_situacao_governador_segundo_turno():
    g1 = _achar(_ler(1), "governador", "AL", "27057")
    assert {c.numero: c.situacao for c in g1.candidatos} == {
        15: "2º turno", 44: "2º turno", 14: "não eleito",
    }  # fmt: skip
    g2 = _achar(_ler(2), "governador", "AL", "27057")
    assert [(c.nome_urna, c.situacao) for c in g2.candidatos] == [
        ("RODRIGO CUNHA", "não eleito"),
        ("PAULO DANTAS", "eleito"),
    ]


def test_agregados_uf_e_brasil():
    resultados = _ler(1)
    uf = _achar(resultados, "presidente", "AL", None)
    assert _votos(uf, 13).votos == 59441  # só Arapiraca na amostra
    br = _achar(resultados, "presidente", "BR", None)
    assert _votos(br, 13).votos == 59441 + 16767
    assert br.validos == 116937 + 27075
    gov_uf = _achar(resultados, "governador", "AL", None)
    assert _votos(gov_uf, 15).votos == 39634
    # governador não tem agregado nacional
    assert not [r for r in resultados if r.cargo == "governador" and r.uf == "BR"]


@pytest.mark.rede
def test_totais_oficiais_2022():
    votacao, detalhe = arquivos_2022()
    esperado = {
        1: {13: 57_259_504, 22: 51_072_345},
        2: {13: 60_345_999, 22: 58_206_354},
    }
    for turno, votos in esperado.items():
        resultados = ler_2022(votacao, detalhe, turno=turno)
        br = _achar(resultados, "presidente", "BR", None)
        for numero, total in votos.items():
            assert _votos(br, numero).votos == total
