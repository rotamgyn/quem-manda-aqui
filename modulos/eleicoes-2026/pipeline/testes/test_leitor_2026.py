import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from qma_eleicoes.config import url_resultado_2026
from qma_eleicoes.leitor_2026 import ler_resultado_2026

AMOSTRAS = Path(__file__).parent / "amostras"


def _carregar(nome: str) -> dict:
    return json.loads((AMOSTRAS / nome).read_text(encoding="utf-8"))


@pytest.fixture
def dados_br():
    return _carregar("br-c0001-e006257-u.json")


@pytest.fixture
def dados_gov():
    return _carregar("go-c0003-e006259-u.json")


def test_brasil_presidente(dados_br):
    r = ler_resultado_2026(dados_br, "presidente")
    assert r.uf == "BR" and r.municipio_tse is None
    assert r.ano == 2026 and r.turno == 1
    assert r.aptos == 158745502
    assert r.candidatos[0].partido == "PL"
    # Amostra baixada em 05/10 (TSE atualizou após o snapshot de 04/10: era 56082216)
    assert r.candidatos[0].votos == 56104268
    assert [c.votos for c in r.candidatos] == sorted((c.votos for c in r.candidatos), reverse=True)


def test_municipio_goiania():
    r = ler_resultado_2026(_carregar("go93734-c0001-e006257-u.json"), "presidente", uf="GO")
    assert r.municipio_tse == "93734" and r.uf == "GO"


def test_municipio_sem_uf_levanta_erro():
    with pytest.raises(ValueError):
        ler_resultado_2026(_carregar("go93734-c0001-e006257-u.json"), "presidente")


def test_uf_governador(dados_gov):
    r = ler_resultado_2026(dados_gov, "governador")
    assert r.uf == "GO" and r.municipio_tse is None
    assert r.candidatos[0].situacao == "eleito"
    assert r.candidatos[1].situacao == "não eleito"


def test_cargo_ausente(dados_br):
    with pytest.raises(ValueError):
        ler_resultado_2026(dados_br, "governador")


@pytest.mark.parametrize(
    "nome,cargo,uf",
    [
        ("br-c0001-e006257-u.json", "presidente", None),
        ("go93734-c0001-e006257-u.json", "presidente", "GO"),
        ("go-c0003-e006259-u.json", "governador", None),
    ],
)
def test_soma_candidatos_igual_validos(nome, cargo, uf):
    r = ler_resultado_2026(_carregar(nome), cargo, uf)
    assert sum(c.votos for c in r.candidatos) == r.validos


def test_pct_secoes_parcial(dados_br):
    r = ler_resultado_2026(dados_br, "presidente")
    # Amostra de 05/10 (era 99,908061725 no snapshot de 04/10)
    assert r.pct_secoes_totalizadas == pytest.approx(99.997195782)
    assert r.pct(r.candidatos[0]) == pytest.approx(r.candidatos[0].votos / r.validos * 100)
    vazio = replace(r, validos=0)
    assert vazio.pct(r.candidatos[0]) is None


def test_situacao_segundo_turno(dados_gov):
    d = copy.deepcopy(dados_gov)
    for agr in d["carg"][0]["agr"]:
        for p in agr["par"]:
            for c in p["cand"]:
                c["e"], c["st"] = "n", "Não eleito"
                if c["n"] == "15":
                    c["st"] = "2º turno"
    r = ler_resultado_2026(d, "governador")
    assert r.candidatos[0].nome_urna == "DANIEL VILELA"
    assert r.candidatos[0].situacao == "2º turno"
    assert all(c.situacao != "eleito" for c in r.candidatos)


def test_url_resultado_2026():
    assert url_resultado_2026("governador", "go", "93734").endswith(
        "/6259/dados/go/go93734-c0003-e006259-u.json"
    )
    assert url_resultado_2026("presidente", "br").endswith(
        "/6257/dados/br/br-c0001-e006257-u.json"
    )


@pytest.mark.parametrize(
    "e,st,esperado",
    [
        ("s", "2º turno", "2º turno"),
        ("s", "Eleito", "eleito"),
        ("n", "Não eleito", "não eleito"),
        ("s", "", ""),
        ("n", "", ""),
    ],
)
def test_situacao_por_st(dados_gov, e, st, esperado):
    d = copy.deepcopy(dados_gov)
    cand = d["carg"][0]["agr"][0]["par"][0]["cand"][0]
    cand["e"], cand["st"] = e, st
    r = ler_resultado_2026(d, "governador")
    alvo = next(c for c in r.candidatos if c.numero == int(cand["n"]))
    assert alvo.situacao == esperado


def test_anulados_sub_judice_fora_dos_validos():
    """SE 2026: Dr. Helton (PSOL) teve 37.081 votos anulados sub judice."""
    r = ler_resultado_2026(_carregar("se-c0003-e006259-u.json"), "governador")
    assert r.validos == 1189927
    assert all(c.partido != "PSOL" for c in r.candidatos)
    assert sum(c.votos for c in r.candidatos) == r.validos
    assert [(a.partido, a.votos) for a in r.anulados] == [("PSOL", 37081)]
    assert sum(r.pct(c) for c in r.candidatos) == pytest.approx(100)
    assert r.pct(r.candidatos[0]) == pytest.approx(727291 / 1189927 * 100)


@pytest.mark.parametrize("dvt", ["Anulado", "Anulado sub judice", "Cassado"])
def test_qualquer_dvt_diferente_de_valido_e_anulado(dados_gov, dvt):
    d = copy.deepcopy(dados_gov)
    cand = d["carg"][0]["agr"][0]["par"][0]["cand"][0]
    cand["dvt"] = dvt
    r = ler_resultado_2026(d, "governador")
    assert int(cand["n"]) in {a.numero for a in r.anulados}
    assert int(cand["n"]) not in {c.numero for c in r.candidatos}


def test_dvt_ausente_conta_como_valido(dados_gov):
    d = copy.deepcopy(dados_gov)
    for agr in d["carg"][0]["agr"]:
        for p in agr["par"]:
            for c in p["cand"]:
                c.pop("dvt", None)
    r = ler_resultado_2026(d, "governador")
    assert r.anulados == ()
