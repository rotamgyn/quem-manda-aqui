from __future__ import annotations

from dataclasses import replace

import pytest

from qma_eleicoes.comparacao import carregar_equivalencias, comparar
from qma_eleicoes.modelo import Resultado, VotoCandidato


def _res(ano, votos: dict[str, int], pct_secoes=100.0, validos=None, cargo="presidente"):
    cands = tuple(
        VotoCandidato(numero=i + 10, nome_urna=p, partido=p, votos=v, situacao="")
        for i, (p, v) in enumerate(sorted(votos.items(), key=lambda x: -x[1]))
    )
    total = sum(votos.values()) if validos is None else validos
    return Resultado(
        ano=ano, turno=1, cargo=cargo, uf="GO", municipio_tse="93734",
        aptos=1000, comparecimento=900, abstencao=100, brancos=0, nulos=0,
        validos=total, pct_secoes_totalizadas=pct_secoes, candidatos=cands,
    )


def _linha(c, partido):
    return next(l for l in c.partidos if l.partido == partido)


def test_delta_simples():
    c = comparar(_res(2022, {"PT": 40, "PL": 60}), _res(2026, {"PT": 30, "PL": 70}), {})
    assert _linha(c, "PT").delta_pp == pytest.approx(-10)
    assert _linha(c, "PL").delta_pp == pytest.approx(10)
    assert c.volatilidade == pytest.approx(10)
    assert c.vencedor_2022 == "PL" and c.vencedor_2026 == "PL"
    assert c.virou is False
    assert [l.partido for l in c.partidos] == ["PL", "PT"]


def test_virada():
    c = comparar(_res(2022, {"PT": 60, "PL": 40}), _res(2026, {"PT": 30, "PL": 70}), {})
    assert (c.vencedor_2022, c.vencedor_2026) == ("PT", "PL")
    assert c.virou is True


def test_partido_so_em_2026():
    c = comparar(_res(2022, {"PT": 50, "PL": 50}), _res(2026, {"PT": 40, "PL": 40, "MISSAO": 20}), {})
    m = _linha(c, "MISSAO")
    assert m.pct_2022 is None and m.delta_pp is None and m.pct_2026 == pytest.approx(20)
    # |40-50|+|40-50|+|20-0| = 40 -> 20
    assert c.volatilidade == pytest.approx(20)


def test_partido_so_em_2022_vai_por_ultimo():
    c = comparar(_res(2022, {"PT": 50, "XX": 50}), _res(2026, {"PT": 100}), {})
    x = _linha(c, "XX")
    assert x.pct_2026 is None and x.delta_pp is None
    assert c.partidos[-1].partido == "XX"
    assert c.volatilidade == pytest.approx(50)


def test_equivalencia_aplicada():
    c = comparar(_res(2022, {"PTB": 30, "PT": 70}), _res(2026, {"PRD": 35, "PT": 65}), {"PTB": "PRD"})
    assert "PTB" not in [l.partido for l in c.partidos]
    assert _linha(c, "PRD").pct_2022 == pytest.approx(30)
    assert _linha(c, "PRD").delta_pp == pytest.approx(5)


def test_equivalencia_soma_partidos_fundidos():
    c = comparar(
        _res(2022, {"PTB": 10, "PATRIOTA": 10, "PT": 80}),
        _res(2026, {"PRD": 20, "PT": 80}),
        {"PTB": "PRD", "PATRIOTA": "PRD"},
    )
    assert _linha(c, "PRD").pct_2022 == pytest.approx(20)
    assert c.volatilidade == pytest.approx(0)


def test_comparacao_sem_2022():
    c = comparar(None, _res(2026, {"PT": 40, "PL": 60}), {})
    assert c.volatilidade is None and c.virou is None and c.vencedor_2022 is None
    assert c.vencedor_2026 == "PL"
    assert all(l.pct_2022 is None and l.delta_pp is None for l in c.partidos)
    assert c.uf == "GO" and c.municipio_tse == "93734" and c.cargo == "presidente"


def test_sem_2026():
    c = comparar(_res(2022, {"PT": 40, "PL": 60}), None, {})
    assert c.volatilidade is None and c.virou is None
    assert c.apuracao_completa is False


def test_ambos_none_levanta():
    with pytest.raises(ValueError):
        comparar(None, None, {})


def test_validos_zero():
    r26 = _res(2026, {"PT": 0, "PL": 0}, validos=0)
    c = comparar(_res(2022, {"PT": 40, "PL": 60}), r26, {})
    assert all(l.pct_2026 is None and l.delta_pp is None for l in c.partidos)
    assert c.volatilidade is None and c.virou is None and c.vencedor_2026 is None


def test_empate_sem_vencedor():
    c = comparar(_res(2022, {"PT": 50, "PL": 50}), _res(2026, {"PT": 30, "PL": 70}), {})
    assert c.vencedor_2022 is None and c.virou is None


def test_apuracao_incompleta():
    c = comparar(_res(2022, {"PT": 1}), _res(2026, {"PT": 1}, pct_secoes=99.9), {})
    assert c.apuracao_completa is False
    c2 = comparar(_res(2022, {"PT": 1}), _res(2026, {"PT": 1}), {})
    assert c2.apuracao_completa is True


def test_vencedor_ignora_situacao_nacional():
    r = _res(2026, {"PT": 40, "PL": 60})
    r = replace(r, candidatos=tuple(
        replace(v, situacao="eleito" if v.partido == "PT" else "não eleito") for v in r.candidatos
    ))
    c = comparar(None, r, {})
    assert c.vencedor_2026 == "PL"


def test_equivalencias_csv_real():
    eq = carregar_equivalencias()
    assert eq["PTB"] == "PRD" and eq["PATRIOTA"] == "PRD"
    assert eq["PROS"] == "SOLIDARIEDADE" and eq["PSC"] == "PODE"


def test_carregar_equivalencias_caminho(tmp_path):
    f = tmp_path / "e.csv"
    f.write_text("sigla_origem,sigla_destino,nota\nAA,BB,fusão\n", encoding="utf-8")
    assert carregar_equivalencias(f) == {"AA": "BB"}
