// Cores dos partidos: atribuídas pela ORDEM de votação nacional no 1º turno de 2026
// (presidente, depois governador), nunca pela identidade do partido.
// Os valores vêm dos tokens aprovados (styles/tokens.css); aqui os hex servem aos testes
// e à geração de imagens. As funções públicas devolvem referências CSS (var(--sN)),
// que respeitam o modo escuro.
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

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

type LinhaComparacao = { partidos?: { partido: string; pct_2026: number | null }[] };

function partidosPorVoto(arquivo: string): string[] {
  const dados = JSON.parse(readFileSync(arquivo, 'utf-8')) as LinhaComparacao;
  return [...(dados.partidos ?? [])]
    .filter((l) => l.pct_2026 !== null && l.pct_2026 !== undefined)
    .sort((a, b) => (b.pct_2026 as number) - (a.pct_2026 as number))
    .map((l) => l.partido);
}

/** Lê a ordem nacional dos arquivos de comparação. Sem dados, devolve [] (tudo cinza). */
export function lerOrdemNacional(pastaDados?: string): string[] {
  const pasta = pastaDados ?? process.env.QMA_DADOS ?? resolve(process.cwd(), '../dados/eleicoes-2026');
  const comp = resolve(pasta, 'comparacoes');
  const presidente = resolve(comp, 'br-presidente.json');
  if (!existsSync(presidente)) return [];
  const ordem = partidosPorVoto(presidente);
  const governadores = readdirSync(comp).filter((f) => f.endsWith('-governador.json')).sort();
  for (const f of governadores) ordem.push(...partidosPorVoto(resolve(comp, f)));
  return ordem;
}

let padrao: ReturnType<typeof criarCores> | undefined;
const doSite = () => (padrao ??= criarCores(lerOrdemNacional()));

export const corDoPartido = (partido: string): string => doSite().corDoPartido(partido);
export const corDoPartidoMapa = (partido: string): string => doSite().corDoPartidoMapa(partido);
export const corHex = (partido: string, tema: Tema = 'claro'): string => doSite().corHex(partido, tema);
