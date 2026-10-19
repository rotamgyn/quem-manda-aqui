import { describe, expect, test } from 'vitest';
import { inteiro, nomeProprio, nomeUF, pct, pctApuracao, pctSecoes, pp, rotuloSituacao } from './formato';

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
  test('pctApuracao trunca e nunca mostra 100%', () => {
    expect(pctApuracao(99.996)).toBe('99,99%');
    expect(pctApuracao(100)).toBe('99,99%');
    expect(pctApuracao(87.5)).toBe('87,5%');
  });
  test('nomeUF converte caixa alta em nome próprio', () => {
    expect(nomeUF('MATO GROSSO DO SUL')).toBe('Mato Grosso do Sul');
    expect(nomeUF('GOIÁS')).toBe('Goiás');
  });
  test('rotuloSituacao mapeia a situação direto', () => {
    const c = (situacao: string) => ({ situacao }) as never;
    expect(rotuloSituacao(c('2º turno'))).toBe('vai ao 2º turno');
    expect(rotuloSituacao(c('eleito'))).toBe('eleito');
    expect(rotuloSituacao(c('não eleito'))).toBe('não eleito');
    expect(rotuloSituacao(c(''))).toBe('—');
  });
});

describe('nomeProprio', () => {
  test('capitaliza e mantém partículas em minúsculas', () => {
    expect(nomeProprio('ANÁPOLIS')).toBe('Anápolis');
    expect(nomeProprio('BOA ESPERANÇA DO NORTE')).toBe('Boa Esperança do Norte');
  });
  test("trata d' e hífen", () => {
    expect(nomeProprio("SÃO JOÃO D'ALIANÇA")).toBe("São João d'Aliança");
    expect(nomeProprio("PINGO-D'ÁGUA")).toBe("Pingo-d'Água");
    expect(nomeProprio('SÃO JOÃO DEL-REI')).toBe('São João del-Rei');
  });
  test('é idempotente', () => {
    expect(nomeProprio("São João d'Aliança")).toBe("São João d'Aliança");
  });
});

describe('pctSecoes', () => {
  test('trunca e só mostra 100% quando completo', () => {
    expect(pctSecoes(99.999)).toBe('99,99%');
    expect(pctSecoes(100)).toBe('100%');
    expect(pctSecoes(87.456)).toBe('87,45%');
  });
});
