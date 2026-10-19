import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, test } from 'vitest';
import type { Topology } from 'topojson-specification';
import { caminhosSVG, siglaDaUF } from './mapa';

const malha = (nome: string) =>
  JSON.parse(readFileSync(resolve(process.cwd(), '..', 'dados/comum/malhas', `${nome}.json`), 'utf-8')) as Topology;

describe('caminhosSVG', () => {
  test('test_um_caminho_por_feature: GO tem 246 municípios', () => {
    const c = caminhosSVG(malha('go'), 600, 600);
    expect(c).toHaveLength(246);
    expect(new Set(c.map((x) => x.codigo)).size).toBe(246);
    expect(c.every((x) => x.d.startsWith('M'))).toBe(true);
  });

  test('test_caminhos_dentro_da_caixa', () => {
    const [l, a] = [600, 500];
    for (const nome of ['go', 'br-uf']) {
      const nums = caminhosSVG(malha(nome), l, a)
        .flatMap((x) => x.d.match(/-?\d+(?:\.\d+)?/g) ?? [])
        .map(Number);
      // pares x,y alternados (comandos M/L/Z não carregam letras entre números além de separar)
      const pares = caminhosSVG(malha(nome), l, a).flatMap((x) =>
        [...x.d.matchAll(/(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g)].map((m) => [Number(m[1]), Number(m[2])]),
      );
      expect(nums.length).toBeGreaterThan(0);
      expect(pares.length).toBeGreaterThan(0);
      for (const [x, y] of pares) {
        expect(x).toBeGreaterThanOrEqual(0);
        expect(x).toBeLessThanOrEqual(l);
        expect(y).toBeGreaterThanOrEqual(0);
        expect(y).toBeLessThanOrEqual(a);
      }
    }
  });

  test('malha do Brasil: 27 UFs com sigla pelo código IBGE', () => {
    const c = caminhosSVG(malha('br-uf'), 600, 600);
    expect(c).toHaveLength(27);
    expect(siglaDaUF('52')).toBe('GO');
    expect(c.map((x) => siglaDaUF(x.codigo))).not.toContain(undefined);
  });
});
