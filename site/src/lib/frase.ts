// Frase de destaque de cada município (presidente, 2026 contra 2022). Texto neutro.
import { nomeProprio } from './formato';
import type { MunicipioComparado } from './tipos';

export const MAX_FRASE = 120;

/** Corta o nome (nunca o resto da frase) para a frase inteira caber em `MAX_FRASE`. */
function montar(nome: string, antes: (n: string) => string): string {
  const completa = antes(nome);
  if (completa.length <= MAX_FRASE) return completa;
  const sobra = MAX_FRASE - antes('').length - 1;
  return antes(`${nome.slice(0, Math.max(sobra, 1)).trimEnd()}…`);
}

export function fraseDestaque(m: MunicipioComparado): string {
  const nome = nomeProprio(m.nome);
  const c = m.presidente;
  let maior: { partido: string; delta: number } | null = null;
  if (c.r2022) {
    for (const l of c.partidos) {
      if (l.pct_2022 === null || l.pct_2026 === null || l.delta_pp === null) continue;
      if (!maior || Math.abs(l.delta_pp) > Math.abs(maior.delta)) maior = { partido: l.partido, delta: l.delta_pp };
    }
  }
  if (!maior) return montar(nome, (n) => `Primeira eleição presidencial de ${n}`);
  const { partido, delta } = maior;
  const numero = Math.abs(delta).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const verbo = delta > 0 ? 'cresceu' : delta < 0 ? 'caiu' : 'ficou estável, com variação de';
  return montar(nome, (n) => `Em ${n}, o ${partido} ${verbo} ${numero} pontos desde 2022`);
}
