import { describe, expect, test } from 'vitest';
import {
  UFS, dividirLinhaCsv, formatarDataHora, lerComparacao, lerEquivalenciasDeTexto, verificarMaioria, lerMeta, lerMunicipiosUF, lerRanking,
} from './dados';

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

describe('leitura dos dados gerados', () => {
  test('comparação nacional de presidente tem partidos', () => {
    const c = lerComparacao('br', 'presidente');
    expect(c.partidos[0].partido).toBeTruthy();
    expect(c.cargo).toBe('presidente');
  });
  test('municípios de GO incluem Goiânia (tse 93734)', () => {
    expect(lerMunicipiosUF('go').some((m) => m.tse === '93734')).toBe(true);
  });
  test('27 UFs, com governador para cada uma', () => {
    expect(UFS).toHaveLength(27);
    expect(lerComparacao('go', 'governador').nome).toBe('GOIÁS');
  });
  test('ranking vem ordenado por volatilidade e meta existe', () => {
    const r = lerRanking();
    expect(r[0].volatilidade).toBeGreaterThanOrEqual(r[1].volatilidade);
    expect(lerMeta()?.gerado_em).toBeTruthy();
  });
});

describe('guarda de maioria no 1º turno', () => {
  const comp = (situacao: string, votos: number) => ({
    cargo: 'governador', uf: 'XX',
    r2026: { validos: 100, candidatos: [{ nome_urna: 'A', votos, situacao }] },
  }) as never;
  test('eleito sem maioria absoluta interrompe', () => {
    expect(() => verificarMaioria(comp('eleito', 50))).toThrow(/maioria absoluta/);
  });
  test('eleito com maioria e 2º turno passam', () => {
    expect(() => verificarMaioria(comp('eleito', 51))).not.toThrow();
    expect(() => verificarMaioria(comp('2º turno', 40))).not.toThrow();
  });
});
