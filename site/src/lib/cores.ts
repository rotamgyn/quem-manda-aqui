// Cores dos partidos: atribuídas pela POSIÇÃO dentro de cada gráfico, cartão ou mapa
// (Rulings 12 e 15), nunca pela identidade do partido nem por uma ordem nacional.
// Os valores vêm dos tokens aprovados (styles/tokens.css); aqui os hex servem aos testes
// e à geração de imagens. As funções que devolvem referências CSS (var(--sN)) respeitam o
// modo escuro. Módulo puro (seguro para o navegador).
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

type PctPartido = { partido: string; pct_2026: number | null; pct_2022: number | null };

/** Ordem de um gráfico: maior % em 2026, depois maior % em 2022 (ausente conta como menor); desempate alfabético. */
export function ordemPorPosicao(linhas: PctPartido[]): string[] {
  const v = (x: number | null) => (x === null ? -1 : x);
  return [...linhas]
    .sort((a, b) => v(b.pct_2026) - v(a.pct_2026) || v(b.pct_2022) - v(a.pct_2022) || a.partido.localeCompare(b.partido, 'pt-BR'))
    .map((l) => l.partido);
}

/**
 * Cores de UM gráfico ou cartão: os 8 primeiros por `ordemPorPosicao` recebem as 8 cores, o resto fica
 * cinza. Sem tema: referências CSS (var(--sN), var(--outros)); com tema: os hex correspondentes.
 */
export function coresPorPosicao(linhas: PctPartido[], tema?: Tema): Record<string, string> {
  const paleta = tema === 'escuro' ? PALETA_ESCURA : PALETA_CLARA;
  const outros = tema === undefined ? OUTROS : tema === 'claro' ? OUTROS_CLARO : OUTROS_ESCURO;
  const cores: Record<string, string> = {};
  ordemPorPosicao(linhas).forEach((p, i) => {
    const k = norm(p);
    if (k in cores) return;
    cores[k] = i < paleta.length ? (tema === undefined ? `var(--s${i + 1})` : paleta[i]!) : outros;
  });
  return cores;
}

/** Cor de um partido num conjunto montado por `coresPorPosicao` (ou `coresDoMapa`); ausente → cinza. */
export const corEm = (cores: Record<string, string>, partido: string | null): string =>
  (partido && cores[norm(partido)]) || OUTROS;

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
export const corNoMapa = corEm;
