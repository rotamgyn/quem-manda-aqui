"""Coleta incremental do 2º turno de 2026: arquivos fixos a cada ciclo + varredura municipal."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from qma_comum.http import ErroDownload, baixar_json
from qma_comum.municipios import Municipio

from ..config import ELEICAO_2026_T2, url_andamento_2026, url_resultado_2026
from ..leitor_2026 import ler_resultado_2026
from ..modelo import Cargo, Resultado

log = logging.getLogger("qma_eleicoes.ao_vivo")

EXTERIOR = "ZZ"
Chave = tuple[Cargo, str, str | None]  # (cargo, uf, município TSE ou None)
_FALHAS = (ErroDownload, ValueError, KeyError, TypeError, AttributeError)


@dataclass
class RelatorioCiclo:
    baixados: int = 0
    alterados: int = 0
    erros: list[str] = field(default_factory=list)


def ufs_governador_de(config: dict) -> list[str]:
    """UFs com 2º turno de governador, a partir de `config/mun-e006260-cm.json`."""
    return sorted(uf["cd"].upper() for uf in config["abr"] if uf.get("mu"))


class Coletor:
    def __init__(
        self,
        municipios: list[Municipio],
        ufs_governador: list[str],
        *,
        _baixar: Callable = baixar_json,
        max_por_ciclo: int = 200,
        _relogio: Callable[[], float] = time.monotonic,
    ):
        self._relogio = _relogio
        self._baixar = _baixar
        self.max_por_ciclo = max_por_ciclo
        self.ufs_governador = [u.upper() for u in ufs_governador]
        ordenados = sorted(municipios, key=lambda m: (m.uf, m.tse))
        self._ufs = sorted({m.uf for m in ordenados})
        self._fila: list[Chave] = [("presidente", m.uf, m.tse) for m in ordenados] + [
            ("governador", m.uf, m.tse)
            for m in ordenados
            if m.uf in self.ufs_governador and m.uf != EXTERIOR
        ]
        self._cursor = 0
        self._idg: dict[str, str | None] = {}
        self.resultados: dict[Chave, Resultado] = {}
        self.horarios: dict[Chave, str] = {}
        self.andamento: dict[str, dict] = {}  # abrangência (BR, UF, ZZ) → {"and", "pst"}

    def _url(self, chave: Chave) -> str:
        cargo, uf, tse = chave
        return url_resultado_2026(cargo, uf.lower(), tse, ELEICAO_2026_T2[cargo])

    def _completo(self, chave: Chave) -> bool:
        r = self.resultados.get(chave)
        return r is not None and r.pct_secoes_totalizadas >= 100

    def _arquivos_fixos(self) -> list[Chave]:
        return [
            ("presidente", "BR", None),
            *(("presidente", uf, None) for uf in self._ufs),
            *(("governador", uf, None) for uf in self.ufs_governador),
        ]

    def _selecionar_municipais(self) -> list[int]:
        """Fila circular: índices a partir do cursor, só dos que ainda não estão em 100%."""
        n = len(self._fila)
        escolhidos: list[int] = []
        for passo in range(n):
            if len(escolhidos) >= self.max_por_ciclo:
                break
            i = (self._cursor + passo) % n
            if not self._completo(self._fila[i]):
                escolhidos.append(i)
        return escolhidos

    def _processar(self, chave: Chave, rel: RelatorioCiclo) -> None:
        url = self._url(chave)
        try:
            dados = self._baixar(url, forcar=True)
            rel.baixados += 1
            idg = dados.get("idg")
            if idg is not None and self._idg.get(url) == idg and chave in self.resultados:
                return
            resultado = ler_resultado_2026(dados, chave[0], uf=chave[1])
            horario = f"{dados['dg']} {dados['hg']}"
        except _FALHAS as e:
            rel.erros.append(f"{url}: {e}")
            log.warning("falha em %s: %s", url, e)
            return
        self._idg[url] = idg
        self.resultados[chave] = resultado
        self.horarios[chave] = horario
        rel.alterados += 1

    def _processar_andamento(self, rel: RelatorioCiclo) -> None:
        url = url_andamento_2026(ELEICAO_2026_T2["presidente"])
        try:
            dados = self._baixar(url, forcar=True)
            rel.baixados += 1
            self.andamento = {
                a["cdabr"].upper(): {"and": a["and"], "pst": a["s"]["pst"]} for a in dados["abr"]
            }
        except _FALHAS as e:
            rel.erros.append(f"{url}: {e}")
            log.warning("falha em %s: %s", url, e)

    def ciclo(self, prazo: float | None = None) -> RelatorioCiclo:
        """Um ciclo. `prazo` (instante do relógio monotônico) interrompe só a varredura
        municipal; andamento, BR e UFs rodam sempre. Os municípios não visitados ficam
        no início da fila do próximo ciclo."""
        rel = RelatorioCiclo()
        self._processar_andamento(rel)
        for chave in self._arquivos_fixos():
            self._processar(chave, rel)
        escolhidos = self._selecionar_municipais()
        for pos, i in enumerate(escolhidos):
            if prazo is not None and self._relogio() >= prazo:
                self._cursor = i
                log.info("prazo do ciclo esgotado: %d municipais pendentes", len(escolhidos) - pos)
                break
            self._processar(self._fila[i], rel)
        else:
            if escolhidos:
                self._cursor = (escolhidos[-1] + 1) % len(self._fila)
        return rel
