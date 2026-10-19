import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from qma_eleicoes.projecao import (
    TEXTO_FIXO,
    VERSAO_MODELO,
    bloco_projecao,
    finalistas_de,
    ler_aprovacao,
    projetar,
)

SP = ZoneInfo("America/Sao_Paulo")
LIGADA = {"projecao_ligada": True}


def _base(n, uf="GO", porte="ate10k", validos=1000, pt_1t=45.0, inicio=0):
    return {
        f"{inicio + i:05d}": {
            "uf": uf, "porte": porte, "aptos_2026": validos * 1.2,
            "t1_2026": {"comparecimento": validos, "validos": validos,
                        "partidos": {"PT": pt_1t, "PL": 40.0, "X": 100 - pt_1t - 40.0}},
        }
        for i in range(n)
    }  # fmt: skip


def _item(tse, pt, validos=1000, pct=100.0):
    status = "completo" if pct >= 100 else "parcial"
    return {
        "tse": tse, "pct_secoes": pct, "status": status,
        "partidos": {"PT": pt, "PL": round(100 - pt, 2)}, "validos": validos,
    }  # fmt: skip


def _aguardando(tse):
    return {"tse": tse, "pct_secoes": 0, "status": "aguardando", "partidos": None, "validos": None}


def test_projecao_com_tudo_completo_e_exata():
    municipios = _base(40)
    municipios.update(_base(10, validos=3000, inicio=100))
    base = {"municipios": municipios}
    itens = {t: _item(t, 60.0 if int(t) < 100 else 40.0, validos=municipios[t]["t1_2026"]["validos"])
             for t in municipios}  # fmt: skip
    p = projetar(itens, base, ("PT", "PL"))
    exato = (40 * 1000 * 0.6 + 10 * 3000 * 0.4) / (40 * 1000 + 10 * 3000) * 100
    assert p.pct_a == pytest.approx(exato)
    assert p.faixa_a == (pytest.approx(exato), pytest.approx(exato))
    assert p.pct_secoes_base == pytest.approx(100)
    assert p.partido_a == "PT" and p.confianca == 0.90 and p.tendencia_definida


def test_projecao_none_com_poucos_completos():
    base = {"municipios": _base(100)}
    itens = {t: _item(t, 50.0) for t in list(base["municipios"])[:29]}
    assert projetar(itens, base, ("PT", "PL")) is None
    itens[f"{29:05d}"] = _item(f"{29:05d}", 50.0)
    assert projetar(itens, base, ("PT", "PL")) is not None


def test_swing_do_estrato_e_restante_do_parcial():
    """Swing +5 (45 → 50) dos completos; aguardando: 45+5; parcial: apurado real + restante."""
    base = {"municipios": _base(40)}
    itens = {t: _item(t, 50.0) for t in list(base["municipios"])[:30]}
    itens["00030"] = _item("00030", 80.0, validos=400, pct=40.0)  # restante: 600 válidos a 50%
    p = projetar(itens, base, ("PT", "PL"))
    esperado = (30 * 500 + 400 * 0.8 + 600 * 0.5 + 9 * 500) / (30 * 1000 + 1000 + 9 * 1000) * 100
    assert p.pct_a == pytest.approx(esperado)


def test_estrato_uf_porte_tem_precedencia_sobre_uf():
    municipios = _base(30)  # GO ate10k: swing +5
    municipios.update(_base(6, porte="mais200k", inicio=100))  # GO mais200k: swing −5
    municipios.update(_base(1, porte="mais200k", inicio=200, validos=100_000))  # aguardando
    itens = {t: _item(t, 50.0) for t in list(municipios)[:30]}
    itens.update({t: _item(t, 40.0) for t in list(municipios)[30:36]})
    p = projetar(itens, {"municipios": municipios}, ("PT", "PL"))
    v_ap = 36 * 1000
    a_ap = 30 * 500 + 6 * 400
    assert p.pct_a == pytest.approx((a_ap + 100_000 * 0.40) / (v_ap + 100_000) * 100)


def _cenario(pt_completos, n_aguardando, dispersao=0.0):
    municipios = _base(60)
    municipios.update(_base(n_aguardando, inicio=1000))
    municipios.update(_base(n_aguardando, uf="BA", inicio=5000))
    itens = {}
    for i, t in enumerate(list(municipios)[:60]):
        itens[t] = _item(t, pt_completos + dispersao * ((i % 7) - 3))
    for t in list(municipios)[60:]:
        itens[t] = _aguardando(t)
    return itens, {"municipios": municipios}


def test_faixa_contem_ponto():
    for pt, disp in ((50.0, 4.0), (48.0, 1.0), (53.0, 6.0)):
        itens, base = _cenario(pt, 200, disp)
        p = projetar(itens, base, ("PT", "PL"))
        lo, hi = p.faixa_a
        assert lo <= p.pct_a <= hi
        assert hi - lo > 0  # há incerteza com municípios aguardando


def test_tendencia_so_com_faixa_de_um_lado():
    apertado = projetar(*_cenario(50.2, 300, 5.0), ("PT", "PL"))
    assert apertado.faixa_a[0] < 50 < apertado.faixa_a[1]
    assert not apertado.tendencia_definida
    folgado = projetar(*_cenario(70.0, 300, 1.0), ("PT", "PL"))
    assert folgado.faixa_a[0] > 50 and folgado.tendencia_definida
    do_outro_lado = projetar(*_cenario(30.0, 300, 1.0), ("PT", "PL"))
    assert do_outro_lado.faixa_a[1] < 50 and do_outro_lado.tendencia_definida


def test_reamostragem_e_reprodutivel():
    itens, base = _cenario(51.0, 200, 4.0)
    assert projetar(itens, base, ("PT", "PL")) == projetar(itens, base, ("PT", "PL"))


# --- integração com o laço -------------------------------------------------------------------


def _por_uf(pt=60.0):
    """GO com 100 municípios completos (PT 60%): projeção válida, PT à frente."""
    base = {"municipios": _base(100)}
    itens = [_item(t, pt) for t in base["municipios"]]
    return {"go": itens}, base


def test_projecao_ausente_antes_das_17h():
    por_uf, base = _por_uf()
    antes = datetime(2026, 10, 25, 16, 59, 59, tzinfo=SP)
    assert bloco_projecao(por_uf, base, LIGADA, antes, True) is None
    bloco = bloco_projecao(por_uf, base, LIGADA, datetime(2026, 10, 25, 17, 0, tzinfo=SP), True)
    assert bloco["texto"] == TEXTO_FIXO
    assert bloco["texto"] == (
        "Projeção estatística a partir de resultados oficiais parciais. Não é pesquisa eleitoral."
    )
    assert bloco["partido_a"] == "PT" and bloco["pct_a"] == 60.0
    assert bloco["faixa_a"] == [60.0, 60.0] and bloco["confianca"] == 0.9
    assert bloco["tendencia_definida"] is True and bloco["pct_secoes_base"] == 100.0
    # 16h59 em UTC é 13h59 em SP: o horário vale no fuso de São Paulo
    utc = datetime(2026, 10, 25, 19, 59, tzinfo=ZoneInfo("UTC"))
    assert bloco_projecao(por_uf, base, LIGADA, utc, True) is None


def test_projecao_desligada():
    por_uf, base = _por_uf()
    noite = datetime(2026, 10, 25, 19, 0, tzinfo=SP)
    assert bloco_projecao(por_uf, base, {"projecao_ligada": False}, noite, True) is None
    assert bloco_projecao(por_uf, base, {}, noite, True) is None
    assert bloco_projecao(por_uf, base, {"projecao_ligada": "true"}, noite, True) is None
    assert bloco_projecao(por_uf, base, LIGADA, noite, False) is None  # backtest não aprovado
    assert bloco_projecao(por_uf, base, LIGADA, noite, True) is not None


def test_bloco_mostra_quem_esta_a_frente_e_respeita_minimo_validado():
    por_uf, base = _por_uf(pt=40.0)
    noite = datetime(2026, 10, 25, 19, 0, tzinfo=SP)
    bloco = bloco_projecao(por_uf, base, LIGADA, noite, True)
    assert bloco["partido_a"] == "PL" and bloco["pct_a"] == 60.0
    # menos de 30% das seções apuradas (critério do backtest): sem bloco
    base["municipios"].update(_base(400, inicio=1000))
    por_uf["go"] += [_aguardando(t) for t in list(base["municipios"])[100:]]
    assert bloco_projecao(por_uf, base, LIGADA, noite, True) is None


def test_finalistas_dos_municipios():
    itens = {"1": _item("1", 70.0), "2": _aguardando("2")}
    assert finalistas_de(itens) == ("PL", "PT")
    assert finalistas_de({"2": _aguardando("2")}) is None


def test_aprovacao_exige_arquivo_e_versao_do_modelo(tmp_path):
    arq = tmp_path / "backtest-aprovado.json"
    assert ler_aprovacao(arq) is False
    arq.write_text(json.dumps({"aprovado": True, "versao_modelo": VERSAO_MODELO}), encoding="utf-8")
    assert ler_aprovacao(arq) is True
    arq.write_text(json.dumps({"aprovado": True, "versao_modelo": "0"}), encoding="utf-8")
    assert ler_aprovacao(arq) is False
    arq.write_text("{inválido", encoding="utf-8")
    assert ler_aprovacao(arq) is False


# --- critério do backtest -------------------------------------------------------------------


def test_criterio_do_backtest():
    from qma_eleicoes.backtest import Linha, avaliar

    real = 50.9

    def linha(estagio, ponto, faixa, oficial=True, base=None):
        tendencia = faixa is not None and (faixa[0] > 50 or faixa[1] < 50)
        return Linha("s", oficial, estagio, estagio, estagio if base is None else base, ponto,
                     faixa, tendencia)  # fmt: skip

    boas = [linha(e, 50.8, (50.2, 51.6)) for e in range(30, 100, 10)]
    assert avaliar(boas, real) == []
    # 20%: fora da faixa e erro grande não contam
    assert avaliar([linha(20, 52.5, (52.0, 53.0))], real) == []
    assert avaliar([linha(30, 51.2, (51.0, 51.4))], real) == ["s, 30%: resultado real fora da faixa"]
    assert avaliar([linha(50, 49.9, (49.0, 51.0))], real) == ["s, 50%: erro do ponto ≥ 1.0 p.p."]
    assert not any("erro do ponto" in m for m in avaliar([linha(40, 49.9, (49.0, 51.0))], real))
    assert avaliar([linha(60, None, None)], real) != []  # sem projeção a partir de 50%: reprova
    # adverso: só a tendência para o lado errado reprova, e só se a página a mostraria
    errada = linha(40, 49.5, (49.2, 49.8), oficial=False)
    assert avaliar([errada], real) == ["s, 40%: tendência definida para o lado errado"]
    assert avaliar([linha(40, 49.5, (49.2, 49.8), oficial=False, base=25.0)], real) == []
    assert avaliar([linha(40, 50.2, (49.0, 50.4), oficial=False)], real) == []


def test_gancho_do_robo_usa_municipios_do_coletor():
    from types import SimpleNamespace

    from qma_eleicoes.ao_vivo.__main__ import _gancho_projecao
    from qma_eleicoes.modelo import Resultado, VotoCandidato

    base = {"municipios": _base(40)}
    for info in base["municipios"].values():
        info.update(ibge="0", t2_2022=None)

    def res(tse):
        return Resultado(
            ano=2026, turno=2, cargo="presidente", uf="GO", municipio_tse=tse, aptos=1200,
            comparecimento=1000, abstencao=200, brancos=0, nulos=0, validos=1000,
            pct_secoes_totalizadas=100.0,
            candidatos=(VotoCandidato(13, "A", "PT", 600, ""), VotoCandidato(22, "B", "PL", 400, "")),
        )  # fmt: skip

    coletor = SimpleNamespace(
        resultados={("presidente", "GO", t): res(t) for t in base["municipios"]}, horarios={}
    )
    noite = datetime(2026, 10, 25, 19, 0, tzinfo=SP)
    bloco = _gancho_projecao(coletor, base, True)({}, LIGADA, noite)
    assert bloco["partido_a"] == "PT" and bloco["pct_a"] == 60.0 and bloco["texto"] == TEXTO_FIXO
    assert _gancho_projecao(coletor, base, False)({}, LIGADA, noite) is None
