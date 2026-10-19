import { describe, expect, test } from 'vitest';
import { buscar, normalizar, type ItemBusca } from './busca';

const item = (n: string, uf = 'GO'): ItemBusca => ({ n, uf, u: `/eleicoes-2026/municipio/${uf.toLowerCase()}/${normalizar(n).replace(/\W+/g, '-')}/` });

describe('busca', () => {
  test('test_busca_sem_acento: "anapolis" encontra ANÁPOLIS', () => {
    const r = buscar('anapolis', [item('ANÁPOLIS'), item('SÃO PAULO', 'SP')]);
    expect(r.map((x) => x.n)).toEqual(['ANÁPOLIS']);
    expect(buscar('ANÁPOLIS', [item('Anápolis')])).toHaveLength(1);
  });
  test('test_prefixo_primeiro: começo do nome vem antes de prefixo de palavra', () => {
    const r = buscar('sao', [item('LAGOA DE SÃO X'), item('SÃO PAULO', 'SP')]);
    expect(r.map((x) => x.n)).toEqual(['SÃO PAULO', 'LAGOA DE SÃO X']);
  });
  test('prefixo de palavra vem antes de trecho no meio da palavra', () => {
    const r = buscar('paulo', [item('SANTAPAULO'), item('SÃO PAULO', 'SP')]);
    expect(r.map((x) => x.n)).toEqual(['SÃO PAULO', 'SANTAPAULO']);
  });
  test('test_maximo_8', () => {
    const indice = Array.from({ length: 20 }, (_, i) => item(`SANTA CIDADE ${String.fromCharCode(65 + i)}`));
    expect(buscar('santa', indice)).toHaveLength(8);
  });
  test('termo vazio ou só de espaços não devolve nada', () => {
    expect(buscar('   ', [item('ANÁPOLIS')])).toEqual([]);
  });
  test('apóstrofo e espaços repetidos não atrapalham', () => {
    expect(buscar("d'alianca", [item("SÃO JOÃO D'ALIANÇA")]).length).toBe(1);
    expect(buscar('  sao   joao ', [item('SÃO JOÃO D’ALIANÇA')]).length).toBe(1);
  });
});
