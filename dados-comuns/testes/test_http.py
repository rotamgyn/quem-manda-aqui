import httpx
import pytest

from qma_comum import http
from qma_comum.http import ErroDownload, baixar, baixar_json


class RelogioFalso:
    def __init__(self):
        self.agora = 0.0
        self.esperas = []

    def __call__(self):
        return self.agora

    def dormir(self, segundos):
        self.esperas.append(segundos)
        self.agora += segundos


@pytest.fixture(autouse=True)
def limpa_limitadores():
    http._limitadores.clear()
    yield
    http._limitadores.clear()


@pytest.fixture
def relogio():
    return RelogioFalso()


def cliente(handler):
    chamadas = []

    def embrulho(request):
        chamadas.append(str(request.url))
        return handler(request)

    return httpx.Client(transport=httpx.MockTransport(embrulho)), chamadas


def kw(relogio, tmp_path, c):
    return dict(cache_dir=tmp_path, _cliente=c, _relogio=relogio, _dormir=relogio.dormir)


def test_usa_cache_na_segunda_chamada(tmp_path, relogio):
    c, chamadas = cliente(lambda r: httpx.Response(200, content=b"ola"))
    p1 = baixar("https://exemplo.gov.br/a/b.csv", **kw(relogio, tmp_path, c))
    p2 = baixar("https://exemplo.gov.br/a/b.csv", **kw(relogio, tmp_path, c))
    assert len(chamadas) == 1
    assert p1 == p2
    assert p1.read_bytes() == b"ola"
    assert tmp_path in p1.parents
    assert not list(tmp_path.rglob("*.parcial"))


def test_forcar_baixa_de_novo(tmp_path, relogio):
    c, chamadas = cliente(lambda r: httpx.Response(200, content=b"x"))
    baixar("https://exemplo.gov.br/a.csv", **kw(relogio, tmp_path, c))
    baixar("https://exemplo.gov.br/a.csv", forcar=True, **kw(relogio, tmp_path, c))
    assert len(chamadas) == 2


def test_404_levanta_erro_sem_retentar(tmp_path, relogio):
    c, chamadas = cliente(lambda r: httpx.Response(404))
    with pytest.raises(ErroDownload) as e:
        baixar("https://exemplo.gov.br/nada", **kw(relogio, tmp_path, c))
    assert e.value.status == 404
    assert e.value.url == "https://exemplo.gov.br/nada"
    assert len(chamadas) == 1
    assert not list(tmp_path.rglob("*.parcial"))


def test_5xx_retenta_3_vezes(tmp_path, relogio):
    c, chamadas = cliente(lambda r: httpx.Response(503))
    with pytest.raises(ErroDownload) as e:
        baixar("https://exemplo.gov.br/x", max_por_segundo=1000, **kw(relogio, tmp_path, c))
    assert e.value.status == 503
    assert len(chamadas) == 4  # 1 tentativa + 3 retentativas
    assert [s for s in relogio.esperas if s >= 1] == [1, 2, 4]


def test_5xx_depois_sucesso(tmp_path, relogio):
    respostas = iter([500, 502, 200])
    c, chamadas = cliente(lambda r: httpx.Response(next(respostas), content=b"ok"))
    p = baixar("https://exemplo.gov.br/y", **kw(relogio, tmp_path, c))
    assert p.read_bytes() == b"ok"
    assert len(chamadas) == 3


def test_erro_de_rede_retenta_e_status_none(tmp_path, relogio):
    def falha(request):
        raise httpx.ConnectError("sem rede")

    c, chamadas = cliente(falha)
    with pytest.raises(ErroDownload) as e:
        baixar("https://exemplo.gov.br/z", max_por_segundo=1000, **kw(relogio, tmp_path, c))
    assert e.value.status is None
    assert len(chamadas) == 4


def test_respeita_limite_de_taxa(tmp_path, relogio):
    c, _ = cliente(lambda r: httpx.Response(200, content=b"x"))
    for i in range(5):
        baixar(f"https://exemplo.gov.br/{i}", max_por_segundo=10, **kw(relogio, tmp_path, c))
    assert sum(relogio.esperas) >= 0.4 - 1e-9


def test_url_com_query_gera_caminhos_distintos_e_validos(tmp_path, relogio):
    c, chamadas = cliente(lambda r: httpx.Response(200, content=b"x"))
    p1 = baixar("https://servicodados.ibge.gov.br/api/v1/localidades?orderBy=nome&a=1", **kw(relogio, tmp_path, c))
    p2 = baixar("https://servicodados.ibge.gov.br/api/v1/localidades?orderBy=id", **kw(relogio, tmp_path, c))
    assert p1 != p2
    assert len(chamadas) == 2
    for p in (p1, p2):
        rel = p.relative_to(tmp_path)
        assert not any(ch in str(rel) for ch in '<>:"|?*')


def test_baixar_json_utf8_com_bom(tmp_path, relogio):
    corpo = '﻿{"nome": "SÃO JOÃO"}'.encode("utf-8")
    c, _ = cliente(lambda r: httpx.Response(200, content=corpo))
    assert baixar_json("https://exemplo.gov.br/j.json", **kw(relogio, tmp_path, c)) == {"nome": "SÃO JOÃO"}


def test_envia_user_agent_descritivo(tmp_path, relogio):
    vistos = []

    def h(request):
        vistos.append(request.headers.get("user-agent"))
        return httpx.Response(200, content=b"x")

    http_cliente = http._novo_cliente(httpx.MockTransport(h))
    baixar("https://exemplo.gov.br/ua", **kw(relogio, tmp_path, http_cliente))
    assert vistos == ["QuemMandaAqui/0.1 (+https://quemmandaaqui.com.br)"]


@pytest.mark.parametrize("ordem", [("a", "a/b"), ("a/b", "a")])
def test_url_prefixo_de_outra_nao_colide(tmp_path, relogio, ordem):
    c, chamadas = cliente(lambda r: httpx.Response(200, content=r.url.path.encode()))
    for caminho in ordem:
        p = baixar(f"https://exemplo.gov.br/{caminho}", **kw(relogio, tmp_path, c))
        assert p.read_bytes() == f"/{caminho}".encode()
    assert len(chamadas) == 2


def test_falha_no_meio_do_stream_nao_deixa_parcial(tmp_path, relogio):
    class Quebrado(httpx.SyncByteStream):
        def __iter__(self):
            yield b"abc"
            raise httpx.ReadError("cortou")

    c, chamadas = cliente(lambda r: httpx.Response(200, stream=Quebrado()))
    with pytest.raises(ErroDownload) as e:
        baixar("https://exemplo.gov.br/grande.zip", max_por_segundo=1000, **kw(relogio, tmp_path, c))
    assert e.value.status is None
    assert len(chamadas) == 4
    assert not [p for p in tmp_path.rglob("*") if p.is_file()]
