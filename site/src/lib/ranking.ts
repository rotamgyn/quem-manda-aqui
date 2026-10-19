// Faixas de porte e filtro do ranking. Módulo puro: usado no build e no script do navegador.
import type { ItemRanking } from './tipos';

export type Faixa = 'ate10k' | '10a50k' | '50a200k' | 'mais200k';

/** Faixas por eleitores aptos (limite superior inclusivo). */
export const FAIXAS: { id: Faixa; rotulo: string; max: number }[] = [
  { id: 'ate10k', rotulo: 'Até 10 mil eleitores', max: 10_000 },
  { id: '10a50k', rotulo: 'De 10 a 50 mil', max: 50_000 },
  { id: '50a200k', rotulo: 'De 50 a 200 mil', max: 200_000 },
  { id: 'mais200k', rotulo: 'Acima de 200 mil', max: Infinity },
];

export function faixaDe(aptos: number): Faixa {
  return (FAIXAS.find((f) => aptos <= f.max) ?? FAIXAS[FAIXAS.length - 1]).id;
}

/** Filtra preservando a ordem (já por volatilidade) e limita. `''` = sem filtro. */
export function filtrarRanking(
  itens: ItemRanking[],
  filtro: { uf: string; faixa: Faixa | '' },
  limite = Infinity,
): ItemRanking[] {
  return itens
    .filter((i) => (!filtro.uf || i.uf === filtro.uf) && (!filtro.faixa || faixaDe(i.aptos) === filtro.faixa))
    .slice(0, limite);
}
