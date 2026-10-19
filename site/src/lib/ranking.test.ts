import { describe, expect, test } from 'vitest';
import { faixaDe, filtrarRanking } from './ranking';
import type { ItemRanking } from './tipos';

const item = (tse: string, uf: string, aptos: number): ItemRanking => ({
  tse, nome: tse, uf, slug: tse, aptos, volatilidade: 10, vencedor_2022: 'PT', vencedor_2026: 'PL', virou: true,
});

describe('ranking', () => {
  test('faixas de porte pelos eleitores aptos', () => {
    expect(faixaDe(10000)).toBe('ate10k');
    expect(faixaDe(10001)).toBe('10a50k');
    expect(faixaDe(50000)).toBe('10a50k');
    expect(faixaDe(200000)).toBe('50a200k');
    expect(faixaDe(200001)).toBe('mais200k');
  });
  test('filtra por UF e porte, mantém a ordem e limita', () => {
    const itens = [item('1', 'GO', 5000), item('2', 'RS', 5000), item('3', 'GO', 300000), item('4', 'GO', 7000)];
    expect(filtrarRanking(itens, { uf: 'GO', faixa: '' }).map((i) => i.tse)).toEqual(['1', '3', '4']);
    expect(filtrarRanking(itens, { uf: '', faixa: 'ate10k' }).map((i) => i.tse)).toEqual(['1', '2', '4']);
    expect(filtrarRanking(itens, { uf: 'GO', faixa: 'ate10k' }, 1).map((i) => i.tse)).toEqual(['1']);
    expect(filtrarRanking(itens, { uf: '', faixa: '' })).toHaveLength(4);
  });
});
