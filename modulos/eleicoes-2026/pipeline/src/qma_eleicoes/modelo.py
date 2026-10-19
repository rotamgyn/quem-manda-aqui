"""Modelo de dados comum a todos os leitores de resultado eleitoral."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Cargo = Literal["presidente", "governador"]
Situacao = Literal["eleito", "2º turno", "não eleito", ""]


@dataclass(frozen=True)
class VotoCandidato:
    numero: int
    nome_urna: str
    partido: str
    votos: int
    situacao: Situacao


@dataclass(frozen=True)
class Resultado:
    ano: int
    turno: int
    cargo: Cargo
    uf: str  # "BR" ou sigla maiúscula
    municipio_tse: str | None
    aptos: int
    comparecimento: int
    abstencao: int
    brancos: int
    nulos: int
    validos: int
    pct_secoes_totalizadas: float
    candidatos: tuple[VotoCandidato, ...]  # válidos, ordenados por votos, do maior ao menor
    # Candidatos com votos anulados (inclusive sub judice): fora de `validos` e dos percentuais.
    anulados: tuple[VotoCandidato, ...] = ()

    def pct(self, candidato: VotoCandidato) -> float | None:
        """Percentual do candidato sobre os votos válidos; None sem votos válidos."""
        if self.validos == 0:
            return None
        return candidato.votos / self.validos * 100
