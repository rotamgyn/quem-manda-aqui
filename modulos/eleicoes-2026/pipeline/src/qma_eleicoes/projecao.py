"""Projeção estatística do 2º turno (presidente) a partir de resultados municipais parciais.

Modelo (uniforme por estrato):
- município completo: resultado real;
- município parcial: votos já apurados + restante estimado; aguardando: tudo estimado;
- participação de A no restante = `t1_2026.partidos[A] + swing`, em que o swing é a mediana de
  (pct 2º turno − pct 1º turno) dos municípios completos do estrato (UF × porte → UF → Brasil,
  mínimo de 5 completos por estrato);
- votos válidos esperados do restante = `t1_2026.validos × (1 − pct_secoes/100)`.

Faixa (bootstrap conservador): em cada reamostra, as medianas são recalculadas sobre
municípios completos sorteados com reposição; quando um estrato cai para o nível de cima,
soma-se um efeito de estrato desconhecido (sorteado entre os desvios observados nos outros
estratos, com sinal aleatório); soma-se também um efeito nacional (o restante do eleitorado
pode diferir do já apurado, como as UFs diferem entre si); cada município restante recebe
ainda um resíduo sorteado entre os resíduos dos completos.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

FUSO = ZoneInfo("America/Sao_Paulo")
TEXTO_FIXO = "Projeção estatística a partir de resultados oficiais parciais. Não é pesquisa eleitoral."
HORA_INICIO = time(17, 0)
MINIMO_COMPLETOS = 30
MINIMO_ESTRATO = 5
# Abaixo deste % de seções (o mesmo do critério do backtest) a projeção não foi validada.
PCT_MINIMO_VALIDADO = 30.0
# Muda sempre que o modelo mudar: a aprovação do backtest vale só para esta versão.
VERSAO_MODELO = "1"
# Efeito nacional desconhecido (um sorteio por reamostra, igual para todos os municípios
# restantes): desvio de UF sorteado × esta escala. Calibrada no backtest de 2022: a menor das
# escalas testadas (1; 1,5; 2) com o resultado real dentro da faixa em todos os estágios ≥ 30%,
# inclusive nas ordens de apuração adversas. Sem ele a faixa ignora o viés de composição
# (cidades grandes terminam por último) e fica estreita demais.
ESCALA_EFEITO_NACIONAL = 1.5
_MINIMO_DESVIOS = 3  # desvios de estrato necessários para usá-los como efeito desconhecido


@dataclass(frozen=True)
class Projecao:
    partido_a: str
    pct_a: float
    faixa_a: tuple[float, float]
    confianca: float
    tendencia_definida: bool
    pct_secoes_base: float


def _validos_apurados(item: dict, t1: dict | None) -> float:
    """Votos válidos já apurados; arquivo antigo sem `validos` → estimativa pelo 1º turno."""
    if item.get("validos") is not None:
        return float(item["validos"])
    return float((t1 or {}).get("validos") or 0) * float(item.get("pct_secoes") or 0) / 100


class _Estratos:
    """Swings dos completos agrupados em UF × porte, UF e Brasil."""

    def __init__(self, completos: list[tuple[str, str, float]]):
        tmp: dict[tuple, list[float]] = defaultdict(list)
        for uf, porte, swing in completos:
            tmp[("up", uf, porte)].append(swing)
            tmp[("u", uf)].append(swing)
            tmp[("br",)].append(swing)
        self.grupos = {k: np.asarray(v) for k, v in tmp.items()}
        self.mediana = {k: float(np.median(v)) for k, v in self.grupos.items()}

    def suficiente(self, chave: tuple) -> bool:
        return len(self.grupos.get(chave, ())) >= MINIMO_ESTRATO

    def nivel(self, uf: str, porte: str) -> tuple:
        if self.suficiente(("up", uf, porte)):
            return ("up", uf, porte)
        if self.suficiente(("u", uf)):
            return ("u", uf)
        return ("br",)

    def desvios(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(efeitos de UF, efeitos de porte, resíduos municipais) observados."""
        br = self.mediana[("br",)]
        uf = [self.mediana[k] - br for k in self.grupos if k[0] == "u" and self.suficiente(k)]
        porte = [
            self.mediana[k] - self.mediana[("u", k[1])]
            for k in self.grupos
            if k[0] == "up" and self.suficiente(k) and self.suficiente(("u", k[1]))
        ]
        residuos = []
        for k, valores in self.grupos.items():
            if k[0] == "up":
                ref = self.mediana[self.nivel(k[1], k[2])]
                residuos.extend(valores - ref)
        individual = self.grupos[("br",)] - br  # recurso (mais largo) quando há poucos estratos
        uf_ = np.asarray(uf) if len(uf) >= _MINIMO_DESVIOS else individual
        porte_ = np.asarray(porte) if len(porte) >= _MINIMO_DESVIOS else individual
        return uf_, porte_, np.asarray(residuos)


def projetar(
    municipais: dict[str, dict],
    base: dict,
    finalistas: tuple[str, str],
    *,
    reamostras: int = 200,
    confianca: float = 0.90,
    semente: int = 25,
) -> Projecao | None:
    """Projeção de A (= `finalistas[0]`) no total de votos válidos; None com < 30 completos."""
    a = finalistas[0]
    completos: list[tuple[str, str, float]] = []
    restantes: list[tuple[str, str, float, float]] = []  # uf, porte, pct 1º turno de A, peso
    fixo_a = fixo_v = 0.0
    aptos_total = aptos_apurados = 0.0
    for tse, info in base["municipios"].items():
        item = municipais.get(tse) or {}
        t1 = info.get("t1_2026")
        uf, porte = info["uf"], info.get("porte", "")
        status = item.get("status")
        apurado = status in ("parcial", "completo")
        pct = min(float(item.get("pct_secoes") or 0), 100.0) if apurado else 0.0
        aptos = float(info.get("aptos_2026") or 0)
        aptos_total += aptos
        aptos_apurados += aptos * pct / 100
        partidos = item.get("partidos") or {}
        pct_1t = float(((t1 or {}).get("partidos") or {}).get(a, 0.0))
        if apurado:
            v = _validos_apurados(item, t1)
            fixo_v += v
            fixo_a += v * float(partidos.get(a, 0.0)) / 100
        if status == "completo":
            if t1 and t1.get("validos"):
                completos.append((uf, porte, float(partidos.get(a, 0.0)) - pct_1t))
            continue
        if not t1 or not t1.get("validos"):
            continue  # sem 1º turno não há como estimar o restante
        peso = float(t1["validos"]) * (1 - pct / 100)
        if peso > 0:
            restantes.append((uf, porte, pct_1t, peso))
    if len(completos) < MINIMO_COMPLETOS:
        return None

    estratos = _Estratos(completos)
    niveis = [estratos.nivel(uf, porte) for uf, porte, _, _ in restantes]
    pct_1t = np.asarray([r[2] for r in restantes])
    peso = np.asarray([r[3] for r in restantes])
    total_v = fixo_v + float(peso.sum())
    if total_v <= 0:
        return None

    def pct_a(swing: np.ndarray) -> float:
        votos_a = fixo_a + float((peso * np.clip(pct_1t + swing, 0, 100) / 100).sum())
        return votos_a / total_v * 100

    ponto = pct_a(np.asarray([estratos.mediana[n] for n in niveis]))
    lo = hi = ponto
    if restantes:
        lo, hi = _faixa(estratos, restantes, niveis, pct_a, reamostras, confianca, semente)
        lo, hi = min(lo, ponto), max(hi, ponto)
    return Projecao(
        partido_a=a,
        pct_a=ponto,
        faixa_a=(lo, hi),
        confianca=confianca,
        tendencia_definida=lo > 50 or hi < 50,
        pct_secoes_base=aptos_apurados / aptos_total * 100 if aptos_total else 0.0,
    )


def _faixa(estratos, restantes, niveis, pct_a, reamostras, confianca, semente):
    rng = np.random.default_rng(semente)
    efeitos_uf, efeitos_porte, residuos = estratos.desvios()
    ufs = [r[0] for r in restantes]
    ufps = [(r[0], r[1]) for r in restantes]
    usados = sorted(set(niveis))
    sem_uf = sorted({uf for uf, n in zip(ufs, niveis) if n[0] == "br"})
    sem_porte = sorted({up for up, n in zip(ufps, niveis) if n[0] != "up"})
    idx_nivel = np.asarray([usados.index(n) for n in niveis])
    idx_uf = {uf: i for i, uf in enumerate(sem_uf)}
    idx_up = {up: i for i, up in enumerate(sem_porte)}
    m_uf = np.asarray([idx_uf.get(uf, -1) for uf in ufs])
    m_up = np.asarray([idx_up.get(up, -1) for up in ufps])

    def sorteio_simetrico(pool: np.ndarray, n: int) -> np.ndarray:
        if n == 0:
            return np.zeros(0)
        return rng.choice(pool, n) * rng.choice((-1.0, 1.0), n)

    valores = []
    for _ in range(reamostras):
        medianas = np.asarray(
            [float(np.median(rng.choice(estratos.grupos[n], len(estratos.grupos[n])))) for n in usados]
        )
        swing = medianas[idx_nivel] + rng.choice(residuos, len(restantes))
        e_uf = np.append(sorteio_simetrico(efeitos_uf, len(sem_uf)), 0.0)
        e_up = np.append(sorteio_simetrico(efeitos_porte, len(sem_porte)), 0.0)
        swing = swing + e_uf[m_uf] + e_up[m_up]  # índice -1 → 0 (estrato observado)
        # efeito nacional: o eleitorado ainda não apurado difere do já apurado
        swing = swing + ESCALA_EFEITO_NACIONAL * sorteio_simetrico(efeitos_uf, 1)[0]
        valores.append(pct_a(swing))
    cauda = (1 - confianca) / 2
    lo, hi = np.quantile(valores, [cauda, 1 - cauda])
    return float(lo), float(hi)


def finalistas_de(municipais: dict[str, dict]) -> tuple[str, str] | None:
    """Os dois partidos com mais votos válidos apurados nos municípios (ordem alfabética)."""
    votos: dict[str, float] = defaultdict(float)
    for item in municipais.values():
        for p, pct in (item.get("partidos") or {}).items():
            votos[p] += float(pct or 0) * float(item.get("validos") or 0)
    if len(votos) < 2:
        return None
    dois = sorted(votos, key=lambda p: -votos[p])[:2]
    return tuple(sorted(dois))  # type: ignore[return-value]


def ler_aprovacao(arquivo: Path) -> bool:
    """Backtest aprovado para a versão atual do modelo (arquivo ausente/inválido → False)."""
    try:
        dados = json.loads(Path(arquivo).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return (
        isinstance(dados, dict)
        and dados.get("aprovado") is True
        and dados.get("versao_modelo") == VERSAO_MODELO
    )


def bloco_projecao(
    estado_municipal_por_uf: dict[str, list[dict]],
    base: dict,
    controle: dict,
    agora: datetime,
    aprovado: bool,
) -> dict | None:
    """Bloco `projecao` do `estado.json`, ou None (antes das 17h, desligada ou não aprovada)."""
    if not aprovado or controle.get("projecao_ligada") is not True:
        return None
    if agora.astimezone(FUSO).time() < HORA_INICIO:
        return None
    municipais = {m["tse"]: m for lista in estado_municipal_por_uf.values() for m in lista}
    finalistas = finalistas_de(municipais)
    if finalistas is None:
        return None
    p = projetar(municipais, base, finalistas)
    if p is None or p.pct_secoes_base < PCT_MINIMO_VALIDADO:
        return None
    partido, pct, (lo, hi) = p.partido_a, p.pct_a, p.faixa_a
    if pct < 50:  # mostra quem está à frente na projeção
        partido = finalistas[1]
        pct, lo, hi = 100 - pct, 100 - hi, 100 - lo
    # arredonda a faixa para fora: a faixa exibida nunca é mais estreita que a calculada
    lo, hi = math.floor(lo * 10) / 10, math.ceil(hi * 10) / 10
    return {
        "partido_a": partido,
        "pct_a": round(pct, 1),
        "faixa_a": [lo, hi],
        "confianca": p.confianca,
        "tendencia_definida": p.tendencia_definida and (lo > 50 or hi < 50),
        "pct_secoes_base": round(p.pct_secoes_base, 2),
        "texto": TEXTO_FIXO,
    }
