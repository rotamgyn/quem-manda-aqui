// Somente servidor/build: lê a ordem nacional dos partidos nos arquivos de comparação.
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { definirOrdem } from './cores';
import { pastaDados } from './dados';

type Comparacao = { partidos?: { partido: string; pct_2026: number | null }[] };

function partidosPorVoto(arquivo: string): string[] {
  const dados = JSON.parse(readFileSync(arquivo, 'utf-8')) as Comparacao;
  return [...(dados.partidos ?? [])]
    .filter((l) => l.pct_2026 !== null && l.pct_2026 !== undefined)
    .sort((a, b) => (b.pct_2026 as number) - (a.pct_2026 as number))
    .map((l) => l.partido);
}

/** Presidente (br-presidente.json) por votação, depois `*-governador.json`. Sem dados → []. */
export function lerOrdemNacional(pasta: string = pastaDados()): string[] {
  const comp = resolve(pasta, 'comparacoes');
  const presidente = resolve(comp, 'br-presidente.json');
  if (!existsSync(presidente)) return [];
  const ordem = partidosPorVoto(presidente);
  for (const f of readdirSync(comp).filter((n) => n.endsWith('-governador.json')).sort()) {
    ordem.push(...partidosPorVoto(resolve(comp, f)));
  }
  return ordem;
}

/** Carrega a ordem real em `cores.ts`. Chamar no frontmatter das páginas que usam cores. */
export function carregarOrdemNacional(): void {
  definirOrdem(lerOrdemNacional());
}
