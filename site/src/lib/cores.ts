// Cores dos partidos: atribuídas pela ORDEM de votação nacional no 1º turno de 2026
// (presidente, depois governador), nunca pela identidade do partido.
// Os valores vêm dos tokens aprovados (styles/tokens.css); aqui os hex servem aos testes
// e à geração de imagens. As funções públicas devolvem referências CSS (var(--sN)),
// que respeitam o modo escuro.
// Módulo puro (seguro para o navegador): a leitura dos arquivos fica em ordemPartidos.ts.

export const PALETA_CLARA = [
  '#e86518', '#703dc6', '#952342', '#245fd4', '#35b4a7', '#0e5794', '#983e1b', '#45aade',
] as const;
export const PALETA_ESCURA = [
  '#dc631e', '#8f6ce0', '#b13554', '#4a81eb', '#12a195', '#2e69b2', '#af5331', '#369dd1',
] as const;
export const OUTROS_CLARO = '#868b94';
export const OUTROS_ESCURO = '#7d828b';

/** Mapas de "quem venceu" usam só as 3 primeiras cores (validação de daltonismo). */
const CORES_NO_MAPA = 3;
const OUTROS = 'var(--outros)';

export type Tema = 'claro' | 'escuro';

const norm = (p: string) => p.trim().toUpperCase();

export function criarCores(ordem: string[]) {
  const posicao = new Map<string, number>();
  for (const p of ordem) {
    const k = norm(p);
    if (!posicao.has(k) && posicao.size < PALETA_CLARA.length) posicao.set(k, posicao.size);
  }
  const indice = (p: string) => posicao.get(norm(p));
  return {
    corDoPartido(partido: string): string {
      const i = indice(partido);
      return i === undefined ? OUTROS : `var(--s${i + 1})`;
    },
    corDoPartidoMapa(partido: string): string {
      const i = indice(partido);
      return i === undefined || i >= CORES_NO_MAPA ? OUTROS : `var(--s${i + 1})`;
    },
    corHex(partido: string, tema: Tema = 'claro'): string {
      const i = indice(partido);
      if (i === undefined) return tema === 'claro' ? OUTROS_CLARO : OUTROS_ESCURO;
      return (tema === 'claro' ? PALETA_CLARA : PALETA_ESCURA)[i];
    },
  };
}

let padrao = criarCores([]);

/** Define a ordem nacional usada pelas funções abaixo (chamada por ordemPartidos.ts no build). */
export function definirOrdem(ordem: string[]): void {
  padrao = criarCores(ordem);
}

export const corDoPartido = (partido: string): string => padrao.corDoPartido(partido);
export const corDoPartidoMapa = (partido: string): string => padrao.corDoPartidoMapa(partido);
export const corHex = (partido: string, tema: Tema = 'claro'): string => padrao.corHex(partido, tema);

/**
 * Cores de UM mapa: os 3 partidos que mais venceram nas regiões mostradas (desempate alfabético)
 * ganham var(--s1..s3); os demais ficam em var(--outros). `null` (sem vencedor) é ignorado.
 */
export function coresDoMapa(vencedores: (string | null)[]): Record<string, string> {
  const contagem = new Map<string, number>();
  for (const v of vencedores) if (v) contagem.set(norm(v), (contagem.get(norm(v)) ?? 0) + 1);
  const ordem = [...contagem.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'pt-BR'));
  const cores: Record<string, string> = {};
  ordem.forEach(([p], i) => { cores[p] = i < CORES_NO_MAPA ? `var(--s${i + 1})` : OUTROS; });
  return cores;
}

/** Cor de um partido num mapa montado com `coresDoMapa`. */
export const corNoMapa = (cores: Record<string, string>, partido: string | null): string =>
  (partido && cores[norm(partido)]) || OUTROS;
