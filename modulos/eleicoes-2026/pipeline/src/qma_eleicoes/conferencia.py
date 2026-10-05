"""Conferência bloqueante: somas dos filhos devem bater com o agregado oficial."""

from __future__ import annotations

from collections import defaultdict

from .modelo import Resultado

_TOTAIS = ("aptos", "comparecimento", "abstencao", "brancos", "nulos", "validos")


class ErroConferencia(Exception):
    def __init__(self, divergencias: list[str]):
        self.divergencias = divergencias
        super().__init__(
            f"{len(divergencias)} divergência(s) com os totais oficiais:\n" + "\n".join(divergencias)
        )


def _rotulo(ano: int, turno: int, cargo: str, uf: str) -> str:
    return f"{ano} {cargo}" + ("" if turno == 1 else f" {turno}º turno") + f" {uf}"


def _n(valor: int) -> str:
    return f"{valor:,}".replace(",", ".")


def _comparar(rotulo: str, filhos: list[Resultado], oficial: Resultado, nome_soma: str) -> list[str]:
    saida: list[str] = []

    def diff(campo: str, soma: int, ref: int) -> None:
        if soma != ref:
            saida.append(f"{rotulo} {campo}: {nome_soma}={_n(soma)} oficial={_n(ref)}")

    for campo in _TOTAIS:
        diff(campo, sum(getattr(f, campo) for f in filhos), getattr(oficial, campo))

    somas: dict[int, int] = defaultdict(int)
    for f in filhos:
        for c in f.candidatos:
            somas[c.numero] += c.votos
    refs = {c.numero: c.votos for c in oficial.candidatos}
    for numero in sorted(somas.keys() | refs.keys()):
        diff(f"candidato {numero}", somas.get(numero, 0), refs.get(numero, 0))
    return saida


def conferir(resultados: list[Resultado]) -> None:
    """Levanta ErroConferencia com todas as divergências encontradas.

    Duas conferências independentes:
    1. soma dos municípios == agregado oficial da UF (por ano, turno, cargo, UF);
    2. só para presidente, soma dos agregados OFICIAIS das UFs (incluindo ZZ) == Brasil,
       o que verifica que os próprios arquivos do TSE são coerentes entre si.
    Um erro num município gera exatamente uma linha (UF). Um agregado de UF corrompido
    gera legitimamente duas (a da UF e a do BR).
    """
    municipios: dict[tuple, list[Resultado]] = defaultdict(list)
    ufs: dict[tuple, list[Resultado]] = defaultdict(list)
    agregados: dict[tuple, list[Resultado]] = defaultdict(list)
    brasil: dict[tuple, list[Resultado]] = defaultdict(list)
    for r in resultados:
        chave = (r.ano, r.turno, r.cargo, r.uf)
        if r.municipio_tse is not None:
            municipios[chave].append(r)
        elif r.uf == "BR":
            brasil[chave].append(r)
        else:
            agregados[chave].append(r)
            ufs[chave[:3]].append(r)

    divergencias: list[str] = []
    for chave in sorted(municipios.keys() | agregados.keys()):
        rotulo = _rotulo(*chave)
        if chave not in agregados:
            divergencias.append(f"{rotulo}: sem agregado oficial da UF")
        elif chave not in municipios:
            divergencias.append(f"{rotulo}: sem municípios para somar")
        else:
            for oficial in agregados[chave]:
                divergencias += _comparar(rotulo, municipios[chave], oficial, "municípios")

    grupos = {c[:3] for c in ufs.keys() | brasil.keys() | municipios.keys() if c[2] == "presidente"}
    for grupo in sorted(grupos):
        rotulo = _rotulo(*grupo, "BR")
        oficial = brasil.get(grupo + ("BR",))
        filhos = ufs.get(grupo)
        if not oficial:
            divergencias.append(f"{rotulo}: sem agregado oficial do Brasil")
        elif not filhos:
            divergencias.append(f"{rotulo}: sem UFs para somar")
        else:
            for of in oficial:
                divergencias += _comparar(rotulo, filhos, of, "UFs")

    if divergencias:
        raise ErroConferencia(divergencias)
