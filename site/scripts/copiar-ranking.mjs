// Copia ranking-presidente.json para public/dados/, de onde o navegador o lê (filtros do ranking).
import { copyFileSync, existsSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

const origem = resolve(process.env.QMA_DADOS ?? resolve(process.cwd(), '..', 'dados/eleicoes-2026'), 'ranking-presidente.json');
if (!existsSync(origem)) {
  console.error(`ranking-presidente.json não encontrado em ${origem}`);
  process.exit(1);
}
const destino = resolve(process.cwd(), 'public/dados');
mkdirSync(destino, { recursive: true });
copyFileSync(origem, resolve(destino, 'ranking-presidente.json'));
