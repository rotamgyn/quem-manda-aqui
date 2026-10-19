"""Backtest da projeção com o 2º turno de 2022: `python -m qma_eleicoes.backtest` (da raiz).

O 1º turno de 2022 faz o papel de `t1_2026`; o simulador (Tarefa 4) reproduz a apuração do
2º turno de 2022 e, em cada estágio (10% a 90% das seções do Brasil), os arquivos simulados
passam pelo mesmo caminho do robô (leitor → `montar`) antes de chegar a `projetar`.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from qma_comum.municipios import Municipio

from .ao_vivo.montar import montar
from .ao_vivo.simulador import gerar_sequencia
from .base_ao_vivo import gerar_base
from .config import url_andamento_2026, url_resultado_2026
from .leitor_2026 import ler_resultado_2026
from .modelo import Resultado
from .projecao import ESCALA_EFEITO_NACIONAL, PCT_MINIMO_VALIDADO, VERSAO_MODELO, projetar

log = logging.getLogger("qma_eleicoes.backtest")

FINALISTAS = ("PT", "PL")
SEMENTES = (25, 1, 2, 3, 4, *range(5, 15))  # 15 sorteios da ordem de apuração
ESTAGIOS = tuple(range(10, 100, 10))
COBERTURA_A_PARTIR = 30  # a faixa contém o resultado real em todos os estágios a partir daqui
ERRO_A_PARTIR = 50  # e o erro do ponto é menor que ERRO_MAXIMO a partir daqui
ERRO_MAXIMO = 1.0
PASSOS = 40
_AGORA = datetime(2022, 10, 30, 20, 0)  # só para o campo `atualizado_em` do `montar`


@dataclass(frozen=True)
class Linha:
    cenario: str  # "semente 25", "PT primeiro"...
    oficial: bool  # entra no critério de aprovação
    estagio: int
    pct_br: float  # % de seções do Brasil (andamento simulado)
    pct_base: float | None  # % de seções que a projeção usou (municípios)
    ponto: float | None
    faixa: tuple[float, float] | None
    tendencia: bool

    def erro(self, real: float) -> float | None:
        return None if self.ponto is None else abs(self.ponto - real)

    def cobre(self, real: float) -> bool:
        return self.faixa is not None and self.faixa[0] <= real <= self.faixa[1]

    def lado_errado(self, real: float) -> bool:
        """'Tendência definida' para quem perdeu de fato."""
        return self.tendencia and self.ponto is not None and (self.ponto > 50) != (real > 50)

    @property
    def visivel(self) -> bool:
        """A página mostraria esta projeção (mínimo validado de seções)."""
        return self.pct_base is not None and self.pct_base >= PCT_MINIMO_VALIDADO


@dataclass
class RelatorioBacktest:
    real: float  # % oficial final do partido A (PT) nos votos válidos
    linhas: list[Linha] = field(default_factory=list)
    motivos: list[str] = field(default_factory=list)  # por que foi reprovado

    @property
    def aprovado(self) -> bool:
        return not self.motivos


def avaliar(linhas: list[Linha], real: float) -> list[str]:
    """Motivos de reprovação (lista vazia = aprovado).

    Cenários oficiais: cobertura em todos os estágios ≥ 30% e erro < 1 p.p. a partir de 50%.
    Todos os cenários (inclusive os adversos): nenhuma "tendência definida" do lado errado
    que a página mostraria (com o mínimo validado de seções).
    """
    motivos = []
    for l in linhas:
        rotulo = f"{l.cenario}, {l.estagio}%"
        if l.lado_errado(real) and l.visivel:
            motivos.append(f"{rotulo}: tendência definida para o lado errado")
        if not l.oficial:
            continue
        if l.estagio >= COBERTURA_A_PARTIR and not l.cobre(real):
            motivos.append(f"{rotulo}: resultado real fora da faixa")
        erro = l.erro(real)
        if l.estagio >= ERRO_A_PARTIR and (erro is None or erro >= ERRO_MAXIMO):
            motivos.append(f"{rotulo}: erro do ponto ≥ {ERRO_MAXIMO:.1f} p.p.")
    return motivos


def _pct_br(passo: dict) -> float:
    abr = passo[url_andamento_2026("6258")]["abr"]
    return float(next(a for a in abr if a["cdabr"] == "br")["s"]["pstn"])


def _municipais(passo: dict, base: dict) -> dict[str, dict]:
    """Itens municipais do robô (`montar`) a partir dos arquivos simulados do passo."""
    resultados = {}
    for tse, info in base["municipios"].items():
        url = url_resultado_2026("presidente", info["uf"].lower(), tse, "6258")
        if url in passo:
            resultados[("presidente", info["uf"], tse)] = ler_resultado_2026(
                passo[url], "presidente", uf=info["uf"]
            )
    arquivos = montar(resultados, {}, base, agora=_AGORA)
    return {
        m["tse"]: m
        for caminho, lista in arquivos.items()
        if caminho.startswith("ao-vivo/municipios/")
        for m in lista
    }


def rodar_cenario(
    sequencia, base: dict, cenario: str, oficial: bool, reamostras: int = 200
) -> list[Linha]:
    linhas = []
    pendentes = list(ESTAGIOS)
    for passo in sequencia:
        if not pendentes:
            break
        pct = _pct_br(passo)
        if pct < pendentes[0]:
            continue
        municipais = _municipais(passo, base)
        p = projetar(municipais, base, FINALISTAS, reamostras=reamostras)
        while pendentes and pct >= pendentes[0]:
            linhas.append(
                Linha(
                    cenario, oficial, pendentes.pop(0), pct,
                    None if p is None else p.pct_secoes_base,
                    None if p is None else p.pct_a,
                    None if p is None else p.faixa_a,
                    False if p is None else p.tendencia_definida,
                )
            )  # fmt: skip
        log.info("%s: %.1f%% -> %s", cenario, pct, p)
    return linhas


def _pct_pt(r: Resultado) -> float:
    pt = sum(c.votos for c in r.candidatos if c.partido == "PT")
    return pt / r.validos if r.validos else 0.5


def cenarios(
    r2022_t2: list[Resultado], capitais, pares
) -> list[tuple[str, bool, Callable[[], object]]]:
    """(nome, entra no critério, fábrica da sequência)."""
    pres = [r for r in r2022_t2 if r.cargo == "presidente"]
    saida: list[tuple[str, bool, Callable[[], object]]] = [
        (
            f"semente {s}", True,
            lambda s=s: gerar_sequencia(pres, passos=PASSOS, semente=s, capitais=capitais, municipios_2026=pares),
        )
        for s in SEMENTES
    ]  # fmt: skip
    saida.append(
        ("adverso: maior % do PT primeiro", False,
         lambda: gerar_sequencia(pres, passos=PASSOS, ordem=lambda r: -_pct_pt(r), municipios_2026=pares))
    )  # fmt: skip
    saida.append(
        ("adverso: maior % do PL primeiro", False,
         lambda: gerar_sequencia(pres, passos=PASSOS, ordem=_pct_pt, municipios_2026=pares))
    )  # fmt: skip
    return saida


def rodar_backtest(dados: Path = Path("dados"), reamostras: int = 200) -> RelatorioBacktest:
    from .leitor_2022 import arquivos_2022, ler_2022

    votacao, detalhe = arquivos_2022()
    r_t1 = ler_2022(votacao, detalhe, turno=1)
    r_t2 = ler_2022(votacao, detalhe, turno=2)
    municipios = [
        Municipio(**m)
        for m in json.loads((dados / "comum" / "municipios.json").read_text(encoding="utf-8"))
    ]
    base = gerar_base(r_t2, r_t1, municipios)  # 1º turno de 2022 no papel de t1_2026
    br = next(r for r in r_t2 if r.cargo == "presidente" and r.uf == "BR")
    real = next(c.votos for c in br.candidatos if c.partido == "PT") / br.validos * 100
    capitais = {(m.uf, m.tse) for m in municipios if m.capital}
    pares = {(m.uf, m.tse) for m in municipios}
    rel = RelatorioBacktest(real=real)
    for nome, oficial, fabrica in cenarios(r_t2, capitais, pares):
        rel.linhas += rodar_cenario(fabrica(), base, nome, oficial, reamostras)
    rel.motivos = avaliar(rel.linhas, real)
    return rel


def _fmt(x: float | None, casas: int = 2) -> str:
    return "—" if x is None else f"{x:.{casas}f}".replace(".", ",")


def _tabela(linhas: list[Linha], real: float) -> list[str]:
    saida = [
        "| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |",
        "|---|---|---|---|---|---|---|",
    ]
    for l in linhas:
        faixa = "—" if l.faixa is None else f"{_fmt(l.faixa[0])} a {_fmt(l.faixa[1])}"
        tendencia = "não"
        if l.tendencia:
            tendencia = "sim, " + ("PT" if (l.ponto or 0) > 50 else "PL")
            if l.lado_errado(real):
                tendencia += " (ERRADA" + ("" if l.visivel else "; não iria para a página") + ")"
        saida.append(
            f"| {l.estagio}% | {_fmt(l.pct_br)}% | {_fmt(l.ponto)} | {faixa} | "
            f"{_fmt(l.erro(real))} | {'sim' if l.cobre(real) else 'não'} | {tendencia} |"
        )
    return saida


def _resumo(linhas: list[Linha], real: float) -> list[str]:
    """Uma linha por estágio somando os sorteios."""
    n = len({l.cenario for l in linhas})
    saida = [
        "| Estágio | Real dentro da faixa | Maior erro do ponto (p.p.) | Largura média da faixa (p.p.) | Com tendência definida |",
        "|---|---|---|---|---|",
    ]
    for estagio in ESTAGIOS:
        do_estagio = [l for l in linhas if l.estagio == estagio]
        erros = [e for l in do_estagio if (e := l.erro(real)) is not None]
        larguras = [l.faixa[1] - l.faixa[0] for l in do_estagio if l.faixa]
        sem = n - len(erros)
        saida.append(
            f"| {estagio}% | {sum(l.cobre(real) for l in do_estagio)} de {n} | "
            f"{_fmt(max(erros) if erros else None)} | "
            f"{_fmt(sum(larguras) / len(larguras) if larguras else None)} | "
            f"{sum(l.tendencia for l in do_estagio)} de {n}"
            + (f" ({sem} sem projeção)" if sem else "")
            + " |"
        )
    return saida


def _titulo(nome: str) -> str:
    return nome[0].upper() + nome[1:]


def relatorio_md(rel: RelatorioBacktest) -> str:
    real = rel.real
    veredito = "APROVADO" if rel.aprovado else "REPROVADO"
    oficiais = [l for l in rel.linhas if l.oficial]
    adversos = [l for l in rel.linhas if not l.oficial]
    sementes = ", ".join(str(s) for s in SEMENTES)
    minimo = _fmt(PCT_MINIMO_VALIDADO, 0)
    partes = [
        "# Backtest da projeção — 2º turno de 2022",
        "",
        f"**Resultado: {veredito}.** Modelo versão {VERSAO_MODELO}; gerado em {date.today():%d/%m/%Y}.",
        "",
        "## O que é este teste",
        "",
        "No dia 25/10 a página ao vivo pode mostrar uma *projeção estatística* do 2º turno de "
        "presidente, feita só com resultados oficiais parciais. Antes de ligar essa projeção, "
        "ela é testada com uma eleição cujo resultado já sabemos: o 2º turno de 2022 "
        f"(resultado oficial: PT {_fmt(real)}% dos votos válidos).",
        "",
        "Como foi feito:",
        "",
        f"- Reproduzimos a apuração de 2022 em {PASSOS} etapas, município a município, com o "
        "simulador do robô. Os arquivos simulados passam pelo mesmo caminho do robô de verdade.",
        "- O 1º turno de 2022 faz o papel do 1º turno de 2026.",
        "- Em cada estágio (10%, 20%, ..., 90% das seções do Brasil apuradas), a projeção calcula "
        "um número (o *ponto*) e uma *faixa* com 90% de confiança.",
        "- A ordem em que os municípios terminam a apuração é sorteada. Repetimos o teste com "
        f"{len(SEMENTES)} sorteios (sementes {sementes}).",
        "",
        f"**Critério de aprovação** (precisa valer em todos os {len(SEMENTES)} sorteios):",
        "",
        f"1. A partir de {COBERTURA_A_PARTIR}% apurado, o resultado real fica dentro da faixa "
        "em todos os estágios.",
        f"2. A partir de {ERRO_A_PARTIR}% apurado, o ponto erra por menos de "
        f"{_fmt(ERRO_MAXIMO, 1)} ponto percentual.",
        "3. Em nenhum cenário, nem nos testes de estresse abaixo, a página mostraria "
        '"tendência definida" para quem perdeu.',
        "",
        "Na página, a projeção só aparece depois das 17h, com este backtest aprovado, com a chave "
        f"`projecao_ligada` ligada e com pelo menos {minimo}% das seções apuradas (abaixo disso "
        "o modelo não foi validado).",
        "",
        "## Limites (leia antes de ligar a projeção)",
        "",
        "- **A ordem sorteada é artificial.** No simulador, capitais e municípios pequenos "
        "terminam primeiro e as cidades médias e grandes por último, sem relação com a região. "
        "Na apuração real, regiões inteiras podem chegar antes de outras. Por isso há dois "
        "testes de estresse com ordens propositalmente ruins (os municípios mais favoráveis a "
        "um lado terminam primeiro). Eles não entram nos critérios 1 e 2, mas reprovam o "
        'modelo se a página mostrasse "tendência definida" para o lado errado.',
        '- **Município parcial é "bem comportado" no simulador:** as seções já apuradas de uma '
        "cidade têm a mesma divisão de votos do total da cidade. O modelo não se aproveita "
        "disso: estima o restante de cada município pelo 1º turno mais a variação do estrato.",
        "- **O ponto tende a subestimar quem cresce mais nas cidades grandes.** Em 2022, o ponto "
        "do PT ficou quase sempre abaixo do real nos estágios intermediários, porque a variação "
        "entre turnos medida nos municípios pequenos (que terminam antes) foi menor que a das "
        "cidades grandes. A faixa leva isso em conta com um *efeito nacional* desconhecido "
        f"(escala {_fmt(ESCALA_EFEITO_NACIONAL, 1)}), calibrado com estes mesmos dados de 2022: "
        "é a menor escala testada (1; 1,5; 2) em que o real ficou dentro da faixa em todos os "
        "estágios a partir de 30%, inclusive nas ordens adversas. Como a calibração usa a "
        "própria eleição de 2022, não há garantia de que 2026 se comporte igual.",
        "- 2022 foi uma eleição muito apertada (50,9% × 49,1%): a faixa só fica inteira de um "
        "lado de 50% com bastante apuração. Esse é o comportamento desejado.",
        "",
    ]
    if not rel.aprovado:
        partes += ["## Por que foi reprovado", "", *[f"- {m}" for m in rel.motivos], ""]
    partes += [
        f"## Resumo dos {len(SEMENTES)} sorteios (entram no critério)",
        "",
        *_resumo(oficiais, real),
        "",
        "## Testes de estresse (ordens adversas; não entram nos critérios 1 e 2)",
        "",
    ]
    for nome in dict.fromkeys(l.cenario for l in adversos):
        linhas = [l for l in adversos if l.cenario == nome]
        partes += [f"### {_titulo(nome)}", "", *_tabela(linhas, real), ""]
    partes += ["## Detalhe de cada sorteio", ""]
    for nome in dict.fromkeys(l.cenario for l in oficiais):
        linhas = [l for l in oficiais if l.cenario == nome]
        partes += [f"### {_titulo(nome)}", "", *_tabela(linhas, real), ""]
    partes += [
        "## Legenda",
        "",
        "- *Seções BR*: % das seções do Brasil apuradas no momento da projeção.",
        "- *Ponto*: o percentual final do PT que a projeção estimava naquele momento.",
        "- *Faixa 90%*: intervalo onde a projeção dizia estar o resultado final, com 90% de confiança.",
        f"- *Erro*: diferença entre o ponto e o resultado real ({_fmt(real)}%).",
        "- *Tendência definida*: a faixa inteira está de um lado de 50%.",
        '- "—": a projeção não sai (menos de 30 municípios completos). Abaixo de '
        f"{minimo}% das seções a página também não mostra a projeção.",
        "",
    ]
    return "\n".join(partes)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m qma_eleicoes.backtest")
    p.add_argument("--dados", type=Path, default=Path("dados"))
    p.add_argument("--docs", type=Path, default=Path("docs"))
    p.add_argument("--reamostras", type=int, default=200)
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    rel = rodar_backtest(args.dados, args.reamostras)
    args.docs.mkdir(parents=True, exist_ok=True)
    (args.docs / "backtest-2022.md").write_text(relatorio_md(rel), encoding="utf-8")
    aprovacao = args.dados / "eleicoes-2026" / "backtest-aprovado.json"
    if rel.aprovado:
        aprovacao.write_text(
            json.dumps(
                {"aprovado": True, "versao_modelo": VERSAO_MODELO, "data": f"{date.today():%Y-%m-%d}",
                 "sementes": list(SEMENTES), "relatorio": "docs/backtest-2022.md"},
                ensure_ascii=False, indent=2,
            ) + "\n",
            encoding="utf-8",
        )  # fmt: skip
    elif aprovacao.exists():
        aprovacao.unlink()  # reprovado: nenhuma aprovação antiga pode sobrar
    print("APROVADO" if rel.aprovado else "REPROVADO")
    for m in rel.motivos:
        print(" -", m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
