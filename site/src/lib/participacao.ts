// Comparecimento, abstenção, brancos e nulos: 2022 × 2026 (números absolutos e %).
import type { Resultado } from './tipos';

export type Medida = { n: number; pct: number | null };
export type LinhaParticipacao = {
  rotulo: string;
  /** Base do percentual: eleitores aptos, comparecimento, ou nenhuma (o próprio número de aptos). */
  base: 'aptos' | 'comparecimento' | null;
  a2022: Medida | null;
  a2026: Medida | null;
};

const razao = (n: number, total: number): number | null => (total > 0 ? (n / total) * 100 : null);

function medidas(r: Resultado | null): Record<string, Medida> | null {
  if (!r) return null;
  return {
    aptos: { n: r.aptos, pct: null },
    comparecimento: { n: r.comparecimento, pct: razao(r.comparecimento, r.aptos) },
    abstencao: { n: r.abstencao, pct: razao(r.abstencao, r.aptos) },
    brancos: { n: r.brancos, pct: razao(r.brancos, r.comparecimento) },
    nulos: { n: r.nulos, pct: razao(r.nulos, r.comparecimento) },
  };
}

/** `null` no ano sem resultado (a página escreve "sem dados de 2022"). */
export function linhasParticipacao(r2022: Resultado | null, r2026: Resultado | null): LinhaParticipacao[] {
  const a = medidas(r2022);
  const b = medidas(r2026);
  const linha = (rotulo: string, chave: string, base: LinhaParticipacao['base']): LinhaParticipacao => ({
    rotulo, base, a2022: a?.[chave] ?? null, a2026: b?.[chave] ?? null,
  });
  return [
    linha('Eleitores aptos', 'aptos', null),
    linha('Comparecimento', 'comparecimento', 'aptos'),
    linha('Abstenção', 'abstencao', 'aptos'),
    linha('Votos brancos', 'brancos', 'comparecimento'),
    linha('Votos nulos', 'nulos', 'comparecimento'),
  ];
}
