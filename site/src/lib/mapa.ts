// Geração, no build, dos caminhos SVG a partir das malhas TopoJSON (dados/comum/malhas).
// Módulo puro de geometria: a leitura dos arquivos fica nas páginas.
import { geoMercator, geoPath } from 'd3-geo';
import { feature } from 'topojson-client';
import type { Topology } from 'topojson-specification';

export type CaminhoSVG = { codigo: string; d: string };

/** Código IBGE de 2 dígitos da UF → sigla. */
const UF_POR_CODIGO: Record<string, string> = {
  '11': 'RO', '12': 'AC', '13': 'AM', '14': 'RR', '15': 'PA', '16': 'AP', '17': 'TO',
  '21': 'MA', '22': 'PI', '23': 'CE', '24': 'RN', '25': 'PB', '26': 'PE', '27': 'AL', '28': 'SE', '29': 'BA',
  '31': 'MG', '32': 'ES', '33': 'RJ', '35': 'SP', '41': 'PR', '42': 'SC', '43': 'RS',
  '50': 'MS', '51': 'MT', '52': 'GO', '53': 'DF',
};

export const siglaDaUF = (codigo: string): string | undefined => UF_POR_CODIGO[codigo];

/** Um caminho por feature da malha, projetado (Mercator) para caber em largura × altura, com 1 casa decimal. */
export function caminhosSVG(topo: Topology, largura: number, altura: number): CaminhoSVG[] {
  const nomeObjeto = Object.keys(topo.objects)[0];
  const colecao = feature(topo, topo.objects[nomeObjeto]) as unknown as GeoJSON.FeatureCollection;
  const projecao = geoMercator().fitSize([largura, altura], colecao);
  const caminho = geoPath(projecao).digits(1);
  const saida: CaminhoSVG[] = [];
  for (const f of colecao.features) {
    const d = caminho(f);
    const codigo = (f.properties as { codarea?: string } | null)?.codarea;
    if (d && codigo) saida.push({ codigo, d });
  }
  return saida;
}

export type ItemLegenda = { rotulo: string; cor: string };

/** Legenda sem repetição de cor: partidos que caem em "outros" viram uma só entrada. */
export function montarLegenda(partidos: string[], corDe: (p: string) => string, rotuloOutros = 'Demais partidos'): ItemLegenda[] {
  const itens: ItemLegenda[] = [];
  let outros = false;
  for (const p of [...new Set(partidos)]) {
    const cor = corDe(p);
    if (cor === 'var(--outros)') outros = true;
    else itens.push({ rotulo: p, cor });
  }
  if (outros) itens.push({ rotulo: rotuloOutros, cor: 'var(--outros)' });
  return itens;
}

/** "Goiânia — vencedor 2026: PL (45,2%)"; sem vencedor, diz que não há dado. */
export function rotuloVencedor(nome: string, ano: number, partido: string | null, pct: number | null): string {
  if (!partido) return `${nome} — sem dados de ${ano}`;
  const p = pct === null ? '' : ` (${pct.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%)`;
  return `${nome} — vencedor ${ano}: ${partido}${p}`;
}
