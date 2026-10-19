"""CLI do robô ao vivo: `python -m qma_eleicoes.ao_vivo [--intervalo 60] [--ate HH:MM] ...`."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from qma_comum.http import baixar_json
from qma_comum.municipios import Municipio

from ..config import URL_CONFIG_GOVERNADOR_T2
from .coleta import Coletor, ufs_governador_de
from .laco import FUSO, executar
from .publicar import PREFIXO_PADRAO, PublicadorLocal, PublicadorR2

log = logging.getLogger("qma_eleicoes.ao_vivo")


def _hora(texto: str) -> datetime:
    """`HH:MM` de hoje, no fuso de São Paulo."""
    try:
        hh, mm = texto.split(":")
        return datetime.now(FUSO).replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    except ValueError:
        raise argparse.ArgumentTypeError(f"horário inválido (use HH:MM): {texto!r}") from None


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m qma_eleicoes.ao_vivo")
    p.add_argument("--intervalo", type=float, default=60.0, help="segundos entre inícios de ciclo")
    p.add_argument("--ate", type=_hora, help="HH:MM (São Paulo) em que o robô encerra")
    p.add_argument("--simular", metavar="PASTA", help="reproduz um ensaio gravado (Tarefa 4)")
    p.add_argument("--local", metavar="PASTA", help="grava em disco em vez de publicar no R2")
    p.add_argument("--prefixo", default=PREFIXO_PADRAO, help="prefixo das chaves (ensaio/, teste/)")
    p.add_argument("--max-por-ciclo", type=int, default=150, help="municipais por ciclo")
    p.add_argument("--dados", type=Path, default=Path("dados"), help="pasta `dados` do repositório")
    return p


def main(
    argv: list[str] | None = None,
    *,
    _baixar_simulado: Callable[[str], Callable] | None = None,
    _projetar_bloco: Callable | None = None,
) -> int:
    """`_baixar_simulado(pasta)` devolve o `_baixar` do simulador (plugado pela Tarefa 4);
    `_projetar_bloco` é o gancho da projeção (Tarefa 5)."""
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)

    baixar = baixar_json
    if args.simular:
        if _baixar_simulado is None:
            raise SystemExit("--simular: simulador disponível na Tarefa 4")
        baixar = _baixar_simulado(args.simular)

    municipios_json = args.dados / "comum" / "municipios.json"
    municipios = [Municipio(**m) for m in json.loads(municipios_json.read_text(encoding="utf-8"))]
    base = json.loads(
        (args.dados / "eleicoes-2026" / "base-ao-vivo.json").read_text(encoding="utf-8")
    )
    ufs = ufs_governador_de(baixar(URL_CONFIG_GOVERNADOR_T2, forcar=True))
    log.info("2º turno de governador em: %s", ", ".join(ufs))
    coletor = Coletor(municipios, ufs, _baixar=baixar, max_por_ciclo=args.max_por_ciclo)

    if args.local:
        publicador = PublicadorLocal(args.local, prefixo=args.prefixo)
    else:
        publicador = PublicadorR2.do_ambiente(args.prefixo)
    log.info("publicando em %s (prefixo %r)", args.local or "R2", publicador.prefixo)

    ciclos = executar(
        coletor, base, publicador, intervalo=args.intervalo, ate=args.ate,
        projetar_bloco=_projetar_bloco,
    )  # fmt: skip
    log.info("encerrado após %d ciclos", ciclos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
