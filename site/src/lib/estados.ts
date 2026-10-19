// Nomes das 27 UFs com a preposição certa: "do Espírito Santo", "da Bahia", "de Goiás";
// "no Espírito Santo", "na Bahia", "em Goiás". Módulo puro (seguro para o navegador).

type Artigo = 'o' | 'a' | '';

const ESTADOS: Record<string, { nome: string; artigo: Artigo }> = {
  AC: { nome: 'Acre', artigo: 'o' },
  AL: { nome: 'Alagoas', artigo: '' },
  AM: { nome: 'Amazonas', artigo: 'o' },
  AP: { nome: 'Amapá', artigo: 'o' },
  BA: { nome: 'Bahia', artigo: 'a' },
  CE: { nome: 'Ceará', artigo: 'o' },
  DF: { nome: 'Distrito Federal', artigo: 'o' },
  ES: { nome: 'Espírito Santo', artigo: 'o' },
  GO: { nome: 'Goiás', artigo: '' },
  MA: { nome: 'Maranhão', artigo: 'o' },
  MG: { nome: 'Minas Gerais', artigo: '' },
  MS: { nome: 'Mato Grosso do Sul', artigo: 'o' },
  MT: { nome: 'Mato Grosso', artigo: 'o' },
  PA: { nome: 'Pará', artigo: 'o' },
  PB: { nome: 'Paraíba', artigo: 'a' },
  PE: { nome: 'Pernambuco', artigo: '' },
  PI: { nome: 'Piauí', artigo: 'o' },
  PR: { nome: 'Paraná', artigo: 'o' },
  RJ: { nome: 'Rio de Janeiro', artigo: 'o' },
  RN: { nome: 'Rio Grande do Norte', artigo: 'o' },
  RO: { nome: 'Rondônia', artigo: '' },
  RR: { nome: 'Roraima', artigo: '' },
  RS: { nome: 'Rio Grande do Sul', artigo: 'o' },
  SC: { nome: 'Santa Catarina', artigo: '' },
  SE: { nome: 'Sergipe', artigo: '' },
  SP: { nome: 'São Paulo', artigo: '' },
  TO: { nome: 'Tocantins', artigo: 'o' },
};

function estado(uf: string) {
  const e = ESTADOS[uf.toUpperCase()];
  if (!e) throw new Error(`UF desconhecida: ${uf}`);
  return e;
}

/** "GO" → "Goiás". */
export const nomeEstado = (uf: string): string => estado(uf).nome;

/** "ES" → "do Espírito Santo"; "BA" → "da Bahia"; "GO" → "de Goiás". */
export function doEstado(uf: string): string {
  const { nome, artigo } = estado(uf);
  return `${artigo === 'o' ? 'do' : artigo === 'a' ? 'da' : 'de'} ${nome}`;
}

/** "ES" → "no Espírito Santo"; "BA" → "na Bahia"; "GO" → "em Goiás". */
export function noEstado(uf: string): string {
  const { nome, artigo } = estado(uf);
  return `${artigo === 'o' ? 'no' : artigo === 'a' ? 'na' : 'em'} ${nome}`;
}
