// Frase de destaque de cada município (presidente, 2026 contra 2022). Texto neutro.
import { nomeProprio } from './formato';
import type { MunicipioComparado } from './tipos';

export const MAX_FRASE = 120;

/**
 * Tenta cada variante com o nome inteiro, da mais clara para a mais curta; se nenhuma couber,
 * corta o NOME (nunca o número) na variante mais curta.
 */
function montar(nome: string, variantes: ((n: string) => string)[]): string {
  for (const v of variantes) {
    const f = v(nome);
    if (f.length <= MAX_FRASE) return f;
  }
  const curta = variantes[variantes.length - 1]!;
  const sobra = MAX_FRASE - curta('').length - 1;
  return curta(`${nome.slice(0, Math.max(sobra, 1)).trimEnd()}…`);
}

export function fraseDestaque(m: MunicipioComparado): string {
  const nome = nomeProprio(m.nome);
  const c = m.presidente;
  if (!c.r2022) return montar(nome, [(n) => `Primeira eleição presidencial de ${n}`]);

  let maior: { partido: string; delta: number } | null = null;
  for (const l of c.partidos) {
    if (l.pct_2022 === null || l.pct_2026 === null || l.delta_pp === null) continue;
    if (!maior || Math.abs(l.delta_pp) > Math.abs(maior.delta)) maior = { partido: l.partido, delta: l.delta_pp };
  }
  if (!maior) return montar(nome, [(n) => `Veja como votou ${n} em 2022 e 2026`]);

  const { partido, delta } = maior;
  const arredondado = Math.round(Math.abs(delta) * 10) / 10;
  if (arredondado === 0) return montar(nome, [(n) => `Em ${n}, ${partido} ficou estável em relação a 2022`]);

  const numero = arredondado.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const verbo = delta > 0 ? 'cresceu' : 'caiu';
  // regra do português: singular até 1,99
  const unidade = arredondado < 2 ? 'ponto percentual' : 'pontos percentuais';
  return montar(nome, [
    (n) => `Em ${n}, ${partido} ${verbo} ${numero} ${unidade} desde 2022`,
    (n) => `Em ${n}, ${partido} ${verbo} ${numero} p.p. desde 2022`,
  ]);
}
