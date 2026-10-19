// Formatação pt-BR de números. Módulo puro (seguro para o navegador).
import type { VotoCandidato } from './tipos';

const MENOS = '−'; // sinal de menos tipográfico

const fmt = (n: number, casas: number) =>
  n.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });

/** 47.0508 → "47,05%"; null → "—". */
export function pct(n: number | null): string {
  return n === null ? '—' : `${fmt(n, 2)}%`;
}

/** 11.5 → "+11,5 p.p."; -3.2 → "−3,2 p.p."; null → "—". */
export function pp(n: number | null): string {
  if (n === null) return '—';
  const sinal = n > 0 ? '+' : n < 0 ? MENOS : '';
  return `${sinal}${fmt(Math.abs(n), 1)} p.p.`;
}

/** 56082216 → "56.082.216". */
export function inteiro(n: number): string {
  return n.toLocaleString('pt-BR', { maximumFractionDigits: 0 });
}

/**
 * Percentual de seções totalizadas para exibição: TRUNCA em 2 casas, para que
 * 99,996 nunca apareça como "100%". Só 100 exato vira "100%".
 */
export function pctApuracao(n: number): string {
  if (n >= 100) return '100%';
  const t = Math.floor(n * 100) / 100;
  return `${t.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}%`;
}

const MINUSCULAS = new Set(['de', 'da', 'do', 'das', 'dos', 'e']);

/** "MATO GROSSO DO SUL" → "Mato Grosso do Sul". */
export function nomeUF(nome: string): string {
  return nome
    .toLocaleLowerCase('pt-BR')
    .split(' ')
    .map((p, i) => (i > 0 && MINUSCULAS.has(p) ? p : p.charAt(0).toLocaleUpperCase('pt-BR') + p.slice(1)))
    .join(' ');
}

/**
 * Rótulo da situação no 1º turno. "2º turno" nunca vira "eleito". Por segurança, um
 * candidato marcado "eleito" sem maioria absoluta dos votos válidos (a regra do 1º turno)
 * também aparece como "vai ao 2º turno".
 */
export function rotuloSituacao(c: Pick<VotoCandidato, 'situacao' | 'votos'>, validos: number): string {
  if (c.situacao === '2º turno') return 'vai ao 2º turno';
  if (c.situacao === 'eleito') return validos > 0 && c.votos * 2 <= validos ? 'vai ao 2º turno' : 'eleito';
  if (c.situacao === 'não eleito') return 'não eleito';
  return '—';
}
