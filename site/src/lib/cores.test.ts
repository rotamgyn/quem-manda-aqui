import { describe, expect, test } from 'vitest';
import {
  PALETA_CLARA,
  PALETA_ESCURA,
  OUTROS_CLARO,
  OUTROS_ESCURO,
  corEm,
  coresDoMapa,
  coresPorPosicao,
  corNoMapa,
  ordemPorPosicao,
} from './cores';

const l = (partido: string, pct_2026: number | null, pct_2022: number | null = null) => ({ partido, pct_2026, pct_2022 });

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

describe('cores por posição no gráfico', () => {
  test('ordena por % de 2026, depois % de 2022; ausentes por último', () => {
    const linhas = [l('C', null, 50), l('A', 10, 5), l('B', 30), l('D', null, 70), l('E', 10, 9)];
    expect(ordemPorPosicao(linhas)).toEqual(['B', 'E', 'A', 'D', 'C']);
  });

  test('os 8 primeiros recebem --s1..--s8, distintos; o resto fica cinza', () => {
    const linhas = 'ABCDEFGHIJ'.split('').map((p, i) => l(p, 100 - i));
    const c = coresPorPosicao(linhas);
    expect(c.A).toBe('var(--s1)');
    expect(c.H).toBe('var(--s8)');
    expect(new Set('ABCDEFGH'.split('').map((p) => c[p])).size).toBe(8);
    expect(c.I).toBe('var(--outros)');
    expect(corEm(c, 'NOVO')).toBe('var(--outros)');
    expect(corEm(c, ' a ')).toBe('var(--s1)');
  });

  test('o vencedor de um estado nunca fica cinza (cor depende só do próprio gráfico)', () => {
    // Ex.: SP governador, REPUBLICANOS 1º no estado, mas fora do topo nacional
    const c = coresPorPosicao([l('PT', 30), l('REPUBLICANOS', 45), l('PL', 20)]);
    expect(c.REPUBLICANOS).toBe('var(--s1)');
  });

  test('hex claro e escuro por posição', () => {
    const linhas = [l('X', 60), l('Y', 40)];
    expect(coresPorPosicao(linhas, 'claro')).toMatchObject({ X: PALETA_CLARA[0], Y: PALETA_CLARA[1] });
    expect(coresPorPosicao(linhas, 'escuro')).toMatchObject({ X: PALETA_ESCURA[0] });
    const muitas = 'ABCDEFGHIJ'.split('').map((p, i) => l(p, 100 - i));
    expect(coresPorPosicao(muitas, 'claro').J).toBe(OUTROS_CLARO);
    expect(coresPorPosicao(muitas, 'escuro').J).toBe(OUTROS_ESCURO);
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

describe('coresDoMapa', () => {
  test('3 partidos mais vitoriosos recebem 3 cores distintas; o resto fica em outros', () => {
    const v = [...Array(5).fill('AA'), ...Array(4).fill('BB'), ...Array(3).fill('CC'), 'DD', 'DD', 'EE', null];
    const c = coresDoMapa(v);
    expect(c.AA).toBe('var(--s1)');
    expect(c.BB).toBe('var(--s2)');
    expect(c.CC).toBe('var(--s3)');
    expect(c.DD).toBe('var(--outros)');
    expect(corNoMapa(c, 'EE')).toBe('var(--outros)');
    expect(corNoMapa(c, null)).toBe('var(--outros)');
    expect(corNoMapa(c, 'ZZ')).toBe('var(--outros)');
  });
  test('empate é resolvido em ordem alfabética, independente da ordem de entrada', () => {
    const a = coresDoMapa(['ZZ', 'BB', 'AA', 'CC', 'DD']);
    const b = coresDoMapa(['DD', 'CC', 'AA', 'BB', 'ZZ']);
    expect(a).toEqual(b);
    expect([a.AA, a.BB, a.CC, a.DD]).toEqual(['var(--s1)', 'var(--s2)', 'var(--s3)', 'var(--outros)']);
  });
});
