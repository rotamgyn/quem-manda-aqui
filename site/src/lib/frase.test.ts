import { describe, expect, test } from 'vitest';
import { fraseDestaque } from './frase';
import type { Comparacao, LinhaPartido, MunicipioComparado } from './tipos';

const linha = (partido: string, a: number | null, b: number | null): LinhaPartido => ({
  partido, pct_2022: a, pct_2026: b, delta_pp: a === null || b === null ? null : Math.round((b - a) * 100) / 100, siglas_2022: a === null ? [] : [partido],
});
const mun = (nome: string, partidos: LinhaPartido[], com2022 = true): MunicipioComparado => ({
  tse: '1', ibge: '1', nome, slug: 'x', capital: false,
  presidente: { cargo: 'presidente', uf: 'GO', municipio_tse: '1', r2022: com2022 ? ({} as never) : null, r2026: null, partidos, volatilidade: null, vencedor_2022: null, vencedor_2026: null, virou: null, apuracao_completa: true } as Comparacao,
});

describe('fraseDestaque', () => {
  test('test_frase_maior_variacao: maior |delta| entre partidos presentes nos dois anos, sem artigo', () => {
    const m = mun('ANÁPOLIS', [linha('PT', 30, 28.5), linha('PL', 40, 51.5), linha('NOVO', null, 20), linha('PSD', 10, 2)]);
    expect(fraseDestaque(m)).toBe('Em Anápolis, PL cresceu 11,5 pontos percentuais desde 2022');
  });
  test('queda usa "caiu" e número sem sinal', () => {
    const m = mun('ANÁPOLIS', [linha('PT', 40, 30.25), linha('PL', 40, 41)]);
    expect(fraseDestaque(m)).toBe('Em Anápolis, PT caiu 9,8 pontos percentuais desde 2022');
  });
  test('singular abaixo de 2 e plural a partir de 2', () => {
    expect(fraseDestaque(mun('X', [linha('PL', 40, 41.5)]))).toBe('Em X, PL cresceu 1,5 ponto percentual desde 2022');
    expect(fraseDestaque(mun('X', [linha('PL', 40, 38.2)]))).toBe('Em X, PL caiu 1,8 ponto percentual desde 2022');
    expect(fraseDestaque(mun('X', [linha('PL', 40, 42)]))).toBe('Em X, PL cresceu 2,0 pontos percentuais desde 2022');
  });
  test('variação 0,0 vira "ficou estável"', () => {
    expect(fraseDestaque(mun('X', [linha('PL', 40, 40.03)]))).toBe('Em X, PL ficou estável em relação a 2022');
  });
  test('partido feminino não leva artigo', () => {
    expect(fraseDestaque(mun('X', [linha('UNIÃO', 10, 15)]))).toBe('Em X, UNIÃO cresceu 5,0 pontos percentuais desde 2022');
  });
  test('test_frase_sem_2022', () => {
    const m = mun('BOA ESPERANÇA DO NORTE', [linha('PL', null, 60)], false);
    expect(fraseDestaque(m)).toBe('Primeira eleição presidencial de Boa Esperança do Norte');
  });
  test('com 2022 mas sem partido nos dois anos: texto neutro, não "primeira eleição"', () => {
    const f = fraseDestaque(mun('X', [linha('PL', null, 60)]));
    expect(f).toBe('Veja como votou X em 2022 e 2026');
    expect(f).not.toContain('Primeira');
  });
  test('test_frase_cabe_em_120_caracteres: usa p.p., depois trunca o nome, nunca o número', () => {
    const nome = 'MUNICÍPIO COM UM NOME ABSURDAMENTE LONGO '.repeat(5).trim();
    const f = fraseDestaque(mun(nome, [linha('UNIÃO', 40, 51.5)]));
    expect(f.length).toBeLessThanOrEqual(120);
    expect(f).toContain('UNIÃO cresceu 11,5 p.p. desde 2022');
    expect(f).toContain('…');
    expect(fraseDestaque(mun(nome, [], false)).length).toBeLessThanOrEqual(120);
    // nome médio: cabe com "p.p." mas não com "pontos percentuais"
    const medio = 'A'.repeat(70);
    const g = fraseDestaque(mun(medio, [linha('PL', 40, 51.5)]));
    expect(g.length).toBeLessThanOrEqual(120);
    expect(g).toContain('A' + 'a'.repeat(69));
    expect(g).not.toContain('…');
  });
});
