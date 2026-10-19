import { describe, expect, test } from 'vitest';
import { dividirLinhaCsv, formatarDataHora, lerEquivalenciasDeTexto } from './dados';

describe('dados', () => {
  test('csv com vírgula dentro de aspas', () => {
    expect(dividirLinhaCsv('PTB,PRD,"Fusão, 2023 (TSE)"')).toEqual(['PTB', 'PRD', 'Fusão, 2023 (TSE)']);
  });
  test('equivalências ignoram cabeçalho e linhas vazias', () => {
    const t = 'sigla_origem,sigla_destino,nota\nPSC,PODE,"Incorporação"\n\n';
    expect(lerEquivalenciasDeTexto(t)).toEqual([{ origem: 'PSC', destino: 'PODE', nota: 'Incorporação' }]);
  });
  test('data em horário de Brasília', () => {
    expect(formatarDataHora('2026-10-05T05:14:00+00:00')).toBe('05/10/2026 às 02:14');
    expect(formatarDataHora('lixo')).toBe('lixo');
  });
});
