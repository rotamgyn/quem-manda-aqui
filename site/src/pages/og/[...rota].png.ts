// Um cartão PNG 1200x630 por página: home, panorama, presidente, 27 governadores e 5.571 municípios.
import type { APIRoute } from 'astro';
import { UFS, lerComparacao, lerMunicipiosUF } from '../../lib/dados';
import { cartaoPNG, escolherBarras } from '../../lib/cartao';
import { fraseDestaque } from '../../lib/frase';
import { nomeProprio, nomeUF } from '../../lib/formato';
import type { LinhaPartido } from '../../lib/tipos';

type Props = { titulo: string; frase: string; partidos: LinhaPartido[]; sem2022: boolean };

export function getStaticPaths() {
  const br = lerComparacao('br', 'presidente').partidos;
  const rotas: { params: { rota: string }; props: Props }[] = [
    { params: { rota: 'home' }, props: { titulo: 'Quem manda aqui', frase: 'Digite sua cidade e veja em quem ela votou em 2026, e o que mudou desde 2022.', partidos: br, sem2022: false } },
    { params: { rota: 'panorama' }, props: { titulo: 'Eleições 2026', frase: 'O 1º turno para presidente e governador, comparado com 2022, sempre por partido.', partidos: br, sem2022: false } },
    { params: { rota: 'presidente' }, props: { titulo: 'Quem manda no Brasil', frase: 'Presidente, 1º turno de 2026, comparado com 2022.', partidos: br, sem2022: false } },
  ];
  for (const uf of UFS) {
    const c = lerComparacao(uf, 'governador');
    rotas.push({
      params: { rota: `governador/${uf.toLowerCase()}` },
      props: { titulo: `Quem manda aqui em ${nomeUF(c.nome ?? uf)}`, frase: 'Governador, 1º turno de 2026, comparado com 2022.', partidos: c.partidos, sem2022: false },
    });
    for (const m of lerMunicipiosUF(uf)) {
      rotas.push({
        params: { rota: `municipio/${uf.toLowerCase()}/${m.slug}` },
        props: { titulo: `Quem manda aqui em ${nomeProprio(m.nome)}/${uf}`, frase: fraseDestaque(m), partidos: m.presidente.partidos, sem2022: !m.presidente.r2022 },
      });
    }
  }
  return rotas;
}

export const GET: APIRoute = async ({ props }) => {
  const { titulo, frase, partidos, sem2022 } = props as Props;
  const png = await cartaoPNG(titulo, frase, escolherBarras([...partidos]), sem2022);
  return new Response(png as BodyInit, { headers: { 'Content-Type': 'image/png' } });
};
