from __future__ import annotations

from dataclasses import replace

import pytest

from qma_eleicoes.conferencia import ErroConferencia, conferir
from qma_eleicoes.modelo import Resultado, VotoCandidato


def _res(uf, mun, votos22, votos13, brancos=5, nulos=5, aptos=1000, cargo="presidente"):
    cands = (
        VotoCandidato(22, "A", "PL", votos22, ""),
        VotoCandidato(13, "B", "PT", votos13, ""),
    )
    validos = votos22 + votos13
    comp = validos + brancos + nulos
    return Resultado(
        ano=2026, turno=1, cargo=cargo, uf=uf, municipio_tse=mun,
        aptos=aptos, comparecimento=comp, abstencao=aptos - comp,
        brancos=brancos, nulos=nulos, validos=validos,
        pct_secoes_totalizadas=100.0, candidatos=cands,
    )


def _soma(uf, filhos):
    cands = tuple(
        VotoCandidato(n, nome, p, sum(c.votos for f in filhos for c in f.candidatos if c.numero == n), "")
        for n, nome, p in ((22, "A", "PL"), (13, "B", "PT"))
    )
    return Resultado(
        ano=2026, turno=1, cargo=filhos[0].cargo, uf=uf, municipio_tse=None,
        aptos=sum(f.aptos for f in filhos), comparecimento=sum(f.comparecimento for f in filhos),
        abstencao=sum(f.abstencao for f in filhos), brancos=sum(f.brancos for f in filhos),
        nulos=sum(f.nulos for f in filhos), validos=sum(f.validos for f in filhos),
        pct_secoes_totalizadas=100.0, candidatos=cands,
    )


def _cenario():
    go = [_res("GO", "1", 300, 200), _res("GO", "2", 100, 50)]
    zz = [_res("ZZ", "10", 7, 3)]
    ufs = [_soma("GO", go), _soma("ZZ", zz)]
    br = _soma("BR", ufs)
    return go + zz + ufs + [br]


def test_totais_batem():
    conferir(_cenario())


def test_divergencia_de_um_voto_bloqueia():
    rs = _cenario()
    i = next(k for k, r in enumerate(rs) if r.uf == "GO" and r.municipio_tse is None)
    uf = rs[i]
    c0 = replace(uf.candidatos[0], votos=uf.candidatos[0].votos + 1)
    rs[i] = replace(uf, candidatos=(c0, uf.candidatos[1]))
    with pytest.raises(ErroConferencia) as e:
        conferir(rs)
    # agregado de UF corrompido: linha da UF e, legitimamente, a do BR (soma dos oficiais)
    assert e.value.divergencias == [
        "2026 presidente GO candidato 22: municípios=400 oficial=401",
        "2026 presidente BR candidato 22: UFs=408 oficial=407",
    ]


def test_voto_municipal_errado_gera_uma_unica_linha():
    rs = _cenario()
    i = next(k for k, r in enumerate(rs) if r.municipio_tse == "1")
    m = rs[i]
    rs[i] = replace(m, candidatos=(replace(m.candidatos[0], votos=m.candidatos[0].votos + 1), m.candidatos[1]))
    with pytest.raises(ErroConferencia) as e:
        conferir(rs)
    assert e.value.divergencias == ["2026 presidente GO candidato 22: municípios=401 oficial=400"]


def test_rotulo_segundo_turno():
    go = [replace(_res("GO", "1", 300, 200, cargo="governador"), turno=2)]
    uf = replace(_soma("GO", go), turno=2, aptos=go[0].aptos + 1, abstencao=go[0].abstencao + 1)
    with pytest.raises(ErroConferencia) as e:
        conferir(go + [uf])
    assert e.value.divergencias[0].startswith("2026 governador 2º turno GO aptos:")


def test_mensagem_lista_todas_as_divergencias():
    go = [_res("GO", "1", 300, 200, cargo="governador"), _res("GO", "2", 100, 50, cargo="governador")]
    uf = _soma("GO", go)
    uf = replace(uf, validos=uf.validos + 1_000, nulos=uf.nulos - 3)
    with pytest.raises(ErroConferencia) as e:
        conferir(go + [uf])
    assert len(e.value.divergencias) == 2
    linhas = str(e.value).splitlines()
    assert "2026 governador GO validos: municípios=650 oficial=1.650" in linhas
    assert "2026 governador GO nulos: municípios=10 oficial=7" in linhas


def test_candidato_ausente_de_um_lado_e_divergencia():
    rs = _cenario()
    i = next(k for k, r in enumerate(rs) if r.uf == "GO" and r.municipio_tse is None)
    rs[i] = replace(rs[i], candidatos=rs[i].candidatos[:1])
    with pytest.raises(ErroConferencia) as e:
        conferir(rs)
    assert "2026 presidente GO candidato 13: municípios=250 oficial=0" in e.value.divergencias


def test_soma_das_ufs_diverge_do_brasil():
    rs = _cenario()
    i = next(k for k, r in enumerate(rs) if r.uf == "BR")
    rs[i] = replace(rs[i], aptos=rs[i].aptos + 1)
    with pytest.raises(ErroConferencia) as e:
        conferir(rs)
    assert e.value.divergencias == ["2026 presidente BR aptos: UFs=3.000 oficial=3.001"]


def test_uf_sem_agregado_ou_sem_municipios_nao_e_ignorada():
    rs = _cenario()
    sem_agregado = [r for r in rs if not (r.uf == "GO" and r.municipio_tse is None)]
    with pytest.raises(ErroConferencia) as e:
        conferir(sem_agregado)
    assert any("GO" in d and "sem agregado" in d for d in e.value.divergencias)

    sem_mun = [r for r in rs if not (r.uf == "GO" and r.municipio_tse is not None)]
    with pytest.raises(ErroConferencia) as e:
        conferir(sem_mun)
    assert any("GO" in d and "sem municípios" in d for d in e.value.divergencias)


def test_governador_nao_exige_brasil():
    go = [_res("GO", "1", 300, 200, cargo="governador")]
    conferir(go + [_soma("GO", go)])
