import { describe, expect, test } from 'vitest';
import { doEstado, noEstado, nomeEstado } from './estados';
import { UFS } from './dados';

// [uf, "do/da/de ...", "no/na/em ..."] para as 27 UFs
const ESPERADO: [string, string, string][] = [
  ['AC', 'do Acre', 'no Acre'],
  ['AL', 'de Alagoas', 'em Alagoas'],
  ['AM', 'do Amazonas', 'no Amazonas'],
  ['AP', 'do Amapá', 'no Amapá'],
  ['BA', 'da Bahia', 'na Bahia'],
  ['CE', 'do Ceará', 'no Ceará'],
  ['DF', 'do Distrito Federal', 'no Distrito Federal'],
  ['ES', 'do Espírito Santo', 'no Espírito Santo'],
  ['GO', 'de Goiás', 'em Goiás'],
  ['MA', 'do Maranhão', 'no Maranhão'],
  ['MG', 'de Minas Gerais', 'em Minas Gerais'],
  ['MS', 'do Mato Grosso do Sul', 'no Mato Grosso do Sul'],
  ['MT', 'do Mato Grosso', 'no Mato Grosso'],
  ['PA', 'do Pará', 'no Pará'],
  ['PB', 'da Paraíba', 'na Paraíba'],
  ['PE', 'de Pernambuco', 'em Pernambuco'],
  ['PI', 'do Piauí', 'no Piauí'],
  ['PR', 'do Paraná', 'no Paraná'],
  ['RJ', 'do Rio de Janeiro', 'no Rio de Janeiro'],
  ['RN', 'do Rio Grande do Norte', 'no Rio Grande do Norte'],
  ['RO', 'de Rondônia', 'em Rondônia'],
  ['RR', 'de Roraima', 'em Roraima'],
  ['RS', 'do Rio Grande do Sul', 'no Rio Grande do Sul'],
  ['SC', 'de Santa Catarina', 'em Santa Catarina'],
  ['SE', 'de Sergipe', 'em Sergipe'],
  ['SP', 'de São Paulo', 'em São Paulo'],
  ['TO', 'do Tocantins', 'no Tocantins'],
];

describe('estados', () => {
  test.each(ESPERADO)('%s: preposições', (uf, de, em) => {
    expect(doEstado(uf)).toBe(de);
    expect(noEstado(uf)).toBe(em);
    expect(doEstado(uf.toLowerCase())).toBe(de);
  });
  test('cobre exatamente as 27 UFs do site', () => {
    expect(ESPERADO.map(([uf]) => uf)).toEqual(UFS);
    expect(nomeEstado('GO')).toBe('Goiás');
  });
  test('UF desconhecida é erro, não texto errado', () => {
    expect(() => doEstado('XX')).toThrow();
  });
});
