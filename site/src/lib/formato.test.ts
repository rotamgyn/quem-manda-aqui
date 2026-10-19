import { describe, expect, test } from 'vitest';
import { inteiro, nomeUF, pct, pctApuracao, pp, rotuloSituacao } from './formato';

describe('formato', () => {
  test('pct usa vírgula e duas casas; null vira travessão', () => {
    expect(pct(47.0508)).toBe('47,05%');
    expect(pct(0)).toBe('0,00%');
    expect(pct(null)).toBe('—');
  });
  test('pp tem sinal e usa menos tipográfico', () => {
    expect(pp(-3.2)).toBe('−3,2 p.p.');
    expect(pp(11.5)).toBe('+11,5 p.p.');
    expect(pp(0)).toBe('0,0 p.p.');
    expect(pp(null)).toBe('—');
  });
  test('inteiro usa ponto como separador de milhar', () => {
    expect(inteiro(56082216)).toBe('56.082.216');
    expect(inteiro(0)).toBe('0');
  });
  test('pctApuracao trunca em vez de arredondar para 100', () => {
    expect(pctApuracao(99.996)).toBe('99,99%');
    expect(pctApuracao(100)).toBe('100%');
    expect(pctApuracao(87.5)).toBe('87,5%');
  });
  test('nomeUF converte caixa alta em nome próprio', () => {
    expect(nomeUF('MATO GROSSO DO SUL')).toBe('Mato Grosso do Sul');
    expect(nomeUF('GOIÁS')).toBe('Goiás');
  });
  test('rotuloSituacao: 2º turno nunca aparece como eleito', () => {
    const c = (situacao: string, votos: number) => ({ situacao, votos }) as never;
    expect(rotuloSituacao(c('2º turno', 40), 100)).toBe('vai ao 2º turno');
    expect(rotuloSituacao(c('eleito', 51), 100)).toBe('eleito');
    // dado marcado "eleito" sem maioria absoluta dos válidos: ainda vai ao 2º turno
    expect(rotuloSituacao(c('eleito', 50), 100)).toBe('vai ao 2º turno');
    expect(rotuloSituacao(c('não eleito', 10), 100)).toBe('não eleito');
    expect(rotuloSituacao(c('', 10), 100)).toBe('—');
  });
});
