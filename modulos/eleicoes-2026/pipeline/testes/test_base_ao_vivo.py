from qma_comum.municipios import Municipio
from qma_eleicoes.base_ao_vivo import gerar_base, porte
from qma_eleicoes.modelo import Resultado, VotoCandidato


def _res(ano, turno, uf, tse, aptos, cands, cargo="presidente"):
    validos = sum(v for _, _, v in cands)
    return Resultado(
        ano=ano, turno=turno, cargo=cargo, uf=uf, municipio_tse=tse, aptos=aptos,
        comparecimento=validos + 10, abstencao=aptos - validos - 10, brancos=5, nulos=5,
        validos=validos, pct_secoes_totalizadas=100.0,
        candidatos=tuple(VotoCandidato(i, n, p, v, "") for i, (n, p, v) in enumerate(cands)),
    )  # fmt: skip


def test_base_tem_todos_os_municipios():
    ms = [Municipio(f"{i:05d}", f"{1000000 + i}", f"CIDADE {i}", "SP", False, f"c{i}") for i in range(5571)]
    ms.append(Municipio("99999", None, "EXTERIOR", "ZZ", False, "ext"))
    base = gerar_base([], [], ms)
    assert len(base["municipios"]) == 5571
    assert "99999" not in base["municipios"]


def test_base_sem_2022_e_null():
    m = Municipio("01120", "1200013", "ACRELÂNDIA", "AC", False, "acrelandia")
    r26 = _res(2026, 1, "AC", "01120", 8000, [("A", "PT", 60), ("B", "PL", 40)])
    item = gerar_base([], [r26], [m])["municipios"]["01120"]
    assert item["t2_2022"] is None
    assert item["porte"] == "ate10k" and item["aptos_2026"] == 8000
    assert item["t1_2026"] == {"comparecimento": 110, "validos": 100, "partidos": {"PT": 60.0, "PL": 40.0}}


def test_2022_usa_equivalencias_e_arredonda():
    m = Municipio("01120", "1200013", "ACRELÂNDIA", "AC", False, "acrelandia")
    r22 = _res(2022, 2, "AC", "01120", 8000, [("A", "PTB", 1), ("B", "PATRIOTA", 1), ("C", "PT", 1)])
    r26 = _res(2026, 1, "AC", "01120", 60000, [("A", "PT", 1)])
    item = gerar_base([r22], [r26], [m], {"PTB": "PRD", "PATRIOTA": "PRD"})["municipios"]["01120"]
    assert item["t2_2022"] == {"validos": 3, "partidos": {"PRD": 66.67, "PT": 33.33}}
    assert item["porte"] == "50a200k"


def test_faixas_de_porte():
    assert [porte(n) for n in (10000, 10001, 50000, 50001, 200000, 200001)] == [
        "ate10k", "10a50k", "10a50k", "50a200k", "50a200k", "mais200k",
    ]  # fmt: skip


def test_agregados_2022_t2_por_br_e_uf():
    m = Municipio("01120", "1200013", "ACRELÂNDIA", "AC", False, "acrelandia")
    br = _res(2022, 2, "BR", None, 100, [("A", "PTB", 2), ("B", "PT", 2), ("C", "PATRIOTA", 4)])
    gov = _res(2022, 2, "AC", None, 100, [("A", "PL", 3), ("B", "PT", 1)], cargo="governador")
    mun = _res(2022, 2, "AC", "01120", 100, [("A", "PL", 1)], cargo="governador")
    base = gerar_base([br, gov, mun], [], [m], {"PTB": "PRD", "PATRIOTA": "PRD"})
    ag = base["agregados_2022_t2"]
    assert ag["presidente"]["BR"] == {
        "validos": 8, "votos": {"PRD": 6, "PT": 2}, "partidos": {"PRD": 75.0, "PT": 25.0}
    }
    assert ag["governador"] == {
        "AC": {"validos": 4, "votos": {"PL": 3, "PT": 1}, "partidos": {"PL": 75.0, "PT": 25.0}}
    }
