import json
from dataclasses import replace
from pathlib import Path

import pytest

from qma_comum.http import baixar_json
from qma_comum.municipios import (
    ErroUniverso,
    Municipio,
    atribuir_slugs,
    gravar_municipios,
    ler_config_municipios,
    slugificar,
    validar_universo,
)

AMOSTRA = Path(__file__).parent / "amostras" / "mun-cm-recorte.json"
URL_REAL = "https://resultados.tse.jus.br/oficial/ele2026/6257/config/mun-e006257-cm.json"


@pytest.fixture(scope="module")
def municipios():
    return ler_config_municipios(json.loads(AMOSTRA.read_text(encoding="utf-8")))


def _mun(tse, nome="X", uf="GO", ibge="5200000", capital=False):
    return Municipio(tse=tse, ibge=ibge, nome=nome, uf=uf, capital=capital, slug="")


def test_le_goiania(municipios):
    goiania = next(m for m in municipios if m.tse == "93734")
    assert goiania.ibge == "5208707"
    assert goiania.uf == "GO"
    assert goiania.capital is True
    assert goiania.nome == "GOIÂNIA"


def test_le_recorte_completo(municipios):
    por_uf = {}
    for m in municipios:
        por_uf[m.uf] = por_uf.get(m.uf, 0) + 1
    assert por_uf == {"AC": 22, "DF": 1, "ZZ": 2, "GO": 246}
    assert sum(m.capital for m in municipios) == 3  # Rio Branco, Brasília, Goiânia


def test_exterior_sem_ibge(municipios):
    exterior = [m for m in municipios if m.uf == "ZZ"]
    assert len(exterior) == 2
    assert all(m.ibge is None for m in exterior)


def test_slug_acentos_e_apostrofo():
    assert slugificar("SÃO JOÃO D'ALIANÇA") == "sao-joao-dalianca"


def test_slug_espacos_e_hifens():
    assert slugificar("ITAPAJÉ DO  OESTE-NOVO") == "itapaje-do-oeste-novo"


def test_slug_homonimo_na_mesma_uf():
    a, b = _mun("11111", "BONITO"), _mun("22222", "BONITO")
    r = atribuir_slugs([a, b])
    assert [m.slug for m in r] == ["bonito", "bonito-22222"]
    assert a.slug == ""  # entrada não é alterada


def test_slug_mesmo_nome_em_ufs_diferentes():
    r = atribuir_slugs([_mun("1", "BONITO", "MS"), _mun("2", "BONITO", "PE")])
    assert [m.slug for m in r] == ["bonito", "bonito"]


def test_slug_exterior_unico(municipios):
    r = atribuir_slugs(municipios)
    slugs = [(m.uf, m.slug) for m in r]
    assert len(set(slugs)) == len(slugs)
    assert all(m.slug for m in r)


def test_gravar_municipios(tmp_path, municipios):
    destino = tmp_path / "sub" / "municipios.json"
    gravar_municipios(atribuir_slugs(municipios), destino)
    lido = json.loads(destino.read_text(encoding="utf-8"))
    assert len(lido) == len(municipios)
    assert set(lido[0]) == {"tse", "ibge", "nome", "uf", "capital", "slug"}
    assert any(o["nome"] == "GOIÂNIA" for o in lido)  # sem escapes \u


def _universo_valido():
    return [_mun(f"{i:05d}", f"M{i}", ibge=f"{1000000 + i}") for i in range(5571)]


def test_validar_universo_ok():
    validar_universo(_universo_valido() + [_mun("99999", "PARIS", "ZZ", ibge=None)])


def test_validar_universo_falha_com_faltante():
    with pytest.raises(ErroUniverso):
        validar_universo(_universo_valido()[:-1])


def test_validar_universo_falha_sem_ibge():
    u = _universo_valido()
    u[0] = replace(u[0], ibge=None)
    with pytest.raises(ErroUniverso):
        validar_universo(u)


def test_validar_universo_falha_ibge_duplicado():
    u = _universo_valido()
    u[1] = replace(u[1], ibge=u[0].ibge)
    with pytest.raises(ErroUniverso):
        validar_universo(u)


@pytest.mark.rede
def test_universo_real():
    municipios = ler_config_municipios(baixar_json(URL_REAL))
    validar_universo(municipios)
    assert sum(m.uf == "ZZ" for m in municipios) == 186
