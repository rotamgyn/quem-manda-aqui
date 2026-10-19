import json
from datetime import datetime
from zoneinfo import ZoneInfo

from qma_eleicoes.ao_vivo.montar import montar
from qma_eleicoes.modelo import Resultado, VotoCandidato

AGORA = datetime(2026, 10, 25, 18, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))
HORA = "25/10/2026 18:29:00"


def _res(cargo, uf, tse, cands, pct=100.0, validos=None, **extra):
    soma = sum(v for _, _, v in cands)
    return Resultado(
        ano=2026, turno=2, cargo=cargo, uf=uf, municipio_tse=tse, aptos=1000,
        comparecimento=extra.get("comparecimento", 900), abstencao=100, brancos=7, nulos=11,
        validos=soma if validos is None else validos, pct_secoes_totalizadas=pct,
        candidatos=tuple(VotoCandidato(i + 1, n, p, v, "") for i, (n, p, v) in enumerate(cands)),
    )  # fmt: skip


BASE = {
    "municipios": {
        "93734": {"uf": "GO", "ibge": "5208707", "nome": "GOIÂNIA", "slug": "goiania",
                  "t2_2022": {"validos": 100, "partidos": {"PT": 40.0, "PL": 60.0}}},
        "11118": {"uf": "DF", "ibge": "5300108", "nome": "BRASÍLIA", "slug": "brasilia",
                  "t2_2022": None},
        "22222": {"uf": "GO", "ibge": "5200050", "nome": "ABADIA", "slug": "abadia",
                  "t2_2022": None},
    },
    "agregados_2022_t2": {
        "presidente": {
            "BR": {"validos": 1000, "votos": {"PT": 480, "PL": 520}, "partidos": {"PT": 48.0, "PL": 52.0}},
            "GO": {"validos": 100, "votos": {"PT": 40, "PL": 60}, "partidos": {"PT": 40.0, "PL": 60.0}},
        },
        "governador": {},
    },
}  # fmt: skip


def _montar(resultados, horarios=None, andamento=None):
    h = horarios if horarios is not None else {k: HORA for k in resultados}
    return montar(resultados, h, BASE, agora=AGORA, andamento=andamento or {})


def test_estado_tem_numeros_oficiais_sem_soma():
    br = _res("presidente", "BR", None, [("A", "PT", 4_567_891), ("B", "PL", 4_000_000)], pct=87.65)
    go = _res("presidente", "GO", None, [("A", "PT", 1), ("B", "PL", 2)], pct=50.0)
    saida = _montar(
        {("presidente", "BR", None): br, ("presidente", "GO", None): go},
        andamento={"BR": {"and": "p", "pst": "87,65"}, "GO": {"and": "p", "pst": "50,00"}},
    )
    estado = saida["ao-vivo/estado.json"]
    b = estado["presidente"]["br"]
    assert estado["atualizado_em"] == "2026-10-25T18:30:00-03:00"
    assert b["horario_tse"] == HORA and b["pct_secoes"] == 87.65
    assert [(c["partido"], c["votos"], c["pct"]) for c in b["candidatos"]] == [
        ("PT", 4_567_891, 53.31), ("PL", 4_000_000, 46.69)
    ]  # fmt: skip
    assert (b["comparecimento"], b["abstencao"], b["brancos"], b["nulos"]) == (900, 100, 7, 11)
    assert estado["andamento"] == {"br": 87.65, "go": 50.0}
    assert set(estado["presidente"]["ufs"]) == {"go"}
    assert "projecao" not in estado and "erro_ultimo_ciclo" not in estado
    json.dumps(saida, ensure_ascii=False)


def test_municipio_sem_apuracao():
    zero = _res("presidente", "GO", "22222", [("A", "PT", 0), ("B", "PL", 0)], pct=0.0)
    saida = _montar({("presidente", "GO", "22222"): zero})
    lista = saida["ao-vivo/municipios/go.json"]
    assert [m["tse"] for m in lista] == ["22222", "93734"]  # ordem por código TSE
    for m in lista:
        assert m["status"] == "aguardando"
        assert m["partidos"] is None and m["vencedor"] is None and m["delta_vs_2022"] is None
    assert lista[1]["horario_tse"] is None and lista[1]["pct_secoes"] == 0
    assert lista[0]["ibge"] == "5200050"


def test_municipio_parcial_completo_empate_e_delta():
    parcial = _res("presidente", "GO", "93734", [("A", "PT", 55), ("B", "PL", 45)], pct=40.0)
    saida = _montar({("presidente", "GO", "93734"): parcial})
    m = next(x for x in saida["ao-vivo/municipios/go.json"] if x["tse"] == "93734")
    assert m["status"] == "parcial" and m["vencedor"] == "PT"
    assert m["partidos"] == {"PT": 55.0, "PL": 45.0}
    assert m["delta_vs_2022"] == {"PT": 15.0, "PL": -15.0}
    completo = _res("presidente", "GO", "93734", [("A", "PT", 50), ("B", "PL", 50)], pct=100.0)
    m = next(
        x for x in _montar({("presidente", "GO", "93734"): completo})["ao-vivo/municipios/go.json"]
        if x["tse"] == "93734"
    )  # fmt: skip
    assert m["status"] == "completo" and m["vencedor"] is None


def test_comparacao_com_2022_t2():
    br = _res("presidente", "BR", None, [("A", "PT", 530), ("B", "PL", 470)], pct=60.0)
    saida = _montar({("presidente", "BR", None): br})
    comp = saida["ao-vivo/estado.json"]["presidente"]["br"]["comparacao_2022"]
    assert comp["partidos"] == [
        {"partido": "PT", "pct_2022": 48.0, "pct_2026": 53.0, "delta_pp": 5.0},
        {"partido": "PL", "pct_2022": 52.0, "pct_2026": 47.0, "delta_pp": -5.0},
    ]  # fmt: skip


def test_governador_so_ufs_com_segundo_turno():
    ac = _res("governador", "AC", None, [("A", "PT", 3), ("B", "PL", 1)], pct=10.0)
    saida = _montar({("governador", "AC", None): ac})
    estado = saida["ao-vivo/estado.json"]
    assert set(estado["governador"]) == {"ac"}
    assert estado["governador"]["ac"]["comparacao_2022"] is None
    assert estado["presidente"]["br"] is None
