import copy
import json
from pathlib import Path

from qma_comum.http import ErroDownload
from qma_comum.municipios import Municipio
from qma_eleicoes.ao_vivo.coleta import Coletor, ufs_governador_de
from qma_eleicoes.config import ELEICAO_2026_T2, url_andamento_2026, url_resultado_2026

AMOSTRAS = Path(__file__).parent / "amostras"


def _carregar(nome: str) -> dict:
    return json.loads((AMOSTRAS / nome).read_text(encoding="utf-8-sig"))


BR = _carregar("br-c0001-e006257-u.json")
UF = _carregar("go-c0003-e006259-u.json")
MUN = _carregar("go93734-c0001-e006257-u.json")

MUNICIPIOS = [
    Municipio("93734", "5208707", "GOIÂNIA", "GO", True, "goiania"),
    Municipio("11118", "5300108", "BRASÍLIA", "DF", True, "brasilia"),
    Municipio("99999", None, "BUENOS AIRES", "ZZ", False, "buenos-aires"),
]


def _escopo(url: str) -> str:
    return url.rsplit("/", 1)[1].split("-")[0]


class Servidor:
    """Fake de `_baixar`: gera cada arquivo a partir das amostras; `idg` e % ajustáveis."""

    def __init__(self):
        self.chamadas: list[str] = []
        self.idg = "1"
        self.pct: dict[str, str] = {}  # prefixo do nome do arquivo → pstn
        self.falhas: dict[str, Exception] = {}  # sufixo da URL → erro

    def __call__(self, url, **kw):
        assert kw.get("forcar") is True
        self.chamadas.append(url)
        for sufixo, erro in self.falhas.items():
            if url.endswith(sufixo):
                raise erro
        if url == url_andamento_2026("6258"):
            return {"abr": [{"cdabr": "br", "and": "p", "s": {"pst": "10,00"}},
                            {"cdabr": "go", "and": "p", "s": {"pst": "5,00"}}]}  # fmt: skip
        nome = url.rsplit("/", 1)[1]
        escopo = _escopo(url)
        cargo = "1" if "-c0001-" in url else "3"
        if escopo == "br":
            d = copy.deepcopy(BR)
        elif len(escopo) > 2:
            d = copy.deepcopy(MUN)
            d["cdabr"] = escopo[2:]
        else:
            d = copy.deepcopy(UF)
            d["cdabr"] = escopo
        d["carg"][0]["cd"] = cargo
        d["idg"] = self.idg
        d["ele"] = "6258" if cargo == "1" else "6260"
        d["t"] = "2"
        d["s"]["pstn"] = next((v for k, v in self.pct.items() if nome.startswith(k)), "50")
        return d

    def municipais(self) -> list[str]:
        return [u for u in self.chamadas if len(_escopo(u)) > 2 and "-ab." not in u and "/br/" not in u]


def _coletor(srv, ufs=("DF",), **kw):
    return Coletor(MUNICIPIOS, list(ufs), _baixar=srv, **kw)


def test_ciclo_baixa_fixos_e_municipais():
    srv = Servidor()
    rel = _coletor(srv).ciclo()
    assert url_andamento_2026("6258") in srv.chamadas
    for uf in ("br", "go", "df", "zz"):
        assert url_resultado_2026("presidente", uf, None, "6258") in srv.chamadas
    assert url_resultado_2026("governador", "df", None, "6260") in srv.chamadas
    assert url_resultado_2026("governador", "go", None, "6260") not in srv.chamadas
    # presidente: os 3 municípios (inclui exterior); governador: só o do DF
    assert len(srv.municipais()) == 4
    assert url_resultado_2026("governador", "go", "93734", "6260") not in srv.chamadas
    assert rel.erros == [] and rel.alterados + 1 == rel.baixados == len(srv.chamadas)  # +1 = andamento


def test_resultados_horarios_e_andamento():
    srv = Servidor()
    c = _coletor(srv)
    c.ciclo()
    r = c.resultados[("presidente", "GO", "93734")]
    assert r.turno == 2 and r.municipio_tse == "93734"
    assert c.horarios[("presidente", "GO", "93734")] == f"{MUN['dg']} {MUN['hg']}"
    assert c.andamento["BR"] == {"and": "p", "pst": "10,00"}
    assert ("presidente", "ZZ", "99999") in c.resultados
    assert ("governador", "DF", "11118") in c.resultados
    assert ("presidente", "BR", None) in c.resultados


def test_idg_igual_nao_reprocessa():
    srv = Servidor()
    c = _coletor(srv, ufs=())
    assert c.ciclo().alterados > 0
    rel = c.ciclo()
    assert rel.alterados == 0 and rel.baixados > 0
    srv.idg = "2"
    assert c.ciclo().alterados > 0


def test_pula_municipio_100():
    srv = Servidor()
    srv.pct = {"go93734-c0001": "100"}
    c = _coletor(srv, ufs=())
    c.ciclo()
    srv.chamadas.clear()
    c.ciclo()
    assert url_resultado_2026("presidente", "go", "93734", "6258") not in srv.chamadas
    assert url_resultado_2026("presidente", "df", "11118", "6258") in srv.chamadas


def test_fila_prioriza_incompletos():
    srv = Servidor()
    srv.pct = {"df11118-c0001": "100", "go93734-c0001": "100"}
    c = _coletor(srv, ufs=(), max_por_ciclo=1)
    c.ciclo()  # DF chega a 100%
    c.ciclo()  # GO chega a 100%
    c.ciclo()  # ZZ, 50%
    srv.chamadas.clear()
    c.ciclo()
    assert [_escopo(u) for u in srv.municipais()] == ["zz99999"]


def test_respeita_max_por_ciclo_e_circula():
    srv = Servidor()
    c = _coletor(srv, ufs=(), max_por_ciclo=2)
    c.ciclo()
    primeiro = srv.municipais()
    assert len(primeiro) == 2
    srv.chamadas.clear()
    c.ciclo()
    segundo = srv.municipais()
    assert len(segundo) == 2 and segundo[0] not in primeiro  # continua de onde parou
    assert segundo[1] == primeiro[0]  # e dá a volta na fila (3 municípios)


def test_erro_vai_para_o_relatorio_sem_abortar():
    srv = Servidor()
    url = url_resultado_2026("presidente", "go", "93734", "6258")
    srv.falhas["go93734-c0001-e006258-u.json"] = ErroDownload(url, 500)
    srv.falhas["df-c0001-e006258-u.json"] = ValueError("json inválido")
    c = _coletor(srv, ufs=())
    rel = c.ciclo()
    assert len(rel.erros) == 2
    assert any(url in e for e in rel.erros)
    assert ("presidente", "GO", "93734") not in c.resultados
    assert ("presidente", "DF", "11118") in c.resultados  # o ciclo seguiu adiante
    assert ("presidente", "BR", None) in c.resultados


def test_ufs_governador_le_do_config():
    config = {"abr": [{"cd": "rn", "mu": [{"cd": "1"}]}, {"cd": "ac", "mu": [{"cd": "2"}]}, {"cd": "sp", "mu": []}]}
    assert ufs_governador_de(config) == ["AC", "RN"]
    assert ELEICAO_2026_T2 == {"presidente": "6258", "governador": "6260"}
