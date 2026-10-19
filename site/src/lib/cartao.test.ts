import { describe, expect, it } from 'vitest';
import { arvore, cartaoPNG, escolherBarras, legenda, rotulo2022 } from './cartao';
import type { LinhaPartido } from './tipos';

// Cabeçalho PNG: assinatura de 8 bytes, depois o bloco IHDR (largura e altura em 16 e 20).
const dimensoes = (png: Uint8Array) => {
  const v = new DataView(png.buffer, png.byteOffset, png.byteLength);
  return { assinatura: Array.from(png.slice(0, 4)), largura: v.getUint32(16), altura: v.getUint32(20) };
};

describe('cartaoPNG', () => {
  it('test_cartao_dimensoes: PNG de 1200x630', async () => {
    const png = await cartaoPNG('Quem manda aqui em Anápolis/GO', 'Em Anápolis, PL cresceu 3,1 pontos percentuais desde 2022', [
      { partido: 'PL', cor: '#e86518', pct2026: 41.2, pct2022: 33.8 },
      { partido: 'PT', cor: '#703dc6', pct2026: 29.5, pct2022: null },
    ]);
    expect(dimensoes(png)).toEqual({ assinatura: [0x89, 0x50, 0x4e, 0x47], largura: 1200, altura: 630 });
    expect(png.byteLength).toBeLessThan(100_000);
  });

  it('test_cartao_texto_longo_nao_quebra: frase de 120 caracteres', async () => {
    const frase = 'x'.repeat(120);
    const png = await cartaoPNG('Quem manda aqui em ' + 'Município de Nome Muito Comprido '.repeat(2) + '/GO', frase);
    expect(dimensoes(png).largura).toBe(1200);
  });
});

describe('rótulos e legenda', () => {
  it('rotulo2022 distingue município sem 2022 de partido que não disputou', () => {
    expect(rotulo2022(null, true)).toBe('Sem dados de 2022');
    expect(rotulo2022(null, false)).toBe('Não disputou em 2022');
    expect(rotulo2022(33.8, false)).toBe('2022: 33,80%');
  });

  it('legenda omite "Listrada" quando não há 2022', () => {
    expect(legenda(false)).toBe('Barra cheia: 2026. Listrada: 2022. Fonte: TSE');
    expect(legenda(true)).toBe('Barra cheia: 2026. Fonte: TSE');
  });

  const textos = (no: unknown): string[] => {
    const n = no as { props?: { children?: unknown } } | string;
    if (typeof n === 'string') return [n];
    const c = n?.props?.children;
    return c === undefined ? [] : (Array.isArray(c) ? c : [c]).flatMap(textos);
  };
  const barras = [
    { partido: 'PL', cor: '#e86518', pct2026: 41.2, pct2022: 33.8 },
    { partido: 'PSD', cor: '#35b4a7', pct2026: 11.5, pct2022: null },
  ];

  it('árvore do cartão usa o rótulo e a legenda corretos', () => {
    const com = textos(arvore('T', 'F', barras, false));
    expect(com).toContain('Não disputou em 2022');
    expect(com).toContain('2022: 33,80%');
    expect(com).toContain('Barra cheia: 2026. Listrada: 2022. Fonte: TSE');
    const sem = textos(arvore('T', 'F', barras, true));
    expect(sem.filter((t) => t === 'Sem dados de 2022')).toHaveLength(2);
    expect(sem).toContain('Barra cheia: 2026. Fonte: TSE');
    expect(sem.join('|')).not.toContain('Listrada');
  });
});

describe('escolherBarras', () => {
  const l = (partido: string, pct_2026: number | null): LinhaPartido => ({ partido, pct_2026, pct_2022: null, delta_pp: null });
  it('pega os 3 mais votados em 2026, ignora sem voto e aplica a cor', () => {
    const r = escolherBarras([l('A', 5), l('B', null), l('C', 40), l('D', 30), l('E', 20)], (p) => `#${p}`);
    expect(r.map((b) => b.partido)).toEqual(['C', 'D', 'E']);
    expect(r[0]).toMatchObject({ cor: '#C', pct2026: 40 });
  });
});
