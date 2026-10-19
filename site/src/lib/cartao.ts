// Cartão de compartilhamento 1200x630 (WhatsApp/redes). Somente servidor/build.
// Sempre em fundo claro, por isso usa os hex do tema claro (satori não lê variáveis CSS).
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';
import { coresPorPosicao, ordemPorPosicao, PALETA_CLARA } from './cores';
import { pct } from './formato';
import type { LinhaPartido } from './tipos';

export type BarraCartao = { partido: string; cor: string; pct2026: number | null; pct2022: number | null };

const LARGURA = 1200;
const ALTURA = 630;
const TRILHA = 520;
const TINTA = '#121417';
const TINTA_2 = '#4a5059';
const TINTA_3 = '#636973';
const LINHA = '#d5d9df';

/**
 * Os 3 partidos mais votados em 2026 (empate: maior % em 2022), com as 3 primeiras cores claras da
 * paleta por posição DENTRO do cartão (Ruling 15): o 1º do cartão nunca fica cinza.
 */
export function escolherBarras(partidos: LinhaPartido[]): BarraCartao[] {
  const comVoto = partidos.filter((l) => l.pct_2026 !== null);
  const topo = ordemPorPosicao(comVoto).slice(0, 3);
  const cores = coresPorPosicao(comVoto.filter((l) => topo.includes(l.partido)), 'claro');
  return topo.map((p) => {
    const l = comVoto.find((x) => x.partido === p)!;
    return { partido: p, cor: cores[p.trim().toUpperCase()] ?? PALETA_CLARA[0], pct2026: l.pct_2026, pct2022: l.pct_2022 };
  });
}

/** Texto sob as barras de 2022: município sem resultado em 2022 x partido que não disputou. */
export const rotulo2022 = (pct2022: number | null, sem2022: boolean): string =>
  sem2022 ? 'Sem dados de 2022' : pct2022 === null ? 'Não disputou em 2022' : `2022: ${pct(pct2022)}`;

export const legenda = (sem2022: boolean): string =>
  sem2022 ? 'Barra cheia: 2026. Fonte: TSE' : 'Barra cheia: 2026. Listrada: 2022. Fonte: TSE';

/** Caminho público do cartão de uma rota (ex.: 'municipio/go/anapolis'). */
export const urlOg = (rota: string): string => `/og/${rota}.png`;

type Fonte = { name: string; data: Buffer; weight: 400 | 700 | 900; style: 'normal' };
let fontes: Fonte[] | null = null;
function carregarFontes(): Fonte[] {
  if (fontes) return fontes;
  // Ao lado do código-fonte (testes, dev); no build o módulo vai para um chunk em dist/, então cai no cwd (site/).
  const ao_lado = fileURLToPath(new URL('../assets/fontes/', import.meta.url));
  const pasta = existsSync(ao_lado) ? ao_lado : resolve(process.cwd(), 'src/assets/fontes');
  const ler = (n: string) => readFileSync(resolve(pasta, n));
  fontes = [
    { name: 'Archivo', data: ler('ArchivoExpanded-Black.ttf'), weight: 900, style: 'normal' },
    { name: 'Atkinson', data: ler('AtkinsonHyperlegible-Regular.ttf'), weight: 400, style: 'normal' },
    { name: 'Atkinson', data: ler('AtkinsonHyperlegible-Bold.ttf'), weight: 700, style: 'normal' },
  ];
  return fontes;
}

type No = { type: string; props: Record<string, unknown> };
const el = (type: string, style: Record<string, unknown>, children?: unknown, extra: Record<string, unknown> = {}): No => ({
  type,
  props: { ...extra, style, children },
});
const caixa = (style: Record<string, unknown>, children?: unknown) => el('div', { display: 'flex', ...style }, children);

// Marcador de mapa com interrogação (mesmo desenho do símbolo da marca).
const simboloQ = (cor: string, altura: number): No => {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 64"><path d="M9 19.5A11 11 0 1 1 26.3 28.5C21.8 31.6 20 34 20 38.5V42" fill="none" stroke="${cor}" stroke-width="12"/>` +
    `<path d="M20 63.5C18.4 60.8 12.6 56.4 12.6 51.2a7.4 7.4 0 0 1 14.8 0c0 5.2-5.8 9.6-7.4 12.3Zm0-9.6a2.7 2.7 0 1 0 0-5.4 2.7 2.7 0 0 0 0 5.4Z" fill="${cor}" fill-rule="evenodd"/></svg>`;
  const largura = Math.round((altura * 40) / 64);
  return el('img', { width: largura, height: altura }, undefined, {
    src: `data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`,
    width: largura,
    height: altura,
  });
};

const texto = (style: Record<string, unknown>, children: string) => el('div', { display: 'flex', ...style }, children);

function barra(b: BarraCartao, maximo: number, sem2022: boolean): No {
  const largura = (v: number) => Math.max(Math.round((v / maximo) * TRILHA), 6);
  const faixa = (v: number | null, listrada: boolean) =>
    caixa(
      { width: TRILHA, height: 26, marginTop: 6, background: '#eef0f3', borderRadius: 4 },
      v === null
        ? undefined
        : caixa(
            listrada
              ? {
                  width: largura(v),
                  height: 26,
                  borderRadius: 4,
                  border: `2px solid ${b.cor}`,
                  backgroundImage: `repeating-linear-gradient(135deg, ${b.cor} 0px, ${b.cor} 3px, #ffffff 3px, #ffffff 8px)`,
                }
              : { width: largura(v), height: 26, borderRadius: 4, background: b.cor },
          ),
    );
  return caixa({ flexDirection: 'column', marginBottom: 24 }, [
    caixa({ justifyContent: 'space-between', alignItems: 'baseline', width: TRILHA }, [
      texto({ fontFamily: 'Atkinson', fontWeight: 700, fontSize: 32, color: TINTA }, b.partido),
      texto({ fontFamily: 'Atkinson', fontWeight: 700, fontSize: 32, color: TINTA }, b.pct2026 === null ? '—' : pct(b.pct2026)),
    ]),
    faixa(b.pct2026, false),
    ...(sem2022 ? [] : [faixa(b.pct2022, true)]),
    texto(
      { fontFamily: 'Atkinson', fontWeight: 400, fontSize: 20, color: TINTA_3, marginTop: 4 },
      rotulo2022(b.pct2022, sem2022),
    ),
  ]);
}

/** Árvore do cartão; título e subtítulo encolhem conforme o comprimento. */
export function arvore(titulo: string, frase: string, barras: BarraCartao[], sem2022 = false): No {
  const tam = titulo.length > 44 ? 34 : titulo.length > 34 ? 40 : titulo.length > 24 ? 46 : 54;
  const tamFrase = frase.length > 90 ? 26 : 30;
  const palavras = titulo.split(' ').filter(Boolean);
  const maximo = Math.max(1, ...barras.flatMap((b) => [b.pct2026 ?? 0, b.pct2022 ?? 0]));
  const esquerda = caixa({ flexDirection: 'column', width: 500, justifyContent: 'space-between' }, [
    caixa({ flexDirection: 'column' }, [
      caixa({ flexDirection: 'row', flexWrap: 'wrap', alignItems: 'flex-end' }, [
        ...palavras.slice(0, -1).map((w) => texto({ fontFamily: 'Archivo', fontWeight: 900, fontSize: tam, lineHeight: 1.15, color: TINTA, marginRight: Math.round(tam * 0.3) }, w)),
        caixa({ alignItems: 'flex-end' }, [
          texto({ fontFamily: 'Archivo', fontWeight: 900, fontSize: tam, lineHeight: 1.15, color: TINTA, marginRight: 10 }, palavras[palavras.length - 1] ?? ''),
          simboloQ(TINTA, Math.round(tam * 0.95)),
        ]),
      ]),
      texto(
        { fontFamily: 'Atkinson', fontWeight: 400, fontSize: tamFrase, lineHeight: 1.3, color: TINTA_2, marginTop: 24, maxHeight: 170, overflow: 'hidden' },
        frase,
      ),
    ]),
    caixa({ alignItems: 'center' }, [
      texto({ fontFamily: 'Archivo', fontWeight: 900, fontSize: 26, color: TINTA, marginRight: 8 }, 'Quem manda aqui'),
      simboloQ(TINTA, 30),
    ]),
  ]);
  const direita = caixa({ flexDirection: 'column', width: TRILHA, justifyContent: 'space-between' }, [
    caixa({ flexDirection: 'column' }, barras.map((b) => barra(b, maximo, sem2022))),
    caixa({ flexDirection: 'column' }, [
      texto({ fontFamily: 'Atkinson', fontWeight: 400, fontSize: 20, color: TINTA_3 }, legenda(sem2022)),
      texto({ fontFamily: 'Atkinson', fontWeight: 700, fontSize: 26, color: TINTA, marginTop: 8 }, 'quemmandaaqui.com.br'),
    ]),
  ]);
  return caixa(
    { width: LARGURA, height: ALTURA, boxSizing: 'border-box', background: '#ffffff', padding: '50px 60px', justifyContent: 'space-between', borderTop: `10px solid ${TINTA}`, borderBottom: `1px solid ${LINHA}` },
    [esquerda, direita],
  );
}

/** PNG 1200x630. `barras`: até 3 partidos (quem chama escolhe e define a cor). */
export async function cartaoPNG(titulo: string, frase: string, barras: BarraCartao[] = [], sem2022 = false): Promise<Uint8Array> {
  const svg = await satori(arvore(titulo, frase, barras.slice(0, 3), sem2022) as never, {
    width: LARGURA,
    height: ALTURA,
    fonts: carregarFontes(),
  });
  return new Resvg(svg, { fitTo: { mode: 'width', value: LARGURA }, font: { loadSystemFonts: false } }).render().asPng();
}
