// Leitura, em tempo de build, de dados que ficam fora de site/ (dados/ e dados-comuns/).
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const raiz = () => resolve(process.cwd(), '..');

export type Equivalencia = { origem: string; destino: string; nota: string };
export type Meta = { gerado_em: string; fonte_2026_dg_hg: string; pct_secoes_br: number };

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
  const pasta = process.env.QMA_DADOS ?? resolve(raiz(), 'dados/eleicoes-2026');
  const caminho = resolve(pasta, 'meta.json');
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
