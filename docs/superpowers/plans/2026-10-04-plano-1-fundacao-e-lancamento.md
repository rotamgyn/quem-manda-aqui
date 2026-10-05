# Plano 1 — Fundação e lançamento (Quem Manda Aqui + Eleições 2026, 1º turno × 2022)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Colocar no ar, até 12/10/2026, o site quemmandaaqui.com.br com os resultados do 1º turno de 2026 comparados a 2022 (presidente e governador), por Brasil, UF e município.

**Architecture:** Um pipeline Python baixa os dados do TSE (2026 ao vivo, já consolidados; 2022 do Dados Abertos) e as malhas do IBGE, normaliza tudo num modelo único, compara 2022 × 2026, confere os totais com os oficiais e grava JSONs em `dados/`, versionados no repositório. Um site Astro lê esses JSONs no build e gera páginas estáticas (incluindo 5.571 páginas de município, mapas SVG e cartões de compartilhamento), publicadas na Cloudflare Pages por GitHub Actions. O robô ao vivo e a projeção ficam para o Plano 2; as análises D, E e C ficam para o Plano 3.

**Tech Stack:** Python 3.12 (uv, pandas, httpx, pytest), Node 22 LTS, Astro 5 + TypeScript, d3-geo + topojson-client (mapas renderizados no build), satori + @resvg/resvg-js (cartões OG), Vitest, Cloudflare Pages, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-04-quem-manda-aqui-plataforma-e-eleicoes-2026-design.md`

**Planos seguintes:** Plano 2 (robô ao vivo + projeção + backtest, até 22/10) e Plano 3 (análises D, E, C) serão escritos após este, sobre os contratos de dados fixados aqui.

## Global Constraints

- Idioma de todo texto do site, da documentação e das mensagens de commit: **português do Brasil**.
- Neutralidade: comparações **por partido/federação do candidato**, nunca por rótulos ideológicos ("esquerda", "direita") em código, dados ou texto.
- Cores: paleta categórica própria; **proibido** usar cores de partidos ou verde-amarelo.
- Ética com as fontes: no máximo **4 requisições/segundo** ao TSE e ao IBGE, com cache em disco (nunca baixar de novo o que já está em cache).
- Toda página com dado mostra fonte e data/hora da coleta.
- Nenhum número publicado pode divergir dos totais oficiais do TSE: divergência **bloqueia** a geração de dados (§7 da spec).
- Sem login, sem cookies, sem coleta de dados pessoais; métricas via **Cloudflare Web Analytics**.
- Manifesto em `/sobre`, texto exato: *"O ser humano é um animal político. Aqui, você descobre quem manda — com dados."*
- Celular primeiro; modo claro/escuro; toda mapa tem tabela alternativa.
- Códigos de eleição 2026, 1º turno: presidente **6257** (cargo 1), governador **6259** (cargo 3). 2022: 1º turno **544**, 2º turno **545** (federal); cargo governador = 3.
- Arquivos 2026 em UTF-8; CSVs 2022 em Latin-1 com separador `;`.
- Universo: 5.571 municípios (incluindo Brasília) + 186 cidades do exterior (UF `ZZ`), estas só nos totais de presidente.
- Sistema operacional de desenvolvimento: Windows 11; comandos devem funcionar no Git Bash.

## Review Focus

1. **Município sem dado de 2022** (ex.: municípios instalados após 2022, como Boa Esperança do Norte/MT): a comparação deve dizer "sem dados de 2022", nunca mostrar 0% nem quebrar o build. → teste `test_comparacao_sem_2022` (Tarefa 7).
2. **Partido presente em só um dos anos** (partidos novos em 2026; partidos incorporados após 2022): aparece com o lado ausente `null`, entra na volatilidade, e as incorporações da tabela de equivalências são aplicadas. → `test_partido_so_em_2026` e `test_equivalencia_aplicada` (Tarefa 7).
3. **Apuração incompleta ou zero votos válidos** num município: nenhum percentual por divisão por zero; `apuracao_completa=false` e aviso na página. → `test_validos_zero` (Tarefa 7) e `test_pct_secoes_parcial` (Tarefa 4).
4. **Nomes com acento, apóstrofo e homônimos** (ex.: "SÃO JOÃO D'ALIANÇA"; mesmo nome em UFs diferentes): slug estável e único dentro da UF. → `test_slug_*` (Tarefa 3).
5. **Governador que vai ao 2º turno**: o 1º colocado não pode aparecer como "eleito". → `test_situacao_segundo_turno` (Tarefa 4).

---

## Ações do dono do projeto (em paralelo, começar já)

O dono não é técnico; o executor fornece o passo a passo em português simples quando cada item for necessário.

- [ ] **D1 (até 06/10):** criar conta no GitHub e informar o nome de usuário.
- [ ] **D2 (até 06/10):** criar conta na Cloudflare, adicionar o site `quemmandaaqui.com.br` (plano Free) e copiar os 2 *nameservers* indicados.
- [ ] **D3 (até 06/10, logo após D2):** no Registro.br, trocar os servidores DNS do domínio pelos *nameservers* da Cloudflare. **A propagação pode levar até 24 h — por isso é a primeira coisa a fazer.**
- [ ] **D4 (Tarefa 10):** aprovar a identidade visual.
- [ ] **D5 (Tarefa 14):** criar um token de API da Cloudflare (modelo "Cloudflare Pages — Edit") e o *Account ID*, e cadastrá-los como *secrets* no repositório GitHub (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`).

---

## Estrutura de arquivos

```
D:\politicaBrasil\
  pyproject.toml                       projeto Python único (uv); pacotes qma_comum e qma_eleicoes
  .python-version                      3.12
  .gitignore                           .cache/, node_modules/, site/dist/, .venv/
  .cache/                              downloads brutos (não versionado)
  dados/                               SAÍDA do pipeline (versionada; lida pelo site)
    comum/municipios.json
    comum/malhas/br-uf.json, comum/malhas/{uf}.json
    eleicoes-2026/comparacoes/{abr}-{cargo}.json
    eleicoes-2026/municipios/{uf}.json
    eleicoes-2026/ranking-presidente.json
    eleicoes-2026/meta.json
  dados-comuns/
    partidos-equivalencias.csv         sigla_origem,sigla_destino,nota
    src/qma_comum/http.py              download com cache + limite de taxa
    src/qma_comum/municipios.py        tabela TSE↔IBGE + slug
    src/qma_comum/malhas.py            malhas IBGE
    testes/
  modulos/eleicoes-2026/
    pipeline/src/qma_eleicoes/
      config.py                        URLs, códigos de eleição, cargos
      modelo.py                        dataclasses Resultado, VotoCandidato, Comparacao
      leitor_2026.py                   JSON ao vivo TSE → Resultado
      leitor_2022.py                   CSV Dados Abertos → Resultado
      coleta_2026.py                   baixa todos os arquivos 2026 necessários
      comparacao.py                    2022 × 2026
      conferencia.py                   totais × oficiais
      exportar.py                      grava dados/eleicoes-2026/*
      __main__.py                      CLI: python -m qma_eleicoes gerar
    pipeline/testes/ (+ amostras/)
    paginas/                           (vazio no Plano 1; páginas ficam em site/src/pages/eleicoes-2026)
  site/                                Astro
    src/lib/tipos.ts, dados.ts, cores.ts, formato.ts, slug.ts
    src/components/ (Layout, Cabecalho, Rodape, TabelaComparativa, BarrasVariacao, Mapa, BuscaMunicipio, Fonte)
    src/pages/ (index, sobre, metodologia, fontes, eleicoes-2026/...)
    src/pages/og/[...rota].png.ts      cartões de compartilhamento
  .github/workflows/deploy.yml, atualizar-dados.yml
```

---

### Task 1: Ambiente e esqueleto do repositório

**Files:**
- Create: `pyproject.toml`, `.python-version`, `.gitignore`, `README.md`, `dados-comuns/src/qma_comum/__init__.py`, `modulos/eleicoes-2026/pipeline/src/qma_eleicoes/__init__.py`, `dados-comuns/testes/test_fumaca.py`
- Create: `site/` (via `npm create astro@latest`)

**Interfaces:**
- Produces: comandos `uv run pytest` (raiz) e `npm --prefix site run build`, `npm --prefix site test` (Vitest).

- [ ] **Step 1:** Instalar ferramentas: `winget install --id OpenJS.NodeJS.LTS -e` e `winget install --id astral-sh.uv -e`; reabrir o shell. Verificar: `node --version` → `v22.x`; `uv --version` → imprime versão.
- [ ] **Step 2:** Criar `pyproject.toml` (nome `quem-manda-aqui`, `requires-python = ">=3.12"`, dependências `pandas`, `httpx`; dev: `pytest`), build hatchling com `packages = ["dados-comuns/src/qma_comum", "modulos/eleicoes-2026/pipeline/src/qma_eleicoes"]`, `[tool.pytest.ini_options] testpaths = ["dados-comuns/testes", "modulos/eleicoes-2026/pipeline/testes"]` e marcador `rede` (testes que acessam a internet). `.python-version` = `3.12`.
- [ ] **Step 3:** Teste de fumaça `test_importa_pacotes`: `import qma_comum, qma_eleicoes`. Rodar `uv sync && uv run pytest` → 1 passed.
- [ ] **Step 4:** `npm create astro@latest site -- --template minimal --typescript strict --no-git --install`; adicionar Vitest (`npm --prefix site i -D vitest`) e script `"test": "vitest run"`. Rodar `npm --prefix site run build` → sucesso.
- [ ] **Step 5:** `.gitignore` com `.cache/`, `.venv/`, `node_modules/`, `site/dist/`, `site/.astro/`. README com 1 parágrafo do projeto e os comandos acima.
- [ ] **Step 6:** Commit `chore: esqueleto do repositório (Python + Astro)`.

---

### Task 2: Download com cache e limite de taxa

**Files:**
- Create: `dados-comuns/src/qma_comum/http.py`
- Test: `dados-comuns/testes/test_http.py`

**Interfaces:**
- Produces: `baixar(url: str, *, cache_dir: Path = Path(".cache"), max_por_segundo: float = 4.0, forcar: bool = False) -> Path` — devolve o caminho local do arquivo em cache; caminho derivado da URL (host + path, seguro para Windows). `baixar_json(url, **kw) -> Any` (lê UTF-8). Erro HTTP ≠ 200 → `ErroDownload(url, status)`. Retentativa: 3 tentativas com espera exponencial (1 s, 2 s, 4 s) para erros de rede e 5xx; 404 não tenta de novo.

- [ ] **Step 1:** Testes com `httpx.MockTransport` (injetado via parâmetro privado `_cliente`): `test_usa_cache_na_segunda_chamada` (transport chamado 1 vez para 2 chamadas), `test_forcar_baixa_de_novo` (2 vezes), `test_404_levanta_erro_sem_retentar` (1 chamada, `ErroDownload.status == 404`), `test_5xx_retenta_3_vezes`, `test_respeita_limite_de_taxa` (5 URLs com `max_por_segundo=10` levam ≥ 0,4 s; usar relógio injetável para não esperar de verdade).
- [ ] **Step 2:** Rodar `uv run pytest dados-comuns/testes/test_http.py -v` → FAIL (módulo inexistente).
- [ ] **Step 3:** Implementar. Gravação atômica (arquivo `.parcial` renomeado ao final) para downloads grandes (os zips de 2022 têm ~640 MB), em *streaming*.
- [ ] **Step 4:** Rodar os testes → PASS.
- [ ] **Step 5:** Commit `feat: download com cache e limite de taxa`.

---

### Task 3: Tabela de municípios TSE↔IBGE e slugs

**Files:**
- Create: `dados-comuns/src/qma_comum/municipios.py`
- Test: `dados-comuns/testes/test_municipios.py`, amostra `dados-comuns/testes/amostras/mun-cm-recorte.json` (recorte real com AC, DF, GO incluindo Goiânia `93734`, e 2 cidades `zz`)

**Interfaces:**
- Consumes: `baixar_json` (Tarefa 2).
- Produces:
  - `@dataclass(frozen=True) Municipio: tse: str (5 dígitos), ibge: str | None (7 dígitos; None no exterior), nome: str, uf: str (maiúsculas, "ZZ" no exterior), capital: bool, slug: str`
  - `ler_config_municipios(dados: dict) -> list[Municipio]` — lê o formato `abr[].mu[]` de `config/mun-e006257-cm.json` (`cd`, `cdi`, `nm`, `c == "s"` → capital).
  - `slugificar(nome: str) -> str` e `atribuir_slugs(municipios) -> list[Municipio]` (desempate dentro da UF com sufixo `-{tse}`).
  - `gravar_municipios(municipios, destino=Path("dados/comum/municipios.json"))` — JSON lista de objetos com os mesmos campos.
  - `validar_universo(municipios)` → `ErroUniverso` se nº de municípios com UF ≠ ZZ for diferente de **5571**, se algum deles não tiver IBGE, ou se houver IBGE duplicado.

- [ ] **Step 1:** Testes: `test_le_goiania` (`tse="93734"`, `ibge="5208707"`, `uf="GO"`, `capital=True`); `test_exterior_sem_ibge` (`uf="ZZ"`, `ibge is None`); `test_slug_acentos_e_apostrofo` (`slugificar("SÃO JOÃO D'ALIANÇA") == "sao-joao-dalianca"`); `test_slug_espacos_e_hifens` (`slugificar("ITAPAJÉ DO  OESTE-NOVO") == "itapaje-do-oeste-novo"`); `test_slug_homonimo_na_mesma_uf` (dois municípios fictícios mesmo nome/UF → segundo recebe `-{tse}`); `test_validar_universo_falha_com_faltante`.
- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** Implementar. Slug: minúsculas, remover acentos (NFKD), remover apóstrofos, demais não alfanuméricos → `-`, colapsar e aparar `-`.
- [ ] **Step 4:** Rodar → PASS. Teste marcado `@pytest.mark.rede` `test_universo_real` baixa o arquivo real (`https://resultados.tse.jus.br/oficial/ele2026/6257/config/mun-e006257-cm.json`) e chama `validar_universo` → PASS (`uv run pytest -m rede -k universo`).
- [ ] **Step 5:** Commit `feat: tabela de municípios TSE↔IBGE com slugs`.

---

### Task 4: Modelo de dados e leitor do formato 2026

**Files:**
- Create: `modulos/eleicoes-2026/pipeline/src/qma_eleicoes/config.py`, `modelo.py`, `leitor_2026.py`
- Test: `modulos/eleicoes-2026/pipeline/testes/test_leitor_2026.py`; amostras reais salvas de `.../ele2026/6257/dados/br/br-c0001-e006257-u.json`, `.../go/go93734-c0001-e006257-u.json`, `.../go/go-c0003-e006259-u.json` em `testes/amostras/`

**Interfaces:**
- Produces (`config.py`): `BASE_2026 = "https://resultados.tse.jus.br/oficial/ele2026"`; `ELEICAO_2026_T1 = {"presidente": "6257", "governador": "6259"}`; `CODIGO_CARGO = {"presidente": 1, "governador": 3}`; `url_resultado_2026(cargo: Cargo, uf: str, municipio_tse: str | None = None) -> str` montando `{BASE}/{ele}/dados/{uf}/{uf}[{mun}]-c{cargo:04d}-e{ele:06d}-u.json` (`uf="br"` para nacional; minúsculas).
- Produces (`modelo.py`):
  - `Cargo = Literal["presidente", "governador"]`
  - `@dataclass(frozen=True) VotoCandidato: numero: int, nome_urna: str, partido: str, votos: int, situacao: Literal["eleito", "2º turno", "não eleito", ""]`
  - `@dataclass(frozen=True) Resultado: ano: int, turno: int, cargo: Cargo, uf: str ("BR" ou sigla maiúscula), municipio_tse: str | None, aptos: int, comparecimento: int, abstencao: int, brancos: int, nulos: int, validos: int, pct_secoes_totalizadas: float, candidatos: tuple[VotoCandidato, ...]` (candidatos ordenados por votos desc.)
  - `Resultado.pct(candidato) -> float | None` = votos/validos×100; `None` se `validos == 0`.
- Produces (`leitor_2026.py`): `ler_resultado_2026(dados: dict, cargo: Cargo) -> Resultado`.

Mapeamento do JSON 2026 (pinado pela verificação de 04/10/2026): `tpabr`/`cdabr` → uf/municipio (`tpabr == "br"` → `uf="BR"`; `"uf"` → `cdabr.upper()`; `"mu"` → municipio_tse = `cdabr`, uf vem do parâmetro de contexto lido do caminho — por isso a assinatura recebe também `uf: str | None = None`); `e.te` → aptos; `e.c` → comparecimento; `e.a` → abstencao; `v.vb` → brancos; `v.tvn` → nulos; `v.vv` → validos; `s.pstn` (vírgula decimal) → pct_secoes_totalizadas; candidatos em `carg[0].agr[].par[].cand[]`: `n`, `nmu`, `par.sg`, `vap`; situação: `cand.e == "s"` → `"eleito"`; `cand.st` contendo `"2º turno"` (sem diferenciar maiúsculas) → `"2º turno"`; `st` contendo `"não eleito"` → `"não eleito"`; senão `""`. `ano=2026`, `turno = int(dados["t"])`.

- [ ] **Step 1:** Testes: `test_brasil_presidente` (amostra BR: `uf == "BR"`, `aptos == 158745502`, primeiro candidato `partido == "PL"`, `votos == 56082216`); `test_municipio_goiania` (`municipio_tse == "93734"`, `uf == "GO"`); `test_soma_candidatos_igual_validos`; `test_pct_secoes_parcial` (amostra BR: `pct_secoes_totalizadas == pytest.approx(99.908061725)`; `Resultado.pct` com `validos=0` → `None`); `test_situacao_segundo_turno` (cópia da amostra de governador com `st` = `"2º turno"` e `e = "n"` no 1º colocado → `situacao == "2º turno"`, nunca `"eleito"`); `test_url_resultado_2026` (`url_resultado_2026("governador", "go", "93734")` termina em `/6259/dados/go/go93734-c0003-e006259-u.json`).
- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** Implementar `config.py`, `modelo.py`, `leitor_2026.py`.
- [ ] **Step 4:** Rodar → PASS.
- [ ] **Step 5:** Commit `feat: modelo de resultado e leitor do formato TSE 2026`.

---

### Task 5: Leitor dos CSVs de 2022

**Files:**
- Create: `modulos/eleicoes-2026/pipeline/src/qma_eleicoes/leitor_2022.py`
- Test: `testes/test_leitor_2022.py`; amostras `testes/amostras/votacao_2022_recorte.csv` e `detalhe_2022_recorte.csv` (≈30 linhas reais cada, com cabeçalho original, cobrindo 1 município em 2 zonas, linhas `ST_VOTO_EM_TRANSITO = "S"`, turnos 1 e 2, cargos 1 e 3, e uma linha de deputado que deve ser ignorada)

**Interfaces:**
- Consumes: `baixar` (Tarefa 2), `Resultado`, `VotoCandidato` (Tarefa 4).
- Produces: `ler_2022(votacao_csvs: Iterable[Path], detalhe_csvs: Iterable[Path], *, turno: int) -> list[Resultado]` — um `Resultado` por (cargo ∈ {1, 3}, UF, município), somando todas as zonas e linhas de trânsito; mais os agregados por UF e Brasil (presidente). `municipio_tse` = `CD_MUNICIPIO` com zeros à esquerda até 5 dígitos. `pct_secoes_totalizadas = 100.0`. Situação a partir de `DS_SIT_TOT_TURNO` (`"ELEITO"` → `"eleito"`, `"2º TURNO"` → `"2º turno"`, `"NÃO ELEITO"` → `"não eleito"`).
- Produces: `arquivos_2022() -> tuple[list[Path], list[Path]]` — baixa (via cache) `votacao_candidato_munzona_2022.zip` e `detalhe_votacao_munzona_2022.zip` de `https://cdn.tse.jus.br/estatistica/sead/odsele/...`, extrai para `.cache/2022/` e devolve os CSVs.

Colunas usadas (pinadas): votação — `NR_TURNO, SG_UF, CD_MUNICIPIO, CD_CARGO, NR_CANDIDATO, NM_URNA_CANDIDATO, SG_PARTIDO, QT_VOTOS_NOMINAIS_VALIDOS, DS_SIT_TOT_TURNO`; detalhe — `NR_TURNO, SG_UF, CD_MUNICIPIO, CD_CARGO, QT_APTOS, QT_COMPARECIMENTO, QT_ABSTENCOES, QT_VOTOS_BRANCOS, QT_TOTAL_VOTOS_NULOS, QT_TOTAL_VOTOS_VALIDOS`. Ler com `pandas.read_csv(sep=";", encoding="latin-1", usecols=..., dtype={"CD_MUNICIPIO": str})` e filtrar `CD_CARGO in (1, 3)` em blocos (`chunksize`) para não estourar memória. Para presidente, usar apenas o arquivo `_BR.csv` de votação (evita contar duas vezes); para governador, os arquivos por UF.

- [ ] **Step 1:** Testes com as amostras: `test_soma_zonas_e_transito` (total de votos do candidato no município = soma das linhas da amostra); `test_ignora_deputados`; `test_codigo_municipio_com_5_digitos`; `test_turno_filtrado`; `test_validos_do_detalhe`.
- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Rodar → PASS. Teste `@pytest.mark.rede` `test_totais_oficiais_2022` (dados completos): presidente 1º turno Brasil — LULA (13) = **57.259.504**, BOLSONARO (22) = **51.072.345**; 2º turno — LULA = **60.345.999**, BOLSONARO = **58.206.354**. Rodar `uv run pytest -m rede -k oficiais_2022` → PASS (primeiro download leva minutos).
- [ ] **Step 5:** Commit `feat: leitor dos dados abertos TSE 2022`.

---

### Task 6: Coleta dos resultados 2026 (1º turno)

**Files:**
- Create: `modulos/eleicoes-2026/pipeline/src/qma_eleicoes/coleta_2026.py`
- Test: `testes/test_coleta_2026.py`

**Interfaces:**
- Consumes: `baixar_json` (T2), `Municipio` (T3), `url_resultado_2026`, `ler_resultado_2026` (T4).
- Produces: `coletar_2026(municipios: list[Municipio], *, forcar: bool = False, _baixar=baixar_json) -> list[Resultado]` — para presidente: BR, cada UF (incluindo `zz`) e cada município (incluindo exterior); para governador: cada UF exceto `zz` e cada município exceto exterior. Arquivo inexistente (404) num município → registra aviso e segue; 404 em BR/UF → erro. Exibe progresso a cada 500 arquivos. Total esperado ≈ 11.400 arquivos (≈ 48 min na primeira vez a 4 req/s; depois, cache).

- [ ] **Step 1:** Testes com `_baixar` falso (dicionário URL → amostra): `test_presidente_inclui_exterior`, `test_governador_exclui_exterior`, `test_404_em_municipio_nao_interrompe`, `test_404_em_uf_interrompe`.
- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Rodar → PASS.
- [ ] **Step 5:** Commit `feat: coleta dos resultados 2026 com cache`.

---

### Task 7: Comparação 2022 × 2026

**Files:**
- Create: `modulos/eleicoes-2026/pipeline/src/qma_eleicoes/comparacao.py`, `dados-comuns/partidos-equivalencias.csv`
- Test: `testes/test_comparacao.py`

**Interfaces:**
- Consumes: `Resultado` (T4).
- Produces:
  - `carregar_equivalencias(caminho=Path("dados-comuns/partidos-equivalencias.csv")) -> dict[str, str]` (sigla 2022 → sigla atual). Conteúdo inicial: `PTB,PRD`, `PATRIOTA,PRD`, `PROS,SOLIDARIEDADE`, `PSC,PODE`, cada um com nota da incorporação/fusão. O executor confere as siglas contra a lista real de partidos dos dois anos e completa a tabela antes do commit (registrando a fonte na coluna `nota`).
  - `@dataclass(frozen=True) LinhaPartido: partido: str, pct_2022: float | None, pct_2026: float | None, delta_pp: float | None`
  - `@dataclass(frozen=True) Comparacao: cargo: Cargo, uf: str, municipio_tse: str | None, r2022: Resultado | None, r2026: Resultado | None, partidos: tuple[LinhaPartido, ...], volatilidade: float | None, vencedor_2022: str | None, vencedor_2026: str | None, virou: bool | None, apuracao_completa: bool`
  - `comparar(r2022: Resultado | None, r2026: Resultado | None, equivalencias: dict[str, str]) -> Comparacao`
- Regras: percentuais sobre votos válidos; siglas de 2022 passam pela tabela de equivalências; partido ausente num ano → `pct_*` = `None` mas conta como 0 na volatilidade; `delta_pp` só quando os dois lados existem; **volatilidade = índice de Pedersen** = ½ × Σ |pct_2026 − pct_2022| sobre todos os partidos (ausente = 0); `virou = vencedor_2022 != vencedor_2026` (None se faltar um lado); `apuracao_completa = r2026 is not None and r2026.pct_secoes_totalizadas >= 100`; `partidos` ordenado por `pct_2026` desc. (None por último).

- [ ] **Step 1:** Testes: `test_delta_simples` (PT 40→30, PL 60→70 → deltas −10/+10, volatilidade 10, `virou` False); `test_virada` (vencedor PT → PL → `virou` True); `test_partido_so_em_2026` (MISSÃO: `pct_2022 is None`, `delta_pp is None`, entra na volatilidade); `test_equivalencia_aplicada` (PTB 2022 aparece como PRD); `test_comparacao_sem_2022` (`r2022=None` → `volatilidade is None`, `virou is None`, sem exceção); `test_validos_zero` (r2026 com `validos=0` → pcts `None`, sem `ZeroDivisionError`); `test_apuracao_incompleta` (`pct_secoes_totalizadas=99.9` → `apuracao_completa` False).
- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Rodar → PASS.
- [ ] **Step 5:** Commit `feat: comparação 2022×2026 com volatilidade de Pedersen`.

---

### Task 8: Conferência de totais

**Files:**
- Create: `modulos/eleicoes-2026/pipeline/src/qma_eleicoes/conferencia.py`
- Test: `testes/test_conferencia.py`

**Interfaces:**
- Consumes: `Resultado` (T4).
- Produces: `conferir(resultados: list[Resultado]) -> None` — para cada (ano, turno, cargo, UF): a soma dos municípios (votos por candidato, aptos, comparecimento, brancos, nulos, válidos) deve ser **exatamente** igual ao `Resultado` agregado da UF; para presidente, a soma das UFs (incluindo ZZ) deve ser igual ao do Brasil. Qualquer diferença → `ErroConferencia` com a lista completa de divergências (`"2026 presidente GO candidato 22: municípios=1.234.567 oficial=1.234.570"`).

- [ ] **Step 1:** Testes: `test_totais_batem` (sem exceção); `test_divergencia_de_um_voto_bloqueia`; `test_mensagem_lista_todas_as_divergencias` (2 divergências → 2 linhas).
- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Rodar → PASS.
- [ ] **Step 5:** Commit `feat: conferência de totais bloqueante`.

---

### Task 9: Malhas, exportação JSON e CLI

**Files:**
- Create: `dados-comuns/src/qma_comum/malhas.py`, `modulos/eleicoes-2026/pipeline/src/qma_eleicoes/exportar.py`, `__main__.py`
- Test: `testes/test_exportar.py`, `dados-comuns/testes/test_malhas.py`

**Interfaces:**
- Consumes: tudo das Tarefas 2–8.
- Produces (`malhas.py`): `baixar_malhas(ufs: list[str], destino=Path("dados/comum/malhas"))` — TopoJSON do IBGE: Brasil por UF `https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/json&qualidade=minima&intrarregiao=UF` → `br-uf.json`; cada UF por município `.../api/v3/malhas/estados/{UF}?formato=application/json&qualidade=minima&intrarregiao=municipio` → `{uf}.json` (minúsculas). Propriedade `codarea` = código IBGE.
- Produces (`exportar.py`) — **contrato lido pelo site e pelos Planos 2 e 3**:
  - `comparacoes/{abr}-{cargo}.json` (`abr` = `br` ou UF minúscula; `br-governador` não existe): objeto `Comparacao` serializado (`dataclasses.asdict`; `candidatos` de cada `Resultado` ganham campo `pct`), mais `nome` da abrangência.
  - `municipios/{uf}.json`: `{"uf": "GO", "municipios": [{"tse", "ibge", "nome", "slug", "capital", "presidente": Comparacao, "governador": Comparacao}]}` — exterior vai em `municipios/zz.json` só com `presidente`.
  - `ranking-presidente.json`: 50 municípios (UF ≠ ZZ) com maior `volatilidade`: `[{"tse", "nome", "uf", "slug", "volatilidade", "vencedor_2022", "vencedor_2026", "virou"}]`.
  - `meta.json`: `{"gerado_em": ISO-8601 America/Sao_Paulo, "fonte_2026_dg_hg": "04/10/2026 22:30:15", "pct_secoes_br": 99.91}`.
  - JSON em UTF-8, `ensure_ascii=False`, números com no máximo 2 casas decimais nos percentuais.
- Produces (`__main__.py`): `uv run python -m qma_eleicoes gerar [--forcar]` executa: municípios → malhas → 2022 (turno 1) → 2026 → **conferir (2022 e 2026)** → comparar → exportar. Falha de conferência termina com código 1 e não escreve nada em `dados/eleicoes-2026/` (gravar em pasta temporária e trocar no fim).

- [ ] **Step 1:** Testes: `test_formato_municipio_uf` (chaves exatas acima); `test_ranking_50_ordenado_sem_exterior`; `test_falha_de_conferencia_nao_altera_dados` (pasta de saída intacta após `ErroConferencia`); `test_malhas_nome_arquivos` (com `_baixar` falso).
- [ ] **Step 2:** Rodar → FAIL.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** Rodar → PASS. Rodar de verdade `uv run python -m qma_eleicoes gerar` → termina com código 0; `dados/eleicoes-2026/municipios/` tem 28 arquivos; `ranking-presidente.json` tem 50 itens.
- [ ] **Step 5:** Commit `feat: exportação de dados e CLI do pipeline` e, separado, `dados: 1º turno 2026 × 2022` (com a pasta `dados/`).

---

### Task 10: Identidade visual, layout e páginas institucionais

**Files:**
- Create: `site/src/styles/tokens.css`, `site/src/lib/cores.ts`, `site/src/components/Layout.astro`, `Cabecalho.astro`, `Rodape.astro`, `Fonte.astro`, `site/src/pages/index.astro`, `sobre.astro`, `metodologia.astro`, `fontes.astro`, `site/public/favicon.svg`
- Test: `site/src/lib/cores.test.ts`

**Interfaces:**
- Produces: `Layout` (props `titulo: string`, `descricao: string`, `imagemOg?: string`); `Fonte` (props `fonte: string`, `atualizadoEm: string`); `corDoPartido(partido: string): string` — cor atribuída pela ordem do partido no resultado nacional do 1º turno 2026 (presidente), depois governador, a partir de uma paleta categórica fixa de 8 cores; demais partidos → cinza neutro. Tokens CSS em `:root` com variantes escuras via `prefers-color-scheme` e `[data-theme]`.

- [ ] **Step 1:** Carregar as skills `frontend-design` e `dataviz` e produzir uma proposta de identidade (logo tipográfico "Quem Manda Aqui", tipografia, paleta categórica validada para daltonismo pelo validador da skill `dataviz`, **sem cores de partidos nem verde-amarelo**). Publicar a proposta como Artifact (página privada) com home de exemplo em claro/escuro.
- [ ] **Step 2:** **Portão D4:** apresentar ao dono e aguardar aprovação. Ajustar até aprovar.
- [ ] **Step 3:** Testes `cores.test.ts`: `test_mesma_cor_para_mesmo_partido`; `test_partido_desconhecido_cinza`; `test_paleta_sem_verde_amarelo` (nenhuma cor da paleta com matiz HSL entre 45° e 150° e saturação > 40%).
- [ ] **Step 4:** Rodar `npm --prefix site test` → FAIL; implementar; → PASS.
- [ ] **Step 5:** Páginas: home (destaque Eleições 2026, busca — componente da Tarefa 13, cartões "em breve" dos módulos: Monitor do Congresso, Gastos dos parlamentares, Rumo a 2028/2030, Dinheiro das campanhas, Governo eleito); `/sobre` com o manifesto exato (Global Constraints) e princípio de neutralidade; `/metodologia` (comparação por partido, volatilidade de Pedersen explicada em linguagem simples, tabela de equivalências lida de `dados-comuns/partidos-equivalencias.csv`, conferência de totais, limitações); `/fontes` (lista das URLs da spec §3 com data de coleta de `meta.json`). Script do Cloudflare Web Analytics no `Layout` (token via variável `PUBLIC_CF_ANALYTICS_TOKEN`; ausente → não inclui).
- [ ] **Step 6:** `npm --prefix site run build` → sucesso. Commit `feat: identidade visual, layout e páginas institucionais`.

---

### Task 11: Páginas de presidente, governador e panorama

**Files:**
- Create: `site/src/lib/tipos.ts`, `dados.ts`, `formato.ts`, `site/src/components/TabelaComparativa.astro`, `BarrasVariacao.astro`, `site/src/pages/eleicoes-2026/index.astro`, `presidente.astro`, `governador/[uf].astro`
- Test: `site/src/lib/dados.test.ts`, `formato.test.ts`

**Interfaces:**
- Consumes: JSONs da Tarefa 9 (lidos de `../dados` relativo a `site/`).
- Produces: `tipos.ts` espelhando exatamente o contrato da Tarefa 9 (`Comparacao`, `LinhaPartido`, `Resultado`, `VotoCandidato`, `MunicipioComparado`, `ItemRanking`, `Meta`); `dados.ts`: `lerComparacao(abr: string, cargo: Cargo): Comparacao`, `lerMunicipiosUF(uf: string): MunicipioComparado[]`, `lerRanking(): ItemRanking[]`, `lerMeta(): Meta`, `UFS: string[]` (27 siglas); `formato.ts`: `pct(n: number | null): string` (`"47,05%"`, `null` → `"—"`), `pp(n: number | null): string` (`"+11,5 p.p."`, `"−3,2 p.p."` com sinal de menos tipográfico), `inteiro(n)` (`"56.082.216"`).

- [ ] **Step 1:** Testes: `formato.test.ts` (`pct(47.0508) === "47,05%"`, `pct(null) === "—"`, `pp(-3.2) === "−3,2 p.p."`, `inteiro(56082216) === "56.082.216"`); `dados.test.ts` (`lerComparacao("br","presidente").partidos[0].partido` existe; `lerMunicipiosUF("go")` contém `tse === "93734"`).
- [ ] **Step 2:** Rodar → FAIL; implementar `tipos.ts`, `dados.ts`, `formato.ts`; → PASS.
- [ ] **Step 3:** Componentes: `TabelaComparativa` (partido, % 2022, % 2026, variação; ausente → "—" e selo "novo"/"não concorreu"); `BarrasVariacao` (barras divergentes em SVG, cores de `corDoPartido`). Páginas: panorama (resultado BR do 1º turno, 3 maiores variações, link para ranking); presidente (BR, tabela, ranking dos 50, cidades do exterior agregadas em linha "Exterior"); `governador/[uf]` (27 páginas via `getStaticPaths`; situação "vai ao 2º turno" quando `situacao === "2º turno"`). Toda página inclui `Fonte`; aviso visível quando `apuracao_completa` for falso.
- [ ] **Step 4:** `npm --prefix site run build` → gera `eleicoes-2026/governador/{27 UFs}/index.html`. Commit `feat: páginas de presidente, governador e panorama`.

---

### Task 12: Mapas SVG renderizados no build

**Files:**
- Create: `site/src/lib/mapa.ts`, `site/src/components/Mapa.astro`
- Modify: `presidente.astro`, `governador/[uf].astro`
- Test: `site/src/lib/mapa.test.ts`

**Interfaces:**
- Consumes: `dados/comum/malhas/*.json` (T9), `corDoPartido` (T10), `lerMunicipiosUF` (T11).
- Produces: `caminhosSVG(topo: Topology, largura: number, altura: number): { codigo: string; d: string }[]` (d3-geo `geoMercator().fitSize`, `topojson-client.feature`); componente `Mapa` (props `uf: string | "br"`, `cores: Record<string, string>` código IBGE ou UF → cor, `rotulos: Record<string, string>` → `<title>` acessível, `links?: Record<string, string>`); sempre acompanhado de tabela alternativa (`<details>` "Ver como tabela").

- [ ] **Step 1:** Testes: `test_um_caminho_por_feature` (malha de GO → 246 caminhos); `test_caminhos_dentro_da_caixa` (todas as coordenadas entre 0 e largura/altura).
- [ ] **Step 2:** Rodar → FAIL; `npm --prefix site i d3-geo topojson-client` (+ tipos); implementar; → PASS.
- [ ] **Step 3:** Presidente: mapa do Brasil por UF (vencedor 2026) e seletor de UF que leva ao mapa municipal da UF. Governador/[uf]: dois mapas municipais lado a lado (vencedor 2022 × 2026) com contorno destacado nos municípios com `virou === true`; município sem 2022 em hachura com rótulo "sem dados de 2022". Cada município é link para sua página (Tarefa 13).
- [ ] **Step 4:** Build → sucesso; maior página HTML < 1,5 MB (`ls -S site/dist/**/*.html | head`). Commit `feat: mapas SVG gerados no build`.

---

### Task 13: Páginas de município e busca

**Files:**
- Create: `site/src/pages/eleicoes-2026/municipio/[uf]/[cidade].astro`, `site/src/components/BuscaMunicipio.astro`, `site/src/lib/busca.ts`
- Test: `site/src/lib/busca.test.ts`

**Interfaces:**
- Consumes: `lerMunicipiosUF` (T11), `TabelaComparativa`, `BarrasVariacao` (T11), `Mapa` (T12).
- Produces: rota `/eleicoes-2026/municipio/{uf minúscula}/{slug}/` para os 5.571 municípios; `buscar(termo: string, indice: ItemBusca[]): ItemBusca[]` (ignora acentos e maiúsculas, prefixo de palavra tem prioridade, máximo 8 resultados); índice `site/public/busca-municipios.json` gerado no build (`[{n: nome, uf, u: url}]`).

- [ ] **Step 1:** Testes: `test_busca_sem_acento` (`"anapolis"` encontra "ANÁPOLIS"); `test_prefixo_primeiro` (`"sao"` → "SÃO PAULO" antes de "LAGOA DE SÃO..." ); `test_maximo_8`.
- [ ] **Step 2:** Rodar → FAIL; implementar; → PASS.
- [ ] **Step 3:** Página do município: título "Quem manda aqui em {Nome}/{UF}?", frase-destaque gerada dos dados (ex.: "Em Anápolis, o PL cresceu 11,5 pontos desde 2022" — maior |delta| do presidente; sem 2022 → "Primeira eleição presidencial de {Nome}"), seções presidente e governador (tabela + barras), comparecimento/abstenção/brancos/nulos 2022 × 2026, link para a UF, `Fonte`. Busca na home e no cabeçalho (ilha com JS mínimo, sem framework).
- [ ] **Step 4:** Build → `find site/dist/eleicoes-2026/municipio -name index.html | wc -l` = **5571**; build total < 10 min. Commit `feat: páginas de município e busca`.

---

### Task 14: Cartões de compartilhamento

**Files:**
- Create: `site/src/pages/og/[...rota].png.ts`, `site/src/lib/cartao.ts`
- Modify: `Layout.astro` (meta `og:image`, `twitter:card`)
- Test: `site/src/lib/cartao.test.ts`

**Interfaces:**
- Consumes: frase-destaque (T13), tokens de cor (T10).
- Produces: `fraseDestaque(m: MunicipioComparado): string` (movida de T13 para `cartao.ts` e reutilizada lá); PNG 1200×630 por página (home, panorama, presidente, 27 governadores, 5.571 municípios) com logo, frase-destaque e "quemmandaaqui.com.br"; fonte embarcada (arquivo `.ttf` da identidade em `site/src/assets/fontes/`).

- [ ] **Step 1:** Testes: `test_frase_maior_variacao`; `test_frase_sem_2022`; `test_frase_cabe_em_120_caracteres`.
- [ ] **Step 2:** Rodar → FAIL; `npm --prefix site i satori @resvg/resvg-js`; implementar; → PASS.
- [ ] **Step 3:** Build → `site/dist/og/` contém 5.601 PNGs; total de arquivos em `site/dist` < 20.000 (limite da Cloudflare Pages). Conferir 3 cartões visualmente (Read nos PNGs).
- [ ] **Step 4:** Commit `feat: cartões de compartilhamento`.

---

### Task 15: Publicação (GitHub, Cloudflare Pages, domínio, automação)

**Files:**
- Create: `.github/workflows/deploy.yml`, `.github/workflows/atualizar-dados.yml`, `docs/guia-do-dono.md`

**Interfaces:**
- Consumes: ações do dono D1, D2, D3, D5.
- Produces: site em `https://quemmandaaqui.com.br`; deploy automático a cada push em `main`; atualização de dados manual (`workflow_dispatch`) e diária às 06:00 de Brasília (`cron: "0 9 * * *"`) que roda o pipeline (com `actions/cache` para `.cache/`), faz commit de `dados/` se mudou, e dispara o deploy.

- [ ] **Step 1:** Com D1 feito: instalar `gh` (`winget install --id GitHub.cli -e`), `gh auth login` (dono autoriza no navegador), criar repositório público `quem-manda-aqui` e fazer push.
- [ ] **Step 2:** `deploy.yml`: Node 22, `npm ci` + `npm run build` em `site/`, `cloudflare/wrangler-action` com `pages deploy site/dist --project-name=quem-manda-aqui`, usando os secrets de D5. Push → workflow verde; site acessível em `quem-manda-aqui.pages.dev`.
- [ ] **Step 3:** Com D3 propagado: no painel da Cloudflare Pages, domínio personalizado `quemmandaaqui.com.br` + `www` (redirecionando para o domínio sem `www`). Verificar `curl -sI https://quemmandaaqui.com.br` → `HTTP/2 200`. Ativar Web Analytics e definir `PUBLIC_CF_ANALYTICS_TOKEN` como variável do build.
- [ ] **Step 4:** `atualizar-dados.yml` conforme Produces; rodar manualmente uma vez (`gh workflow run atualizar-dados.yml`) → verde; falha de conferência deixa o workflow vermelho sem commit.
- [ ] **Step 5:** Verificação final no celular (DevTools, 390 px): home, presidente, governador/go, município Goiânia, busca, modo escuro, cartão OG (validar com o depurador de compartilhamento do Facebook ou `curl` na URL do PNG).
- [ ] **Step 6:** `docs/guia-do-dono.md`: como ver se o site está no ar, como disparar atualização de dados, o que fazer se o workflow ficar vermelho, como falar comigo. Commit `chore: publicação e automação` e push.

---

## Calendário-alvo

| Data | Tarefas |
|---|---|
| 05–07/10 | 1–9 (pipeline completo e dados gerados) + D1–D3 |
| 08–11/10 | 10–14 (site) + D4–D5 |
| 12/10 | 15 — no ar |
