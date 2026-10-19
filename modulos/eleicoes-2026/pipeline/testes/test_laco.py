import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from test_coleta_ao_vivo import MUNICIPIOS, Servidor

from qma_eleicoes.ao_vivo.coleta import Coletor
from qma_eleicoes.ao_vivo.laco import executar
from qma_eleicoes.ao_vivo.publicar import PublicadorLocal
from qma_eleicoes.config import url_andamento_2026

SP = ZoneInfo("America/Sao_Paulo")
INICIO = datetime(2026, 10, 25, 18, 0, tzinfo=SP)

BASE = {
    "municipios": {
        "93734": {"uf": "GO", "ibge": "5208707", "nome": "GOIÂNIA", "slug": "goiania", "t2_2022": None},
        "11118": {"uf": "DF", "ibge": "5300108", "nome": "BRASÍLIA", "slug": "brasilia", "t2_2022": None},
    },
    "agregados_2022_t2": {"presidente": {}, "governador": {}},
}


class Tempo:
    """Relógio, monotônico e `dormir` falsos; `dormir` avança os dois."""

    def __init__(self):
        self.mono = 1000.0
        self.dormidas: list[float] = []

    def agora(self):
        return INICIO + timedelta(seconds=self.mono - 1000.0)

    def monotonic(self):
        return self.mono

    def dormir(self, s):
        self.dormidas.append(s)
        self.mono += s

    def kw(self):
        return {"_agora": self.agora, "_monotonic": self.monotonic, "_dormir": self.dormir}


class ServidorAndamento(Servidor):
    """Andamento controlável; `quebrar_1a` faz o 1º andamento trazer um `pst` que o `montar` rejeita."""

    def __init__(self, pst_br="10,00", pst_go="5,00", quebrar_1a=False):
        super().__init__()
        self.pst_br, self.pst_go = pst_br, pst_go
        self.quebrar_1a = quebrar_1a

    def __call__(self, url, **kw):
        if url == url_andamento_2026("6258"):
            self.chamadas.append(url)
            pst_br = self.pst_br
            if self.quebrar_1a:
                self.quebrar_1a, pst_br = False, "quebrado"
            return {"abr": [{"cdabr": "br", "and": "p", "s": {"pst": pst_br}},
                            {"cdabr": "go", "and": "p", "s": {"pst": self.pst_go}},
                            {"cdabr": "df", "and": "p", "s": {"pst": self.pst_go}}]}  # fmt: skip
        return super().__call__(url, **kw)


def _estado(pasta):
    return json.loads((pasta / "ao-vivo" / "estado.json").read_text(encoding="utf-8"))


def _rodar(srv, tmp_path, tempo, *, maximo_ciclos, ufs=("DF",), **kw):
    """Roda o laço por `maximo_ciclos` ciclos (via `--ate`) e devolve (publicador, coletor)."""
    coletor = Coletor(MUNICIPIOS, list(ufs), _baixar=srv, _relogio=tempo.monotonic)
    pub = PublicadorLocal(tmp_path)
    ate = INICIO + timedelta(seconds=60 * (maximo_ciclos - 1) + 1)
    n = executar(coletor, BASE, pub, intervalo=60, ate=ate, **tempo.kw(), **kw)
    return pub, coletor, n


def test_publica_a_cada_intervalo_e_para_em_ate(tmp_path):
    tempo = Tempo()
    _, _, n = _rodar(ServidorAndamento(), tmp_path, tempo, maximo_ciclos=3)
    assert n == 3
    assert _estado(tmp_path)["atualizado_em"].startswith("2026-10-25T18:02:00")
    assert (tmp_path / "ao-vivo" / "municipios" / "go.json").exists()


def test_ciclo_sobrevive_a_erro(tmp_path):
    tempo = Tempo()
    srv = ServidorAndamento(quebrar_1a=True)  # `montar` levanta ValueError no 1º ciclo
    coletor = Coletor(MUNICIPIOS, ["DF"], _baixar=srv, _relogio=tempo.monotonic)
    pub = PublicadorLocal(tmp_path)
    publicados = []
    original = pub.publicar

    def espiao(arquivos):
        publicados.append(json.loads(json.dumps(arquivos["ao-vivo/estado.json"])))
        original(arquivos)

    pub.publicar = espiao
    n = executar(
        coletor, BASE, pub, intervalo=60, ate=INICIO + timedelta(seconds=121), **tempo.kw()
    )
    assert n == 3  # o laço seguiu depois do erro
    assert len(publicados) == 2  # o ciclo com erro não publicou nada
    erro = publicados[0]["erro_ultimo_ciclo"]
    assert erro == "18:00 — dados do TSE em formato inesperado"
    assert publicados[0]["arquivos_com_erro"] == 0
    assert "erro_ultimo_ciclo" not in publicados[1]  # o seguinte, limpo, não repete o erro


def test_erro_por_arquivo_nao_e_falha_do_ciclo(tmp_path):
    tempo = Tempo()
    srv = ServidorAndamento()
    srv.falhas["go93734-c0001-e006258-u.json"] = ValueError("json inválido")
    _rodar(srv, tmp_path, tempo, maximo_ciclos=1)
    estado = _estado(tmp_path)
    assert estado["arquivos_com_erro"] == 1
    assert "erro_ultimo_ciclo" not in estado


def test_falha_de_publicacao_nao_mata_o_laco(tmp_path):
    tempo = Tempo()
    coletor = Coletor(MUNICIPIOS, ["DF"], _baixar=ServidorAndamento(), _relogio=tempo.monotonic)
    pub = PublicadorLocal(tmp_path)
    original = pub.publicar
    chamadas = []

    def instavel(arquivos):
        chamadas.append(1)
        if len(chamadas) == 1:
            raise OSError("R2 fora do ar")
        original(arquivos)

    pub.publicar = instavel
    n = executar(
        coletor, BASE, pub, intervalo=60, ate=INICIO + timedelta(seconds=61), **tempo.kw()
    )
    assert n == 2
    assert _estado(tmp_path)["erro_ultimo_ciclo"] == "18:00 — falha na publicação"


def test_termina_com_100(tmp_path):
    tempo = Tempo()
    srv = ServidorAndamento(pst_br="100,00", pst_go="100,00")
    srv.pct = {"": "100"}
    _, _, n = _rodar(srv, tmp_path, tempo, maximo_ciclos=10)
    assert n == 1
    assert _estado(tmp_path)["andamento"]["br"] == 100.0


def test_nao_termina_se_governador_ainda_nao_chegou_a_100(tmp_path):
    tempo = Tempo()
    srv = ServidorAndamento(pst_br="100,00", pst_go="100,00")
    srv.pct = {"df-c0003": "80", "": "100"}  # governador do DF: 80%
    _, _, n = _rodar(srv, tmp_path, tempo, maximo_ciclos=3)
    assert n == 3


def test_nao_termina_com_br_100_e_uf_de_governador_abaixo(tmp_path):
    tempo = Tempo()
    srv = ServidorAndamento(pst_br="100,00", pst_go="99,00")
    srv.pct = {"": "100"}
    _, _, n = _rodar(srv, tmp_path, tempo, maximo_ciclos=2)
    assert n == 2


def test_proximo_ciclo_comeca_apos_o_anterior_terminar(tmp_path):
    """Ruling P2-3: próximo início = início + max(intervalo, duração); nunca sobrepõe."""
    from qma_eleicoes.ao_vivo.coleta import RelatorioCiclo

    tempo = Tempo()
    inicios, prazos = [], []

    class CicloLento:
        resultados, horarios, andamento, ufs_governador = {}, {}, {}, []

        def __init__(self, duracoes):
            self.duracoes = iter(duracoes)

        def ciclo(self, prazo=None):
            inicios.append(tempo.mono)
            prazos.append(prazo)
            tempo.mono += next(self.duracoes)
            return RelatorioCiclo()

    n = executar(
        CicloLento([10, 100, 59.5, 5]), BASE, PublicadorLocal(tmp_path), intervalo=60,
        ate=INICIO + timedelta(seconds=221), **tempo.kw(),
    )  # fmt: skip
    assert n == 4
    assert inicios == [1000.0, 1060.0, 1160.0, 1220.0]
    assert tempo.dormidas == [50.0, 0.5]  # o ciclo de 100 s não dorme nem atropela o seguinte
    assert prazos == [1060.0, 1120.0, 1220.0, 1280.0]  # prazo = início + intervalo


def test_hook_de_projecao_e_chamado_e_inserido(tmp_path):
    tempo = Tempo()
    recebido = {}

    def projetar(estado, controle, agora):
        recebido.update(controle=controle, agora=agora, chaves=set(estado))
        return {"texto": "bloco"}

    _rodar(ServidorAndamento(), tmp_path, tempo, maximo_ciclos=1, projetar_bloco=projetar)
    assert recebido["controle"] == {"projecao_ligada": False}
    assert _estado(tmp_path)["projecao"] == {"texto": "bloco"}


def test_sem_hook_nao_ha_bloco_projecao(tmp_path):
    _rodar(ServidorAndamento(), tmp_path, Tempo(), maximo_ciclos=1)
    assert "projecao" not in _estado(tmp_path)


def test_cli_simular_usa_o_baixar_do_simulador(tmp_path):
    from qma_eleicoes.ao_vivo.__main__ import main
    from qma_eleicoes.config import URL_CONFIG_GOVERNADOR_T2

    pedidos = []

    def baixar(url, **kw):
        pedidos.append(url)
        raise RuntimeError("parar")

    dados = tmp_path / "dados"
    (dados / "comum").mkdir(parents=True)
    (dados / "eleicoes-2026").mkdir()
    (dados / "comum" / "municipios.json").write_text("[]", encoding="utf-8")
    (dados / "eleicoes-2026" / "base-ao-vivo.json").write_text("{}", encoding="utf-8")
    import pytest

    with pytest.raises(RuntimeError, match="parar"):
        main(
            ["--simular", "--local", str(tmp_path / "saida"), "--dados", str(dados)],
            _baixar_simulado=lambda municipios: baixar,
        )
    assert pedidos == [URL_CONFIG_GOVERNADOR_T2]


def test_excecao_com_url_do_r2_nao_vaza_para_estado_nem_log(tmp_path, caplog, monkeypatch):
    monkeypatch.setenv("R2_ACCOUNT_ID", "conta123")
    monkeypatch.setenv("R2_BUCKET", "bucket-secreto")
    tempo = Tempo()
    coletor = Coletor(MUNICIPIOS, ["DF"], _baixar=ServidorAndamento(), _relogio=tempo.monotonic)
    pub = PublicadorLocal(tmp_path)
    original = pub.publicar
    chamadas = []

    def vaza(arquivos):
        chamadas.append(1)
        if len(chamadas) == 1:
            raise OSError("Could not connect to https://conta123.r2.cloudflarestorage.com/bucket-secreto/estado.json")
        original(arquivos)

    pub.publicar = vaza
    with caplog.at_level("DEBUG"):
        executar(coletor, BASE, pub, intervalo=60, ate=INICIO + timedelta(seconds=61), **tempo.kw())
    bruto = (tmp_path / "ao-vivo" / "estado.json").read_text(encoding="utf-8")
    for segredo in ("conta123", "bucket-secreto", "cloudflarestorage"):
        assert segredo not in bruto
        assert segredo not in caplog.text
    assert "falha na publicação" in bruto
    assert "ciclo falhou" in caplog.text  # o log existe, só que oculto


def test_falha_inesperada_tem_mensagem_generica(tmp_path):
    from qma_eleicoes.ao_vivo.coleta import RelatorioCiclo

    tempo = Tempo()

    class Estranho:
        resultados, horarios, andamento, ufs_governador = {}, {}, {}, []
        chamadas = 0

        def ciclo(self, prazo=None):
            self.chamadas += 1
            if self.chamadas == 1:
                raise RuntimeError("detalhe interno")
            return RelatorioCiclo()

    executar(
        Estranho(), BASE, PublicadorLocal(tmp_path), intervalo=60,
        ate=INICIO + timedelta(seconds=61), **tempo.kw(),
    )  # fmt: skip
    assert _estado(tmp_path)["erro_ultimo_ciclo"] == "18:00 — falha inesperada"


def test_falha_no_controle_ou_na_projecao_nao_bloqueia_a_publicacao(tmp_path, caplog):
    class ControleQuebrado(PublicadorLocal):
        def ler_controle(self):
            raise ConnectionError("R2 fora")

    _rodar_com(ControleQuebrado(tmp_path), tmp_path, lambda e, c, a: {"x": 1})
    estado = _estado(tmp_path)
    assert "projecao" not in estado and "erro_ultimo_ciclo" not in estado
    assert "projeção ignorada" in caplog.text


def test_falha_no_gancho_de_projecao_nao_bloqueia_a_publicacao(tmp_path):
    def quebra(estado, controle, agora):
        raise ZeroDivisionError("boom")

    _rodar_com(PublicadorLocal(tmp_path), tmp_path, quebra)
    estado = _estado(tmp_path)
    assert "projecao" not in estado and "erro_ultimo_ciclo" not in estado
    assert (tmp_path / "ao-vivo" / "municipios" / "go.json").exists()


def _rodar_com(pub, tmp_path, projetar):
    tempo = Tempo()
    coletor = Coletor(MUNICIPIOS, ["DF"], _baixar=ServidorAndamento(), _relogio=tempo.monotonic)
    executar(
        coletor, BASE, pub, intervalo=60, ate=INICIO + timedelta(seconds=1),
        projetar_bloco=projetar, **tempo.kw(),
    )  # fmt: skip


def test_hora_interpreta_em_sao_paulo_mesmo_com_tz_utc(monkeypatch):
    import argparse
    import pytest

    from qma_eleicoes.ao_vivo import __main__ as cli

    monkeypatch.setenv("TZ", "UTC")
    instante = datetime(2026, 10, 25, 2, 0, tzinfo=ZoneInfo("UTC"))  # 23:00 de 24/10 em SP

    class Falso(datetime):
        @classmethod
        def now(cls, tz=None):
            return instante.astimezone(tz)

    monkeypatch.setattr(cli, "datetime", Falso)
    ate = cli._hora("22:30")
    assert (ate.year, ate.month, ate.day, ate.hour, ate.minute) == (2026, 10, 24, 22, 30)
    assert ate.utcoffset() == timedelta(hours=-3)
    for ruim in ("", "abc", "12", "25:00", "12:60", "1:2:3", "12:3x"):
        with pytest.raises(argparse.ArgumentTypeError):
            cli._hora(ruim)


def test_ajuda_documenta_ate_sem_virada_de_dia(capsys):
    import pytest

    from qma_eleicoes.ao_vivo.__main__ import main

    with pytest.raises(SystemExit):
        main(["--help"])
    saida = " ".join(capsys.readouterr().out.split())
    assert "hoje" in saida and "sem virada" in saida
