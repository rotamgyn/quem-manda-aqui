// Leitura, em tempo de build, de dados que ficam fora de site/ (dados/ e dados-comuns/).
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { Cargo, Comparacao, ItemRanking, Meta, MunicipioComparado } from './tipos';

const raiz = () => resolve(process.cwd(), '..');

/** Pasta dos dados gerados: `QMA_DADOS` ou `<repo>/dados/eleicoes-2026`. */
export const pastaDados = () => process.env.QMA_DADOS ?? resolve(raiz(), 'dados/eleicoes-2026');

export type Equivalencia = { origem: string; destino: string; nota: string };
export type { Meta };

/** Divide uma linha CSV respeitando campos entre aspas (aspas duplas escapadas com ""). */
export function dividirLinhaCsv(linha: string): string[] {
  const campos: string[] = [];
  let atual = '';
  let aspas = false;
  for (let i = 0; i < linha.length; i++) {
    const c = linha[i];
    if (aspas) {
      if (c === '"' && linha[i + 1] === '"') { atual += '"'; i++; }
      else if (c === '"') aspas = false;
      else atual += c;
    } else if (c === '"') aspas = true;
    else if (c === ',') { campos.push(atual); atual = ''; }
    else atual += c;
  }
  campos.push(atual);
  return campos;
}

export function lerEquivalenciasDeTexto(texto: string): Equivalencia[] {
  const linhas = texto.split(/\r?\n/).filter((l) => l.trim() !== '');
  return linhas.slice(1).map((l) => {
    const [origem = '', destino = '', nota = ''] = dividirLinhaCsv(l);
    return { origem: origem.trim(), destino: destino.trim(), nota: nota.trim() };
  });
}

export function lerEquivalencias(): Equivalencia[] {
  const caminho = resolve(raiz(), 'dados-comuns/partidos-equivalencias.csv');
  return lerEquivalenciasDeTexto(readFileSync(caminho, 'utf-8'));
}

/** `meta.json` do pipeline; `null` quando os dados ainda não foram gerados. */
export function lerMeta(): Meta | null {
  const caminho = resolve(pastaDados(), 'meta.json');
  return existsSync(caminho) ? (JSON.parse(readFileSync(caminho, 'utf-8')) as Meta) : null;
}

/** "2026-10-05T02:14:00-03:00" → "05/10/2026 às 02:14" (horário de Brasília). */
export function formatarDataHora(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const p = Object.fromEntries(
    new Intl.DateTimeFormat('pt-BR', {
      timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(d).map((x) => [x.type, x.value]),
  );
  return `${p.day}/${p.month}/${p.year} às ${p.hour}:${p.minute}`;
}

/** As 27 unidades da federação (sem BR e sem o exterior, ZZ). */
export const UFS: string[] = [
  'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA',
  'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO',
];

const lerJson = <T>(...partes: string[]): T => JSON.parse(readFileSync(resolve(pastaDados(), ...partes), 'utf-8')) as T;

/** Comparação 2022 × 2026 de uma abrangência ('br', sigla de UF ou 'zz' para o exterior). */
/**
 * Guarda de integridade: no 1º turno só é "eleito" quem tem mais da metade dos votos válidos.
 * Qualquer outro caso é erro nos dados e interrompe o build, em vez de ser mascarado.
 */
export function verificarMaioria(c: Comparacao): void {
  const r = c.r2026;
  if (!r) return;
  for (const cand of r.candidatos) {
    if (cand.situacao === 'eleito' && !(r.validos > 0 && cand.votos * 2 > r.validos)) {
      throw new Error(
        `Dados inconsistentes: ${cand.nome_urna} (${c.cargo}, ${c.uf}) consta como "eleito" no 1º turno sem maioria absoluta dos votos válidos (${cand.votos} de ${r.validos}).`,
      );
    }
  }
}

/** Comparação 2022 × 2026 de uma abrangência ('br', sigla de UF ou 'zz' para o exterior). */
export function lerComparacao(abr: string, cargo: Cargo): Comparacao {
  const c = lerJson<Comparacao>('comparacoes', `${abr.toLowerCase()}-${cargo}.json`);
  verificarMaioria(c);
  return c;
}

export function lerMunicipiosUF(uf: string): MunicipioComparado[] {
  return lerJson<{ municipios: MunicipioComparado[] }>('municipios', `${uf.toLowerCase()}.json`).municipios;
}

/** Ranking nacional de volatilidade (presidente), já ordenado do maior para o menor. */
export function lerRanking(): ItemRanking[] {
  return lerJson<ItemRanking[]>('ranking-presidente.json');
}

/** Como `lerMeta`, mas falha o build se os dados ainda não foram gerados. */
export function lerMetaObrigatoria(): Meta {
  const meta = lerMeta();
  if (!meta) throw new Error('dados/eleicoes-2026/meta.json não encontrado: gere os dados antes de montar o site.');
  return meta;
}
