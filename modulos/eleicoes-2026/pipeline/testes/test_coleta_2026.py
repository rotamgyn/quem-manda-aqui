import copy
import json
import logging
from pathlib import Path

import pytest

from qma_comum.http import ErroDownload
from qma_comum.municipios import Municipio
from qma_eleicoes.coleta_2026 import coletar_2026
from qma_eleicoes.config import url_resultado_2026

AMOSTRAS = Path(__file__).parent / "amostras"


def _amostra(nome: str, cd_cargo: str) -> dict:
    dados = json.loads((AMOSTRAS / nome).read_text(encoding="utf-8"))
    dados = copy.deepcopy(dados)
    dados["carg"] = [c for c in dados["carg"]]
    dados["carg"][0]["cd"] = cd_cargo
    return dados


MUNICIPIOS = [
    Municipio("93734", "5208707", "GOIÂNIA", "GO", True, "goiania"),
    Municipio("11118", "5300108", "BRASÍLIA", "DF", True, "brasilia"),
    Municipio("99999", None, "BUENOS AIRES", "ZZ", False, "buenos-aires"),
]


def _fake(ausentes=()):
    """Devolve (_baixar, chamadas); responde com as amostras salvas, dependendo da URL."""
    chamadas: list[str] = []

    def _baixar(url, **kw):
        chamadas.append(url)
        if url in ausentes:
            raise ErroDownload(url, 404)
        cd = "1" if "-c0001-" in url else "3"
        if "/br/" in url:
            return _amostra("br-c0001-e006257-u.json", cd)
        nome_arquivo = url.rsplit("/", 1)[1]
        partes = nome_arquivo.split("-")[0]
        if len(partes) > 2:  # uf + código do município
            d = _amostra("go93734-c0001-e006257-u.json", cd)
            d["cdabr"] = partes[2:]
            return d
        d = _amostra("go-c0003-e006259-u.json", cd)
        d["cdabr"] = partes
        return d

    return _baixar, chamadas


def test_presidente_inclui_exterior():
    baixar, chamadas = _fake()
    res = coletar_2026(MUNICIPIOS, _baixar=baixar)
    pres = [r for r in res if r.cargo == "presidente"]
    assert pres[0].uf == "BR"
    assert url_resultado_2026("presidente", "zz") in chamadas
    assert url_resultado_2026("presidente", "zz", "99999") in chamadas
    assert url_resultado_2026("presidente", "br") in chamadas
    assert {r.uf for r in pres} == {"BR", "GO", "DF", "ZZ"}
    # BR, 3 UFs, 3 municípios
    assert len(pres) == 7


def test_governador_exclui_exterior():
    baixar, chamadas = _fake()
    res = coletar_2026(MUNICIPIOS, _baixar=baixar)
    gov = [r for r in res if r.cargo == "governador"]
    assert {r.uf for r in gov} == {"GO", "DF"}
    assert len(gov) == 4  # 2 UFs + 2 municípios
    assert not [u for u in chamadas if "/zz/" in u and "-c0003-" in u]
    assert url_resultado_2026("governador", "df") in chamadas


def test_404_em_municipio_nao_interrompe(caplog):
    url = url_resultado_2026("presidente", "go", "93734")
    baixar, _ = _fake(ausentes={url})
    with caplog.at_level(logging.WARNING, logger="qma_eleicoes.coleta"):
        res = coletar_2026(MUNICIPIOS, _baixar=baixar)
    pres_mun = [r for r in res if r.cargo == "presidente" and r.municipio_tse]
    assert {r.municipio_tse for r in pres_mun} == {"11118", "99999"}
    assert url in caplog.text


@pytest.mark.parametrize("uf", ["br", "go"])
def test_404_em_uf_interrompe(uf):
    url = url_resultado_2026("presidente", uf)
    baixar, _ = _fake(ausentes={url})
    with pytest.raises(ErroDownload):
        coletar_2026(MUNICIPIOS, _baixar=baixar)


def test_forcar_e_repassado():
    recebidos = []
    baixar, _ = _fake()

    def espiao(url, **kw):
        recebidos.append(kw)
        return baixar(url, **kw)

    coletar_2026(MUNICIPIOS, forcar=True, _baixar=espiao)
    assert recebidos and all(kw == {"forcar": True} for kw in recebidos)
