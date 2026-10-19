"""Laço do robô ao vivo: coletar → montar → (projeção) → publicar → dormir."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from qma_comum.http import ErroDownload

from .montar import montar
from .publicar import ocultar

log = logging.getLogger("qma_eleicoes.ao_vivo")

FUSO = ZoneInfo("America/Sao_Paulo")
CAMINHO_ESTADO = "ao-vivo/estado.json"

# Gancho da projeção (Tarefa 5): (estado, controle, agora) → bloco `projecao` ou None.
ProjetarBloco = Callable[[dict, dict, datetime], dict | None]


def _agora_sp() -> datetime:
    return datetime.now(FUSO)


def _terminou(estado: dict, coletor) -> bool:
    """Brasil e todas as UFs de governador em 100% (andamento e resultado de governador)."""
    andamento = estado["andamento"]
    if andamento.get("br", 0) < 100:
        return False
    for uf in coletor.ufs_governador:
        if andamento.get(uf.lower(), 0) < 100:
            return False
        r = coletor.resultados.get(("governador", uf, None))
        if r is None or r.pct_secoes_totalizadas < 100:
            return False
    return True


class _FalhaDoCiclo(Exception):
    """Falha classificada; `str(self)` é a mensagem pública (sem detalhes do erro)."""


@contextmanager
def _etapa(mensagem: str, excecoes: tuple[type[Exception], ...] = (Exception,)):
    """Converte erros da etapa na mensagem pública fixa (o detalhe fica só no log)."""
    try:
        yield
    except excecoes as e:
        raise _FalhaDoCiclo(mensagem) from e


def _projetar(projetar_bloco, estado: dict, publicador, agora: datetime) -> None:
    """Projeção opcional: qualquer falha é registrada e o ciclo publica sem `projecao`."""
    try:
        bloco = projetar_bloco(estado, publicador.ler_controle(), agora)
    except Exception as e:
        log.warning("projeção ignorada neste ciclo: %s", ocultar(repr(e)), exc_info=True)
        return
    if bloco is not None:
        estado["projecao"] = bloco


def _um_ciclo(coletor, base, publicador, prazo, agora, erro_pendente, projetar_bloco) -> bool:
    """Coleta, monta e publica. Devolve True quando a apuração acabou."""
    with _etapa("falha na coleta de dados do TSE", (ErroDownload, OSError)):
        rel = coletor.ciclo(prazo=prazo)
    for erro in rel.erros:
        log.warning("arquivo com erro: %s", erro)
    with _etapa("dados do TSE em formato inesperado", (ValueError, KeyError, TypeError, AttributeError)):
        arquivos = montar(
            coletor.resultados, coletor.horarios, base, agora=agora, andamento=coletor.andamento
        )
    estado = arquivos[CAMINHO_ESTADO]
    estado["arquivos_com_erro"] = len(rel.erros)
    if erro_pendente:
        estado["erro_ultimo_ciclo"] = erro_pendente
    if projetar_bloco is not None:
        _projetar(projetar_bloco, estado, publicador, agora)
    with _etapa("falha na publicação"):
        publicador.publicar(arquivos)
    log.info(
        "ciclo: %d baixados, %d alterados, %d com erro", rel.baixados, rel.alterados, len(rel.erros)
    )
    return _terminou(estado, coletor)


def executar(
    coletor,
    base: dict,
    publicador,
    *,
    intervalo: float = 60.0,
    ate: datetime | None = None,
    projetar_bloco: ProjetarBloco | None = None,
    _agora: Callable[[], datetime] = _agora_sp,
    _monotonic: Callable[[], float] = time.monotonic,
    _dormir: Callable[[float], None] = time.sleep,
) -> int:
    """Roda até a apuração acabar ou `ate`; devolve o número de ciclos.

    O próximo ciclo começa em `início + max(intervalo, duração)`: nunca se sobrepõem.
    Uma exceção no ciclo (coleta, montagem, projeção ou upload) é registrada, o último
    estado publicado continua no ar e o próximo estado leva `erro_ultimo_ciclo`.
    """
    erro_pendente: str | None = None
    ciclos = 0
    while True:
        inicio = _monotonic()
        agora = _agora()
        terminou = False
        try:
            terminou = _um_ciclo(
                coletor, base, publicador, inicio + intervalo, agora, erro_pendente, projetar_bloco
            )
            erro_pendente = None
        except Exception as e:
            log.exception("ciclo falhou; o último estado publicado continua no ar")
            publica = str(e) if isinstance(e, _FalhaDoCiclo) else "falha inesperada"
            erro_pendente = f"{agora.astimezone(FUSO):%H:%M} — {publica}"
        ciclos += 1
        if terminou:
            log.info("apuração em 100%%; encerrando após %d ciclos", ciclos)
            break
        if ate is not None and _agora() >= ate:
            break
        espera = inicio + intervalo - _monotonic()
        if ate is not None:
            espera = min(espera, (ate - _agora()).total_seconds())
        if espera > 0:
            _dormir(espera)
        if ate is not None and _agora() >= ate:
            break
    return ciclos
