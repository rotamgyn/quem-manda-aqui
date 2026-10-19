// Gera public/busca-municipios.json: [{n: nome, uf, u: url}] dos 5.571 municípios (sem o exterior, ZZ).
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { nomeProprio } from '../src/lib/formato.ts';

const pasta = process.env.QMA_DADOS ?? resolve(process.cwd(), '..', 'dados/eleicoes-2026');
const UFS = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO'];

const indice = [];
for (const uf of UFS) {
  const { municipios } = JSON.parse(readFileSync(resolve(pasta, 'municipios', `${uf.toLowerCase()}.json`), 'utf-8'));
  for (const m of municipios) {
    indice.push({ n: nomeProprio(m.nome), uf, u: `/eleicoes-2026/municipio/${uf.toLowerCase()}/${m.slug}/` });
  }
}
indice.sort((a, b) => a.n.localeCompare(b.n, 'pt-BR') || a.uf.localeCompare(b.uf));
mkdirSync(resolve(process.cwd(), 'public'), { recursive: true });
writeFileSync(resolve(process.cwd(), 'public/busca-municipios.json'), JSON.stringify(indice));
console.log(`busca-municipios.json: ${indice.length} municípios`);
