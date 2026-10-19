import json

import pytest
from botocore.exceptions import ClientError

from qma_eleicoes.ao_vivo.publicar import PublicadorLocal, PublicadorR2

ARQUIVOS = {
    "ao-vivo/estado.json": {"atualizado_em": "x", "nome": "Brasília"},
    "ao-vivo/municipios/go.json": [{"tse": "1"}],
    "ao-vivo/municipios/ac.json": [{"tse": "2"}],
}


class ClienteFalso:
    def __init__(self, controle: bytes | None = None):
        self.puts: list[dict] = []
        self.controle = controle

    def put_object(self, **kw):
        self.puts.append(kw)

    def get_object(self, *, Bucket, Key):
        assert Key == "controle.json"
        if self.controle is None:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "x"}}, "GetObject")
        conteudo = self.controle

        class Corpo:
            def read(self):
                return conteudo

        return {"Body": Corpo()}


def test_ordem_de_publicacao():
    c = ClienteFalso()
    PublicadorR2("bkt", _cliente=c).publicar(ARQUIVOS)
    chaves = [p["Key"] for p in c.puts]
    assert chaves[-1] == "ao-vivo/estado.json"
    assert sorted(chaves[:-1]) == ["ao-vivo/municipios/ac.json", "ao-vivo/municipios/go.json"]
    assert len(chaves) == 3


def test_estado_nao_e_publicado_se_um_arquivo_falha():
    class Falha(ClienteFalso):
        def put_object(self, **kw):
            if kw["Key"].endswith("go.json"):
                raise RuntimeError("R2 fora")
            super().put_object(**kw)

    c = Falha()
    with pytest.raises(RuntimeError):
        PublicadorR2("bkt", _cliente=c).publicar(ARQUIVOS)
    assert "ao-vivo/estado.json" not in [p["Key"] for p in c.puts]


def test_cabecalhos_cache_e_corpo_compacto():
    c = ClienteFalso()
    PublicadorR2("bkt", _cliente=c).publicar(ARQUIVOS)
    for p in c.puts:
        assert p["Bucket"] == "bkt"
        assert p["ContentType"] == "application/json; charset=utf-8"
        assert p["CacheControl"] == "public, max-age=20"
    assert c.puts[-1]["Body"] == '{"atualizado_em":"x","nome":"Brasília"}'.encode("utf-8")


def test_prefixo_vale_para_todas_as_chaves():
    c = ClienteFalso()
    PublicadorR2("bkt", prefixo="ensaio/", _cliente=c).publicar(ARQUIVOS)
    chaves = [p["Key"] for p in c.puts]
    assert chaves[-1] == "ensaio/estado.json"
    assert all(k.startswith("ensaio/") for k in chaves)
    assert "ensaio/municipios/go.json" in chaves


def test_controle_ausente_desliga_projecao():
    assert PublicadorR2("bkt", _cliente=ClienteFalso()).ler_controle() == {"projecao_ligada": False}


def test_controle_na_raiz_mesmo_com_prefixo():
    c = ClienteFalso(json.dumps({"projecao_ligada": True}).encode())
    assert PublicadorR2("bkt", prefixo="ensaio/", _cliente=c).ler_controle() == {
        "projecao_ligada": True
    }


def test_controle_invalido_desliga_projecao():
    c = ClienteFalso(b"{quebrado")
    assert PublicadorR2("bkt", _cliente=c).ler_controle() == {"projecao_ligada": False}


def test_outro_erro_do_r2_na_leitura_do_controle_desliga_projecao_sem_vazar(caplog):
    class Negado(ClienteFalso):
        def get_object(self, **kw):
            raise ConnectionError("falha em https://conta.r2.cloudflarestorage.com/bkt/controle.json")

    r = PublicadorR2("bkt", _cliente=Negado()).ler_controle()
    assert r == {"projecao_ligada": False}
    assert "cloudflarestorage" not in caplog.text and "falha ao ler controle.json" in caplog.text


def test_filtro_oculta_conta_bucket_e_url_no_traceback(caplog, monkeypatch):
    import logging

    monkeypatch.setenv("R2_ACCOUNT_ID", "conta999")
    monkeypatch.setenv("R2_BUCKET", "meu-bucket")
    log = logging.getLogger("qma_eleicoes.ao_vivo")
    try:
        raise OSError("https://conta999.r2.cloudflarestorage.com/meu-bucket/k e meu-bucket")
    except OSError:
        log.exception("erro em conta999")
    assert "conta999" not in caplog.text and "meu-bucket" not in caplog.text
    assert "cloudflarestorage" not in caplog.text and "***" in caplog.text


def test_bundle_do_sistema_fora_do_windows_e_none(monkeypatch):
    from qma_eleicoes.ao_vivo import publicar

    monkeypatch.setattr(publicar.sys, "platform", "linux")
    assert publicar._bundle_do_sistema() is None


def test_publicador_local_grava_as_mesmas_chaves(tmp_path):
    p = PublicadorLocal(tmp_path, prefixo="ensaio/")
    p.publicar(ARQUIVOS)
    estado = (tmp_path / "ensaio" / "estado.json").read_text(encoding="utf-8")
    assert json.loads(estado) == ARQUIVOS["ao-vivo/estado.json"]
    assert (tmp_path / "ensaio" / "municipios" / "go.json").exists()
    assert p.ler_controle() == {"projecao_ligada": False}
    (tmp_path / "controle.json").write_text('{"projecao_ligada": true}', encoding="utf-8")
    assert p.ler_controle() == {"projecao_ligada": True}
