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
    p.add_argument("--ate", type=_hora, help="HH:MM de hoje (America/Sao_Paulo, independe do TZ da máquina; sem virada de dia) em que o robô encerra")
    p.add_argument(
        "--simular", action="store_true",
        help="ensaio: reproduz o 2º turno de 2022 (CSVs em .cache/2022) no lugar do TSE; "
        "com --local roda totalmente offline",
    )  # fmt: skip
    p.add_argument(
        "--data-simulada", choices=("2022", "hoje"), default="2022",
        help="data/hora (dg/hg) dos arquivos simulados: 2022 (padrão, backtest) ou hoje, "
        "às 17:00 de São Paulo (ensaio)",
    )  # fmt: skip
    p.add_argument("--local", metavar="PASTA", help="grava em disco em vez de publicar no R2")
    p.add_argument("--prefixo", default=PREFIXO_PADRAO, help="prefixo das chaves (ensaio/, teste/)")
    p.add_argument("--max-por-ciclo", type=int, default=150, help="municipais por ciclo")
    p.add_argument("--dados", type=Path, default=Path("dados"), help="pasta `dados` do repositório")
    return p


def _simulador_2022(municipios: list[Municipio], inicio: datetime | None = None) -> Callable:
    """`_baixar` simulado com o 2º turno de 2022 (CSVs do cache; capitais apuram primeiro)."""
    from ..leitor_2022 import arquivos_2022, ler_2022
    from .simulador import baixar_simulado, gerar_sequencia

    votacao, detalhe = arquivos_2022()
    r2022 = ler_2022(votacao, detalhe, turno=2)
    capitais = {(m.uf, m.tse) for m in municipios if m.capital}
    pares = {(m.uf, m.tse) for m in municipios}
    opcoes = {"inicio": inicio} if inicio else {}
    return baixar_simulado(
        gerar_sequencia(r2022, capitais=capitais, municipios_2026=pares, **opcoes)
    )


def main(
    argv: list[str] | None = None,
    *,
    _baixar_simulado: Callable[[list[Municipio], datetime | None], Callable] | None = None,
    _projetar_bloco: Callable | None = None,
) -> int:
    """`_baixar_simulado(municipios, inicio)` devolve o `_baixar` do `--simular` (padrão: o simulador
    sobre o 2º turno de 2022); `_projetar_bloco` é o gancho da projeção (Tarefa 5)."""
    args = _parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)

    municipios_json = args.dados / "comum" / "municipios.json"
    municipios = [Municipio(**m) for m in json.loads(municipios_json.read_text(encoding="utf-8"))]
    base = json.loads(
        (args.dados / "eleicoes-2026" / "base-ao-vivo.json").read_text(encoding="utf-8")
    )
    baixar = baixar_json
    if args.simular:
        inicio = None
        if args.data_simulada == "hoje":
            inicio = datetime.now(FUSO).replace(hour=17, minute=0, second=0, microsecond=0, tzinfo=None)
        baixar = (_baixar_simulado or _simulador_2022)(municipios, inicio)
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
