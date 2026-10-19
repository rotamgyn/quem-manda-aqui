// Busca de município: módulo puro, usado no build e no navegador.

/** Item do índice `public/busca-municipios.json` (chaves curtas para o arquivo ser pequeno). */
export type ItemBusca = { n: string; uf: string; u: string };

export const MAX_RESULTADOS = 8;

/** Minúsculas, sem acentos, sem apóstrofos e com espaços simples. */
export function normalizar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLocaleLowerCase('pt-BR')
    .replace(/['’`]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

/**
 * Até 8 resultados. Ordem: nome começa com o termo; alguma palavra começa com o termo;
 * termo em qualquer parte do nome. Empate: ordem alfabética.
 */
const normalizados = new WeakMap<ItemBusca, string>(); // nome normalizado, calculado uma vez por item

export function buscar(termo: string, indice: ItemBusca[]): ItemBusca[] {
  const t = normalizar(termo);
  if (t === '') return [];
  const achados: { item: ItemBusca; nome: string; rank: number }[] = [];
  for (const item of indice) {
    let nome = normalizados.get(item);
    if (nome === undefined) { nome = normalizar(item.n); normalizados.set(item, nome); }
    const pos = nome.indexOf(t);
    if (pos < 0) continue;
    const rank = pos === 0 ? 0 : nome.includes(` ${t}`) ? 1 : 2;
    achados.push({ item, nome, rank });
  }
  achados.sort((a, b) => a.rank - b.rank || a.nome.localeCompare(b.nome, 'pt-BR') || a.item.uf.localeCompare(b.item.uf));
  return achados.slice(0, MAX_RESULTADOS).map((a) => a.item);
}
