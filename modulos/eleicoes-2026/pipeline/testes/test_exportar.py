import json
from datetime import datetime, timezone

import pytest

from qma_comum.municipios import Municipio
from qma_eleicoes import __main__ as cli
from qma_eleicoes.conferencia import ErroConferencia
from qma_eleicoes.exportar import exportar, meta_de
from qma_eleicoes.modelo import Resultado, VotoCandidato

MUNICIPIOS = [
    Municipio("93734", "5208707", "GOIÂNIA", "GO", True, "goiania"),
    Municipio("11111", "5201108", "ANÁPOLIS", "GO", False, "anapolis"),
    Municipio("11118", "5300108", "BRASÍLIA", "DF", True, "brasilia"),
    Municipio("99999", None, "BUENOS AIRES", "ZZ", False, "buenos-aires"),
]
UFS = {"GO": "GOIÁS", "DF": "DISTRITO FEDERAL", "ZZ": "EXTERIOR"}


def _res(ano, cargo, uf, mun, v22, v13, aptos=1000):
    cands = (VotoCandidato(22, "A", "PL", v22, ""), VotoCandidato(13, "B", "PT", v13, ""))
    validos = v22 + v13
    return Resultado(
        ano=ano, turno=1, cargo=cargo, uf=uf, municipio_tse=mun, aptos=aptos,
        comparecimento=validos, abstencao=aptos - validos, brancos=0, nulos=0, validos=validos,
        pct_secoes_totalizadas=99.9166, candidatos=cands,
    )  # fmt: skip


def _dados():
    """Resultados sintéticos; Anápolis (11111) não existe em 2022."""
    r22, r26 = [], []
    for ano, lista, d in ((2022, r22, 0), (2026, r26, 100)):
        lista.append(_res(ano, "presidente", "BR", None, 500 + d, 400))
        for uf in ("GO", "DF", "ZZ"):
            lista.append(_res(ano, "presidente", uf, None, 300 + d, 200))
            if uf != "ZZ":
                lista.append(_res(ano, "governador", uf, None, 300, 200 + d))
        for m in MUNICIPIOS:
            lista.append(_res(ano, "presidente", m.uf, m.tse, 100 + d, 100))
            if m.uf != "ZZ":
                lista.append(_res(ano, "governador", m.uf, m.tse, 100, 100 + d))
    return [r for r in r22 if r.municipio_tse != "11111"], r26


def _ler(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_formato_municipio_uf(tmp_path):
    r22, r26 = _dados()
    e = tmp_path / "e"
    exportar(MUNICIPIOS, UFS, r22, r26, {}, {"gerado_em": "x"}, e)

    go = _ler(e / "municipios" / "go.json")
    assert list(go) == ["uf", "municipios"] and go["uf"] == "GO"
    assert sorted(go["municipios"][0]) == sorted(
        ["tse", "ibge", "nome", "slug", "capital", "presidente", "governador"]
    )
    zz = _ler(e / "municipios" / "zz.json")
    assert "governador" not in zz["municipios"][0] and "presidente" in zz["municipios"][0]
    assert len(list((e / "municipios").iterdir())) == 3

    goiania = next(m for m in go["municipios"] if m["tse"] == "93734")["presidente"]
    assert goiania["r2026"]["candidatos"][0]["pct"] == 66.67
    assert goiania["volatilidade"] == 16.67
    sem22 = next(m for m in go["municipios"] if m["tse"] == "11111")["presidente"]
    assert sem22["r2022"] is None and sem22["volatilidade"] is None

    br = _ler(e / "comparacoes" / "br-presidente.json")
    assert br["nome"] == "Brasil" and br["r2026"]["pct_secoes_totalizadas"] == 99.92
    assert _ler(e / "comparacoes" / "go-governador.json")["nome"] == "GOIÁS"
    assert (e / "comparacoes" / "zz-presidente.json").exists()
    assert not (e / "comparacoes" / "br-governador.json").exists()
    assert not (e / "comparacoes" / "zz-governador.json").exists()
    assert "\\u" not in (e / "municipios" / "go.json").read_text(encoding="utf-8")
    assert _ler(e / "meta.json") == {"gerado_em": "x"}


def test_ranking_ordenado_sem_exterior_com_aptos(tmp_path):
    r22, r26 = _dados()
    r26 = [  # Brasília muda mais que Goiânia e tem 777 aptos
        _res(2026, "presidente", "DF", "11118", 300, 100, aptos=777)
        if (r.cargo, r.municipio_tse) == ("presidente", "11118")
        else r
        for r in r26
    ]
    exportar(MUNICIPIOS, UFS, r22, r26, {}, {}, tmp_path / "e")
    rk = _ler(tmp_path / "e" / "ranking-presidente.json")
    assert [r["tse"] for r in rk] == ["11118", "93734"]  # sem Anápolis (sem 2022) nem exterior
    assert sorted(rk[0]) == sorted(
        ["tse", "nome", "uf", "slug", "aptos", "volatilidade", "vencedor_2022", "vencedor_2026", "virou"]
    )
    assert rk[0]["aptos"] == 777
    assert rk[0]["volatilidade"] > rk[1]["volatilidade"]


def test_anulados_exportados_sem_pct():
    from dataclasses import replace

    from qma_eleicoes.comparacao import comparar
    from qma_eleicoes.exportar import serializar

    r = replace(
        _res(2026, "governador", "SE", None, 600, 400),
        anulados=(VotoCandidato(50, "C", "PSOL", 37, ""),),
    )
    d = serializar(comparar(None, r, {}))["r2026"]
    assert list(d["anulados"]) == [
        {"numero": 50, "nome_urna": "C", "partido": "PSOL", "votos": 37, "situacao": ""}
    ]
    assert [c["pct"] for c in d["candidatos"]] == [60.0, 40.0]
    assert d["votos_anulados"] == 37


def test_meta():
    br = _dados()[1][0]
    m = meta_de({"dg": "04/10/2026", "hg": "22:30:15"}, br, datetime(2026, 10, 5, 3, 0, tzinfo=timezone.utc))
    assert m == {
        "gerado_em": "2026-10-05T00:00:00-03:00",
        "fonte_2026_dg_hg": "04/10/2026 22:30:15",
        "pct_secoes_br": 99.92,
    }


def test_falha_no_meio_da_exportacao_preserva_pasta(tmp_path):
    destino = tmp_path / "e"
    destino.mkdir()
    (destino / "velho.json").write_text("{}")
    r22, r26 = _dados()
    with pytest.raises(TypeError):  # meta não serializável
        exportar(MUNICIPIOS, UFS, r22, r26, {}, {"x": object()}, destino)
    assert [p.name for p in destino.iterdir()] == ["velho.json"]
    assert [p.name for p in tmp_path.iterdir()] == ["e"]


def test_falha_de_conferencia_nao_altera_dados(tmp_path, monkeypatch):
    raiz = tmp_path / "dados"
    (raiz / "eleicoes-2026").mkdir(parents=True)
    (raiz / "eleicoes-2026" / "velho.json").write_text("{}")
    r22, r26 = _dados()
    r22 = [r for r in r22 if r.uf != "BR"]
    r22.append(_res(2022, "presidente", "BR", None, 51_072_345, 57_259_504))
    r26[1] = _res(2026, "presidente", "GO", None, 1, 1)  # agregado da UF diverge dos municípios
    monkeypatch.setattr(cli, "validar_universo", lambda m: None)
    monkeypatch.setattr(cli, "ler_config_municipios", lambda c: MUNICIPIOS)

    with pytest.raises(ErroConferencia):
        cli.gerar(
            raiz=raiz,
            _baixar_json=lambda url, **kw: {"abr": []},
            _malhas=lambda ufs, destino: None,
            _arquivos_2022=lambda: ([], []),
            _ler_2022=lambda v, d, turno: r22,
            _coletar=lambda m, forcar: r26,
            _equivalencias=lambda: {},
        )
    assert [p.name for p in (raiz / "eleicoes-2026").iterdir()] == ["velho.json"]
    assert (raiz / "comum" / "municipios.json").exists()  # comum pode ser escrito antes do gate


def test_totais_2022_oficiais():
    cli.verificar_totais_2022([_res(2022, "presidente", "BR", None, 51_072_345, 57_259_504)])
    with pytest.raises(ErroConferencia, match="candidato 13"):
        cli.verificar_totais_2022([_res(2022, "presidente", "BR", None, 51_072_345, 57_259_503)])


def test_cobertura_2026_lista_faltantes():
    _, r26 = _dados()
    cli.verificar_cobertura_2026(MUNICIPIOS, r26)
    sem = [r for r in r26 if r.municipio_tse != "93734"]
    with pytest.raises(ErroConferencia, match="93734 GOIÂNIA"):
        cli.verificar_cobertura_2026(MUNICIPIOS, sem)
