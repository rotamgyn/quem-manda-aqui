import { describe, expect, it } from 'vitest';
import { cartaoPNG } from './cartao';

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
