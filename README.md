# Quem Manda Aqui

Site estático com dados abertos da política brasileira, no qual qualquer pessoa descobre quem manda na sua cidade, com dados oficiais, fonte e data de coleta em cada página. O projeto tem um pipeline de dados em Python (pandas, httpx) e um site em Astro.

> O ser humano é um animal político. Aqui, você descobre quem manda — com dados.

## Comandos

Requisitos: Node.js LTS e uv (`winget install --id OpenJS.NodeJS.LTS -e` e `winget install --id astral-sh.uv -e`).

```bash
uv sync                        # instala as dependências Python
uv run pytest                  # testes Python (exclui os marcados com "rede")
uv run pytest -m rede          # testes que acessam a internet
npm --prefix site install      # instala as dependências do site
npm --prefix site run build    # gera o site estático em site/dist
npm --prefix site test         # testes do site (Vitest)
```

Se o `uv` falhar com "invalid peer certificate", defina `UV_NATIVE_TLS=1`.
