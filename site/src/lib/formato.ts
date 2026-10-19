// Formatação pt-BR de números. Módulo puro (seguro para o navegador).
import type { LinhaPartido, Resultado, VotoCandidato } from './tipos';

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

const MINUSCULAS = new Set(['de', 'da', 'do', 'das', 'dos', 'e']);

/** "MATO GROSSO DO SUL" → "Mato Grosso do Sul". */
export function nomeUF(nome: string): string {
  return nome
    .toLocaleLowerCase('pt-BR')
    .split(' ')
    .map((p, i) => (i > 0 && MINUSCULAS.has(p) ? p : p.charAt(0).toLocaleUpperCase('pt-BR') + p.slice(1)))
    .join(' ');
}

/** Rótulo da situação no 1º turno, direto do campo `situacao` dos dados. */
export function rotuloSituacao(c: Pick<VotoCandidato, 'situacao'>): string {
  if (c.situacao === '2º turno') return 'vai ao 2º turno';
  if (c.situacao === 'eleito') return 'eleito';
  if (c.situacao === 'não eleito') return 'não eleito';
  return '—';
}

/**
 * Nota sob a tabela de resultado quando há candidatos com votos anulados (inclusive sub judice):
 * esses votos não entram nos votos válidos nem nos percentuais. `null` quando não há.
 */
export function notaAnulados(r: Partial<Pick<Resultado, 'anulados'>>): string | null {
  const lista = r.anulados ?? [];
  if (lista.length === 0) return null;
  const itens = lista.map((c) => `${c.nome_urna} (${c.partido}), ${inteiro(c.votos)} ${c.votos === 1 ? 'voto' : 'votos'}`);
  return `Votos anulados (inclusive sub judice): ${itens.join('; ')} — não entram nos percentuais nem nos votos válidos.`;
}

type Siglas = Pick<LinhaPartido, 'partido' | 'siglas_2022'>;
const converteu = (l: Siglas) => l.siglas_2022.length > 0 && !(l.siglas_2022.length === 1 && l.siglas_2022[0] === l.partido);

/**
 * Sigla com que a linha concorreu em 2022: "PSC (hoje PODE)", "PATRIOTA + PTB (hoje PRD)" ou só "PL".
 * Sem linha, usa `reserva`.
 */
export function sigla2022(l: Siglas | undefined, reserva = ''): string {
  if (!l) return reserva;
  return converteu(l) ? `${l.siglas_2022.join(' + ')} (hoje ${l.partido})` : l.partido;
}

/** Notas para tabelas: "PRD em 2022 = PATRIOTA + PTB", uma por linha que soma siglas convertidas. */
export function notasSiglas2022(linhas: Siglas[]): string[] {
  return linhas.filter(converteu).map((l) => `${l.partido} em 2022 = ${l.siglas_2022.join(' + ')}`);
}

/**
 * Percentual de seções totalizadas, sempre com 2 casas e TRUNCADO (nunca arredondado para cima).
 * "100,00%" só aparece quando quem chama informa que a totalização está completa; caso contrário
 * o valor nunca passa de 99,99%.
 */
export function pctSecoes(n: number, completa: boolean): string {
  if (completa) return '100,00%';
  const t = Math.min(Math.floor(Number((n * 100).toFixed(6))) / 100, 99.99);
  return `${fmt(t, 2)}%`;
}

const PARTICULAS = new Set([...MINUSCULAS, 'del']);
const maiuscula1 = (s: string) => s.charAt(0).toLocaleUpperCase('pt-BR') + s.slice(1);

/** Uma palavra já em minúsculas: "d'água" → "d'Água"; partícula fica minúscula (exceto a primeira). */
function palavraProprio(p: string, primeira: boolean): string {
  if (!primeira && PARTICULAS.has(p)) return p;
  const apostrofo = /^(d)(['’])(.+)$/.exec(p);
  if (apostrofo) return `${primeira ? 'D' : 'd'}${apostrofo[2]}${maiuscula1(apostrofo[3]!)}`;
  return maiuscula1(p);
}

/**
 * Nome de município do TSE (MAIÚSCULAS) em caixa de título, com partículas em minúsculas:
 * "SÃO JOÃO D'ALIANÇA" → "São João d'Aliança".
 */
export function nomeProprio(nome: string): string {
  return nome
    .toLocaleLowerCase('pt-BR')
    .split(' ')
    .filter((p) => p !== '')
    .map((palavra, i) =>
      palavra.split('-').map((parte, j) => palavraProprio(parte, i === 0 && j === 0)).join('-'),
    )
    .join(' ');
}
