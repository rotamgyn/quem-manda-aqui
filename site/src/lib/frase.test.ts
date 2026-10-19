import { describe, expect, test } from 'vitest';
import { fraseDestaque } from './frase';
import type { Comparacao, LinhaPartido, MunicipioComparado } from './tipos';

const linha = (partido: string, a: number | null, b: number | null): LinhaPartido => ({
  partido, pct_2022: a, pct_2026: b, delta_pp: a === null || b === null ? null : Math.round((b - a) * 100) / 100,
});
const mun = (nome: string, partidos: LinhaPartido[], com2022 = true): MunicipioComparado => ({
  tse: '1', ibge: '1', nome, slug: 'x', capital: false,
  presidente: { cargo: 'presidente', uf: 'GO', municipio_tse: '1', r2022: com2022 ? ({} as never) : null, r2026: null, partidos, volatilidade: null, vencedor_2022: null, vencedor_2026: null, virou: null, apuracao_completa: true } as Comparacao,
});

describe('fraseDestaque', () => {
  test('test_frase_maior_variacao: maior |delta| entre partidos presentes nos dois anos', () => {
    const m = mun('ANÁPOLIS', [linha('PT', 30, 28.5), linha('PL', 40, 51.5), linha('NOVO', null, 20), linha('PSD', 10, 2)]);
    expect(fraseDestaque(m)).toBe('Em Anápolis, o PL cresceu 11,5 pontos desde 2022');
  });
  test('queda usa "caiu" e número sem sinal', () => {
    const m = mun('ANÁPOLIS', [linha('PT', 40, 30.25), linha('PL', 40, 41)]);
    expect(fraseDestaque(m)).toBe('Em Anápolis, o PT caiu 9,8 pontos desde 2022');
  });
  test('test_frase_sem_2022', () => {
    const m = mun('BOA ESPERANÇA DO NORTE', [linha('PL', null, 60)], false);
    expect(fraseDestaque(m)).toBe('Primeira eleição presidencial de Boa Esperança do Norte');
  });
  test('sem nenhum partido nos dois anos também é primeira eleição', () => {
    expect(fraseDestaque(mun('X', [linha('PL', null, 60)]))).toBe('Primeira eleição presidencial de X');
  });
  test('test_frase_cabe_em_120_caracteres: trunca o nome, nunca o número', () => {
    const nome = 'MUNICÍPIO COM UM NOME ABSURDAMENTE LONGO '.repeat(5).trim();
    const f = fraseDestaque(mun(nome, [linha('PL', 40, 51.5)]));
    expect(f.length).toBeLessThanOrEqual(120);
    expect(f).toContain('o PL cresceu 11,5 pontos desde 2022');
    expect(f).toContain('…');
    expect(fraseDestaque(mun(nome, [], false)).length).toBeLessThanOrEqual(120);
  });
});
