# Plano 2 — Ao vivo no 2º turno (25/10/2026), versão enxuta

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** No dia 25/10/2026, a partir das 17h, o site mostra os números oficiais da apuração do 2º turno (presidente e os 6 governadores em disputa), atualizados a cada ~1 minuto e comparados com o 2º turno de 2022. A projeção estatística só aparece se passar no backtest.

**Architecture:** Um robô em Python (reaproveitando `leitor_2026`, `comparacao` e `qma_comum.http` do Plano 1) roda como **um único job longo do GitHub Actions** (até 6 h). Em cada ciclo de 60 s ele lê os arquivos oficiais de Brasil e UFs e faz uma fatia da varredura municipal, mantendo o limite de 4 req/s. Depois monta JSONs e os publica num bucket **Cloudflare R2** servido em `dados.quemmandaaqui.com.br` com cache curto. A página `/eleicoes-2026/ao-vivo` e a home leem esse JSON no navegador a cada 30 s.

**Tech Stack:** Python 3.12 (uv, httpx, boto3 para R2/S3), GitHub Actions, Cloudflare R2 + domínio próprio, Astro (página ao vivo com script cliente mínimo).

**Spec:** `docs/superpowers/specs/2026-10-04-quem-manda-aqui-plataforma-e-eleicoes-2026-design.md`. Este plano também depende do contrato de dados do Plano 1 (`docs/superpowers/plans/2026-10-04-plano-1-fundacao-e-lancamento.md`, Tarefa 9).

**Desvio da spec, registrado:** a spec previa um Cloudflare Worker em TypeScript. Este plano usa um job Python no GitHub Actions. Motivos: reaproveita código já testado, cabe no prazo de 7 dias e elimina o custo do Workers Paid. As garantias da spec continuam: um único robô consulta o TSE, visitantes leem só o CDN, atualização a cada ~1 min, último dado válido mantido em caso de falha e botão de emergência.

## Global Constraints

- Tudo do Plano 1 continua valendo: pt-BR, neutralidade, sem cores de partidos e sem verde-amarelo, **≤ 4 req/s ao TSE** e fonte/horário em toda página.
- Códigos 2026, 2º turno: presidente **6258** (cargo 1); governador **6260** (cargo 3). UFs com 2º turno de governador: as listadas em `.../ele2026/6260/config/mun-e006260-cm.json` (em 18/10: AC, AM, DF, ES, RN, TO). O código lê essa lista e não a fixa.
- 2022, 2º turno: código **545**. Comparação com 2022 sempre **2º turno × 2º turno**, por partido.
- Arquivo de andamento: `.../6258/dados/br/br-e006258-ab.json` (por UF: `and`, `s.pst`). Arquivos de resultado com o mesmo formato do 1º turno (`-u.json`), lidos por `ler_resultado_2026`.
- **Números oficiais publicados = arquivos do TSE tal como vieram.** No ao vivo o site não publica somas derivadas no lugar de totais oficiais. Dado municipal mostra o próprio horário e o próprio % de seções.
- Projeção: só depois das **17h00 (America/Sao_Paulo)**; sempre com faixa e nível de confiança; texto fixo **"Projeção estatística a partir de resultados oficiais parciais. Não é pesquisa eleitoral."**; "tendência definida" só quando a faixa inteira estiver de um lado de 50%. Sem backtest aprovado, ou com `projecao_ligada=false` em `controle.json`, a projeção não aparece.
- JSONs ao vivo com `Cache-Control: public, max-age=20`.
- Segredos só em GitHub Secrets: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.

## Review Focus

1. **TSE fora do ar ou arquivo inválido no meio da apuração:** o ciclo não derruba o robô. O último estado válido continua publicado e `estado.json` registra `erro_ultimo_ciclo` com o horário. → `test_ciclo_sobrevive_a_erro` (Tarefa 3).
2. **Arquivo que não mudou (`idg` igual):** não é parseado de novo nem conta como nova atualização. → `test_idg_igual_nao_reprocessa` (Tarefa 1).
3. **Município com 0% apurado ou ainda sem arquivo:** aparece como "aguardando", nunca com 0% de votos para alguém. → `test_municipio_sem_apuracao` (Tarefa 2).
4. **Antes das 17h ou projeção desligada:** o JSON não contém o bloco `projecao`. → `test_projecao_ausente_antes_das_17h` e `test_projecao_desligada` (Tarefa 5).
5. **Falha de upload no R2:** o robô tenta de novo no próximo ciclo e nunca publica `estado.json` antes dos arquivos de município de que ele depende. → `test_ordem_de_publicacao` (Tarefa 3).

---

## Ações do dono

- [ ] **D6 (até 21/10):** no painel da Cloudflare, ativar o **R2** (pede cartão, mas o uso previsto cabe no plano gratuito), criar o bucket `quem-manda-aqui-ao-vivo` e um token de API R2 com permissão "Object Read & Write" nesse bucket. Passar os 4 valores para eu cadastrar como Secrets.
- [ ] **D7 (25/10, 16h30–fim da apuração):** estar disponível para acompanhar.

---

## Estrutura de arquivos

```
modulos/eleicoes-2026/pipeline/src/qma_eleicoes/
  base_ao_vivo.py          dados estáticos para o ao vivo (2022 t2 + 2026 t1 por município)
  ao_vivo/__init__.py
  ao_vivo/coleta.py        ciclo de coleta incremental (idg, varredura municipal)
  ao_vivo/montar.py        monta os JSONs ao vivo
  ao_vivo/publicar.py      upload R2 (S3 API)
  ao_vivo/__main__.py      laço: python -m qma_eleicoes.ao_vivo
  ao_vivo/simulador.py     gera sequência de arquivos "TSE" a partir de 2022 t2 (ensaio e backtest)
  projecao.py              modelo de projeção
  backtest.py              backtest com 2022
dados/eleicoes-2026/base-ao-vivo.json
site/src/pages/eleicoes-2026/ao-vivo.astro, site/src/scripts/ao-vivo.ts, site/src/lib/aoVivo.ts
.github/workflows/ao-vivo.yml
docs/guia-dia-25.md
```

---

### Task 1: Base estática e coleta incremental

**Files:**
- Create: `base_ao_vivo.py`, `ao_vivo/__init__.py`, `ao_vivo/coleta.py`
- Modify: `config.py` (adicionar `ELEICAO_2026_T2 = {"presidente": "6258", "governador": "6260"}` e o parâmetro `eleicao` em `url_resultado_2026`, com padrão no 1º turno, para não quebrar chamadas existentes)
- Test: `testes/test_base_ao_vivo.py`, `testes/test_coleta_ao_vivo.py`

**Interfaces:**
- Produces: `gerar_base(r2022_t2: list[Resultado], r2026_t1: list[Resultado], municipios: list[Municipio]) -> dict`, gravado em `dados/eleicoes-2026/base-ao-vivo.json`: `{"municipios": {"<tse>": {"uf", "ibge", "nome", "slug", "porte": "ate10k"|"10a50k"|"50a200k"|"mais200k", "aptos_2026": int, "t1_2026": {"comparecimento": int, "validos": int, "partidos": {"PT": pct, "PL": pct, ...}}, "t2_2022": {"validos": int, "partidos": {...}} | null}}}`. As faixas de porte usam `aptos_2026` e as mesmas faixas do Plano 1.
- Produces: `class Coletor` com `__init__(self, municipios, ufs_governador: list[str], *, _baixar=baixar_json, max_por_ciclo: int = 200)` e `ciclo(self) -> RelatorioCiclo`. Cada ciclo baixa (com `forcar=True`) `br-e006258-ab.json`, BR e cada UF de presidente (incluindo ZZ) e as UFs de governador. Em seguida baixa até `max_por_ciclo` arquivos municipais, numa fila circular que prioriza municípios ainda não 100% e pula os que já estão em 100%. Só parseia arquivo cujo `idg` mudou. Expõe `resultados: dict[tuple[cargo, uf, municipio_tse | None], Resultado]` e `horarios: dict[mesma chave, str]` (`dg hg` do arquivo). `RelatorioCiclo(baixados: int, alterados: int, erros: list[str])`.
- A CLI de `qma_eleicoes` ganha o subcomando `gerar-base`.

- [ ] **Step 1:** Testes: `test_base_tem_todos_os_municipios` (5.571); `test_base_sem_2022_e_null`; `test_idg_igual_nao_reprocessa` (mesmo `idg` duas vezes → `alterados == 0` no 2º ciclo); `test_fila_prioriza_incompletos`; `test_pula_municipio_100`; `test_respeita_max_por_ciclo`.
- [ ] **Step 2:** Rodar → FAIL. Implementar. → PASS.
- [ ] **Step 3:** Rodar `uv run python -m qma_eleicoes gerar-base` de verdade (2022 t2 vem do leitor do Plano 1 com `turno=2`) e fazer commit de `base-ao-vivo.json`. Commits `feat: base estática e coleta incremental do ao vivo` e `dados: base do ao vivo`.

### Task 2: Montagem dos JSONs ao vivo

**Files:** Create `ao_vivo/montar.py`; Test `testes/test_montar_ao_vivo.py`

**Interfaces:**
- Consumes: `Coletor.resultados/horarios` (T1), base (T1), `comparar` e `carregar_equivalencias` (Plano 1).
- Produces: `montar(resultados, horarios, base, *, agora: datetime) -> dict[str, dict]` (caminho → conteúdo):
  - `ao-vivo/estado.json`: `{"atualizado_em", "andamento": {"br": pct, "<uf>": pct}, "presidente": {"br": ResultadoAoVivo, "ufs": {"<uf>": ResultadoAoVivo}}, "governador": {"<uf>": ResultadoAoVivo}, "projecao"?: {...}, "erro_ultimo_ciclo"?: str}`. Em `ResultadoAoVivo`: `{"horario_tse", "pct_secoes", "candidatos": [{"numero", "nome_urna", "partido", "votos", "pct"}], "comparecimento", "abstencao", "brancos", "nulos", "comparacao_2022": {"partidos": [{"partido", "pct_2022", "pct_2026", "delta_pp"}]} | null}`.
  - `ao-vivo/municipios/{uf}.json`: `[{"tse", "ibge", "pct_secoes", "status": "aguardando"|"parcial"|"completo", "vencedor": partido | null, "partidos": {"PT": pct, ...} | null, "delta_vs_2022": {"PT": pp, ...} | null, "horario_tse"}]`.
- Regras: percentuais com 2 casas; município sem arquivo ou com `pct_secoes == 0` → `status = "aguardando"`, com `partidos`, `vencedor` e `delta` `null`.

- [ ] **Step 1:** Testes: `test_estado_tem_numeros_oficiais_sem_soma` (o `br` do estado é exatamente o do arquivo BR); `test_municipio_sem_apuracao`; `test_comparacao_com_2022_t2`; `test_governador_so_ufs_com_segundo_turno`.
- [ ] **Step 2:** FAIL → implementar → PASS. Commit `feat: montagem dos JSONs ao vivo`.

### Task 3: Publicação no R2 e laço do robô

**Files:** Create `ao_vivo/publicar.py`, `ao_vivo/__main__.py`; Test `testes/test_publicar.py`, `testes/test_laco.py`

**Interfaces:**
- Produces: `class PublicadorR2(bucket, *, _cliente=None)` com `publicar(arquivos: dict[str, dict]) -> None` (`boto3` S3 com endpoint `https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com`; `ContentType: application/json; charset=utf-8`; `CacheControl: public, max-age=20`; **`ao-vivo/estado.json` sempre por último**) e `ler_controle() -> dict` (`controle.json` na raiz do bucket; ausente → `{"projecao_ligada": false}`). `PublicadorLocal(pasta)` com a mesma interface, para ensaio e testes.
- Produces: CLI `python -m qma_eleicoes.ao_vivo [--intervalo 60] [--ate HH:MM] [--simular PASTA] [--local PASTA]`. Laço: ciclo → montar → (projeção, T5) → publicar → dormir até completar o intervalo. Exceção num ciclo → registra, põe `erro_ultimo_ciclo` no próximo estado e continua. Termina quando `andamento.br == 100` e todas as UFs de governador estão em 100, ou em `--ate`.

- [ ] **Step 1:** Testes: `test_ordem_de_publicacao` (o último `put_object` é `estado.json`); `test_cabecalhos_cache`; `test_controle_ausente_desliga_projecao`; `test_ciclo_sobrevive_a_erro` (o `_baixar` falha uma vez → o laço segue e o próximo estado tem `erro_ultimo_ciclo`); `test_termina_com_100`.
- [ ] **Step 2:** FAIL → implementar → PASS. Commit `feat: publicação R2 e laço do robô ao vivo`.

### Task 4: Simulador de apuração (2022, 2º turno)

**Files:** Create `ao_vivo/simulador.py`; Test `testes/test_simulador.py`

**Interfaces:**
- Produces: `gerar_sequencia(r2022_t2: list[Resultado], *, passos: int = 40, semente: int = 25) -> Iterator[dict[str, dict]]`. Cada passo é um conjunto de arquivos no formato TSE `-u.json` (com `idg` crescente, `s.pstn` e votos parciais) e mais o `ab.json`. A ordem de apuração dos municípios é simulada: municípios menores e capitais primeiro, com embaralhamento por UF a partir da semente, e cada município avança por frações de seção.
- Produces: `baixar_simulado(sequencia) -> Callable` compatível com o `_baixar` do `Coletor`, que avança um passo a cada ciclo. Esse fluxo alimenta o ensaio geral e o backtest.

- [ ] **Step 1:** Testes: `test_ultimo_passo_igual_resultado_oficial_2022` (no passo final, BR = Lula 60.345.999 e Bolsonaro 58.206.354); `test_idg_cresce`; `test_formato_lido_por_ler_resultado_2026`.
- [ ] **Step 2:** FAIL → implementar → PASS. Commit `feat: simulador de apuração para ensaio e backtest`.

### Task 5: Projeção e backtest

**Files:** Create `projecao.py`, `backtest.py`; Test `testes/test_projecao.py`

**Interfaces:**
- Produces: `projetar(municipais: dict[str, dict], base: dict, finalistas: tuple[str, str], *, reamostras: int = 200, confianca: float = 0.90, semente: int = 25) -> Projecao | None`, com `Projecao(partido_a: str, pct_a: float, faixa_a: tuple[float, float], confianca: float, tendencia_definida: bool, pct_secoes_base: float)`.
- Modelo:
  - Município completo: usa o resultado real.
  - Município parcial ou aguardando: estima a participação final de A como `t1_2026.partidos[A] + swing`.
  - O `swing` é a mediana de (`pct_2t − pct_1t`) dos municípios **completos** do mesmo estrato, nesta ordem: UF × porte, depois UF, depois Brasil, com mínimo de 5 municípios por estrato.
  - Votos válidos esperados do restante = `t1_2026.validos × (1 − pct_secoes/100)`.
  - Retorna `None` quando há menos de 30 municípios completos.
  - Faixa: *bootstrap* dos swings.
- Produces: `rodar_backtest() -> RelatorioBacktest` usando o simulador (T4) e 2022 1º turno como "t1". Registra erro e cobertura da faixa nos estágios de 10% a 90% de seções apuradas.
  - **Critério de aprovação:** a partir de 30% apurado, o resultado final real fica dentro da faixa em **todos** os estágios, e o erro do ponto é < 1,0 p.p. a partir de 50%.
  - O relatório é gravado em `docs/backtest-2022.md`.
- Integração no laço (T3): o bloco `projecao` só entra se `agora >= 17:00`, `controle.projecao_ligada` for verdadeiro e o backtest estiver aprovado (arquivo `dados/eleicoes-2026/backtest-aprovado.json` versionado).

- [ ] **Step 1:** Testes: `test_projecao_com_tudo_completo_e_exata`; `test_projecao_none_com_poucos_completos`; `test_faixa_contem_ponto`; `test_tendencia_so_com_faixa_de_um_lado`; `test_projecao_ausente_antes_das_17h`; `test_projecao_desligada`.
- [ ] **Step 2:** FAIL → implementar → PASS.
- [ ] **Step 3:** Rodar `uv run python -m qma_eleicoes.backtest`. Se aprovado, fazer commit de `backtest-aprovado.json` e `docs/backtest-2022.md`. Se reprovado, fazer commit só do relatório e registrar no ledger que a projeção fica desligada (Ruling 8 do Plano 1). Commit `feat: projeção e backtest`.

### Task 6: Página ao vivo e home em modo eleição

**Files:** Create `site/src/pages/eleicoes-2026/ao-vivo.astro`, `site/src/scripts/ao-vivo.ts`, `site/src/lib/aoVivo.ts`; Modify `site/src/pages/index.astro`, `Mapa.astro` (atributo `data-ibge` em cada caminho); Test `site/src/lib/aoVivo.test.ts`

**Interfaces:**
- Consumes: JSONs da T2 em `PUBLIC_DADOS_AO_VIVO` (padrão `https://dados.quemmandaaqui.com.br`).
- Produces: `aoVivo.ts` com `estadoDaPagina(agora: Date, estado: Estado | null): "antes" | "apurando" | "encerrada" | "indisponivel"`, `textoAtualizado(iso: string, agora: Date): string` ("atualizado às 18h42 (há 1 min)") e `corMunicipio(m, cores)`. O script cliente busca `estado.json` a cada 30 s (e o `municipios/{uf}.json` da UF escolhida), atualiza números e mapa (recolorindo por `data-ibge`) e, em caso de erro, mantém o último dado com aviso.
- Antes das 17h de 25/10: "A apuração começa às 17h" mais a comparação 2022 × 1º turno. Entre 25/10 e 26/10 23:59, a home mostra no topo o bloco ao vivo (presidente BR) com link para a página.
- Bloco de projeção só se `estado.projecao` existir, com o texto fixo das Global Constraints.

- [ ] **Step 1:** Testes: `test_estado_antes_das_17h`; `test_estado_indisponivel_sem_dados`; `test_texto_atualizado`; `test_cor_municipio_aguardando_cinza`.
- [ ] **Step 2:** FAIL → implementar → PASS. Build ok. Commit `feat: página ao vivo e home em modo eleição`.

### Task 7: Infra, workflow e ensaio geral

**Files:** Create `.github/workflows/ao-vivo.yml`, `docs/guia-dia-25.md`

**Interfaces:** consome D6. Produz:
- workflow `ao-vivo.yml` com `workflow_dispatch` (entradas `simular: bool`, `ate: HH:MM`) e `schedule` (`cron: "15 19 25 10 *"` → 16h15 BRT), `timeout-minutes: 355`, uv + cache de `.cache/`, rodando `python -m qma_eleicoes.ao_vivo --ate 23:30`. No modo `simular`, usa o simulador e publica em `ensaio/` no bucket, em vez de `ao-vivo/`.
- Domínio `dados.quemmandaaqui.com.br` ligado ao bucket, CORS `GET` para `https://quemmandaaqui.com.br` e `www` e `controle.json` inicial `{"projecao_ligada": false}`.

- [ ] **Step 1:** Configurar o bucket, o domínio e o CORS (com os dados de D6); cadastrar os Secrets via `gh secret set`. Verificar com `curl -sI https://dados.quemmandaaqui.com.br/controle.json` → 200 com `access-control-allow-origin` correto.
- [ ] **Step 2:** **Ensaio geral (até 24/10):** disparar `gh workflow run ao-vivo.yml -f simular=true -f ate=<agora+40min>`, abrir o site apontando para `ensaio/`, acompanhar 30 min e conferir números e mapa no celular. Teste de carga: `npx autocannon -c 200 -d 60 https://dados.quemmandaaqui.com.br/ensaio/estado.json` → 0 erros e p99 < 500 ms.
- [ ] **Step 3:** `docs/guia-dia-25.md`: horários, como ligar e desligar a projeção (editar `controle.json`), o que fazer se o workflow cair (rodar de novo com `gh workflow run`) e a lista de checagem das 16h30. Commit `chore: workflow ao vivo, infra e guia do dia 25`.

---

## Calendário-alvo

| Data | Tarefas |
|---|---|
| 21–22/10 | 1–4 (depois que o site do Plano 1 estiver no ar) |
| 23/10 | 5 (backtest decide se a projeção entra) e 6 |
| 24/10 | 7 (ensaio geral) |
| 25/10 | ao vivo |
