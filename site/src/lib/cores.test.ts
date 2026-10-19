import { describe, expect, test } from 'vitest';
import {
  PALETA_CLARA,
  PALETA_ESCURA,
  OUTROS_CLARO,
  OUTROS_ESCURO,
  criarCores,
  corDoPartido,
} from './cores';

const ORDEM = ['AA', 'BB', 'CC', 'DD', 'EE', 'FF', 'GG', 'HH', 'II', 'JJ'];

function hsl(hex: string): { h: number; s: number; l: number } {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  if (d === 0) return { h: 0, s: 0, l };
  const s = d / (1 - Math.abs(2 * l - 1));
  let h: number;
  if (max === r) h = ((g - b) / d) % 6;
  else if (max === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;
  return { h: (h * 60 + 360) % 360, s, l };
}

describe('cores dos partidos', () => {
  test('test_mesma_cor_para_mesmo_partido', () => {
    const c = criarCores(ORDEM);
    expect(c.corDoPartido('BB')).toBe(c.corDoPartido('BB'));
    expect(c.corDoPartido('bb ')).toBe(c.corDoPartido('BB'));
    expect(c.corDoPartido('AA')).toBe('var(--s1)');
    expect(c.corDoPartido('HH')).toBe('var(--s8)');
    const distintas = new Set(ORDEM.slice(0, 8).map((p) => c.corDoPartido(p)));
    expect(distintas.size).toBe(8);
  });

  test('test_partido_desconhecido_cinza', () => {
    const c = criarCores(ORDEM);
    expect(c.corDoPartido('NOVO')).toBe('var(--outros)');
    expect(c.corDoPartido('II')).toBe('var(--outros)'); // 9º em diante
    expect(c.corHex('NOVO', 'claro')).toBe(OUTROS_CLARO);
    expect(c.corHex('NOVO', 'escuro')).toBe(OUTROS_ESCURO);
    expect(corDoPartido('PARTIDO-QUE-NAO-EXISTE')).toBe('var(--outros)');
  });

  test('mapa usa só as 3 primeiras cores', () => {
    const c = criarCores(ORDEM);
    expect(c.corDoPartidoMapa('AA')).toBe('var(--s1)');
    expect(c.corDoPartidoMapa('CC')).toBe('var(--s3)');
    expect(c.corDoPartidoMapa('DD')).toBe('var(--outros)');
    expect(c.corDoPartidoMapa('NOVO')).toBe('var(--outros)');
  });

  test('corHex devolve o hex do tema', () => {
    const c = criarCores(ORDEM);
    expect(c.corHex('AA', 'claro')).toBe(PALETA_CLARA[0]);
    expect(c.corHex('AA', 'escuro')).toBe(PALETA_ESCURA[0]);
  });

  test('ordem duplicada conta uma vez', () => {
    const c = criarCores(['AA', 'AA', 'BB']);
    expect(c.corDoPartido('BB')).toBe('var(--s2)');
  });

  test('test_paleta_sem_verde_amarelo', () => {
    const todas = [...PALETA_CLARA, ...PALETA_ESCURA, OUTROS_CLARO, OUTROS_ESCURO];
    expect(PALETA_CLARA).toHaveLength(8);
    expect(PALETA_ESCURA).toHaveLength(8);
    for (const hex of todas) {
      const { h, s } = hsl(hex);
      const proibida = h >= 45 && h <= 150 && s > 0.4;
      expect(proibida, `${hex} h=${h.toFixed(0)} s=${s.toFixed(2)}`).toBe(false);
    }
  });
});

describe('ordem nacional lida dos arquivos', () => {
  test('presidente por votação, depois governadores; sem dados → vazio', async () => {
    const { mkdtempSync, mkdirSync, writeFileSync } = await import('node:fs');
    const { tmpdir } = await import('node:os');
    const { join } = await import('node:path');
    const { lerOrdemNacional } = await import('./cores');
    const base = mkdtempSync(join(tmpdir(), 'qma-'));
    expect(lerOrdemNacional(base)).toEqual([]);
    mkdirSync(join(base, 'comparacoes'));
    const arq = (nome: string, ps: [string, number | null][]) =>
      writeFileSync(join(base, 'comparacoes', nome), JSON.stringify({ partidos: ps.map(([partido, pct_2026]) => ({ partido, pct_2026 })) }));
    arq('br-presidente.json', [['B', 20], ['A', 50], ['X', null]]);
    arq('go-governador.json', [['C', 10], ['A', 70]]);
    expect(lerOrdemNacional(base)).toEqual(['A', 'B', 'A', 'C']);
    expect(criarCores(lerOrdemNacional(base)).corDoPartido('C')).toBe('var(--s3)');
  });
});
