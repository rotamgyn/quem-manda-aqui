import { describe, expect, test } from 'vitest';
import { linhasParticipacao } from './participacao';
import type { Resultado } from './tipos';

const r = (o: Partial<Resultado>): Resultado => ({ ano: 2026, turno: 1, cargo: 'presidente', uf: 'GO', municipio_tse: '1', aptos: 1000, comparecimento: 800, abstencao: 200, brancos: 40, nulos: 80, validos: 680, pct_secoes_totalizadas: 100, candidatos: [], ...o });

describe('linhasParticipacao', () => {
  test('percentuais: abstenção sobre aptos, brancos e nulos sobre comparecimento', () => {
    const l = linhasParticipacao(null, r({}));
    const por = Object.fromEntries(l.map((x) => [x.rotulo, x]));
    expect(por['Abstenção'].a2026).toEqual({ n: 200, pct: 20 });
    expect(por['Comparecimento'].a2026).toEqual({ n: 800, pct: 80 });
    expect(por['Votos brancos'].a2026).toEqual({ n: 40, pct: 5 });
    expect(por['Votos nulos'].a2026).toEqual({ n: 80, pct: 10 });
    expect(por['Votos brancos'].base).toBe('comparecimento');
    expect(por['Abstenção'].a2022).toBeNull();
  });
  test('divisor zero não gera percentual', () => {
    const l = linhasParticipacao(null, r({ aptos: 0, comparecimento: 0, abstencao: 0, brancos: 0, nulos: 0 }));
    expect(l.every((x) => x.a2026?.pct === null || x.rotulo === 'Eleitores aptos')).toBe(true);
  });
});
