// Um cartão PNG 1200x630 por página: home, panorama, presidente, 27 governadores e 5.571 municípios.
import type { APIRoute } from 'astro';
import { UFS, lerComparacao, lerMunicipiosUF } from '../../lib/dados';
import { carregarOrdemNacional } from '../../lib/ordemPartidos';
import { corHex } from '../../lib/cores';
import { cartaoPNG, type BarraCartao } from '../../lib/cartao';
import { fraseDestaque } from '../../lib/frase';
import { nomeProprio, nomeUF } from '../../lib/formato';
import type { LinhaPartido } from '../../lib/tipos';

type Props = { titulo: string; frase: string; partidos: LinhaPartido[] };

/** Os 3 partidos mais votados em 2026, com a cor da ordem nacional (tema claro). */
function barras(partidos: LinhaPartido[]): BarraCartao[] {
  return partidos
    .filter((l) => l.pct_2026 !== null)
    .sort((a, b) => (b.pct_2026 as number) - (a.pct_2026 as number))
    .slice(0, 3)
    .map((l) => ({ partido: l.partido, cor: corHex(l.partido, 'claro'), pct2026: l.pct_2026, pct2022: l.pct_2022 }));
}

export function getStaticPaths() {
  carregarOrdemNacional();
  const br = lerComparacao('br', 'presidente').partidos;
  const rotas: { params: { rota: string }; props: Props }[] = [
    { params: { rota: 'home' }, props: { titulo: 'Quem manda aqui', frase: 'Digite sua cidade e veja em quem ela votou em 2026, e o que mudou desde 2022.', partidos: br } },
    { params: { rota: 'panorama' }, props: { titulo: 'Eleições 2026', frase: 'O 1º turno para presidente e governador, comparado com 2022, sempre por partido.', partidos: br } },
    { params: { rota: 'presidente' }, props: { titulo: 'Quem manda no Brasil', frase: 'Presidente, 1º turno de 2026, comparado com 2022.', partidos: br } },
  ];
  for (const uf of UFS) {
    const c = lerComparacao(uf, 'governador');
    rotas.push({
      params: { rota: `governador/${uf.toLowerCase()}` },
      props: { titulo: `Quem manda aqui em ${nomeUF(c.nome ?? uf)}`, frase: 'Governador, 1º turno de 2026, comparado com 2022.', partidos: c.partidos },
    });
    for (const m of lerMunicipiosUF(uf)) {
      rotas.push({
        params: { rota: `municipio/${uf.toLowerCase()}/${m.slug}` },
        props: { titulo: `Quem manda aqui em ${nomeProprio(m.nome)}/${uf}`, frase: fraseDestaque(m), partidos: m.presidente.partidos },
      });
    }
  }
  return rotas;
}

export const GET: APIRoute = async ({ props }) => {
  carregarOrdemNacional();
  const { titulo, frase, partidos } = props as Props;
  const png = await cartaoPNG(titulo, frase, barras([...partidos]));
  return new Response(png as BodyInit, { headers: { 'Content-Type': 'image/png' } });
};
