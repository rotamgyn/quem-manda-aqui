# Quem Manda Aqui — Plataforma base + Módulo Eleições 2026

**Data:** 04/10/2026 (dia do 1º turno)
**Status:** design aprovado em conversa; aguardando revisão desta spec
**Escopo desta spec:** Subprojeto 0 (plataforma base) e Subprojeto 1 (módulo Eleições 2026)
**Domínio pretendido:** quemmandaaqui.com.br (livre no Registro.br em 04/10/2026; registrar e consultar INPI)

---

## 1. Objetivo e público

Plataforma de política brasileira, **neutra e técnica**, baseada exclusivamente em dados abertos e públicos coletados de forma ética. O primeiro módulo compara as eleições de **2022 × 2026** para **presidente e governador**, com análises que os grandes portais não oferecem, e funciona **ao vivo no 2º turno (25/10/2026)**.

- **Público fase 1:** eleitor comum (vitrine popular, celular primeiro).
- **Público futuro:** clientes profissionais (jornalistas, analistas, assessorias) — camada comercial fora desta spec.
- **Quem constrói e opera:** Claude escreve todo o código e a documentação; o dono do projeto (não técnico) cria contas, registra domínio e aprova publicações.
- **Orçamento:** até R$ 300/mês; estimativa real ≈ US$ 5/mês (Cloudflare Workers Paid) + ~R$ 40/ano (domínio).

### Critérios de sucesso

1. No ar até **12/10/2026** com resultados do 1º turno comparados a 2022.
2. Em **25/10/2026**: atualização a cada ~1 minuto, sem queda sob pico de acesso, com projeção apresentada como faixa de incerteza.
3. Nenhum número publicado diverge dos totais oficiais do TSE.
4. Toda análise tem página de metodologia com fonte, data de coleta e limitações.

### Princípios editoriais

- **Neutralidade:** comparações sempre **por partido/federação do candidato**, nunca por rótulos ideológicos ("esquerda", "direita"). Quando não houver correspondência direta entre 2022 e 2026, o site diz isso explicitamente.
- **Cores neutras:** gráficos e mapas usam paleta categórica própria, **não** as cores dos partidos nem verde-amarelo, para evitar associação simbólica com campanhas.
- **Transparência:** fontes, datas e tabela de correspondência de partidos são públicas.
- **Ética com as fontes:** só um robô consulta o TSE (no máximo 1 vez por minuto, apenas arquivos que mudaram); visitantes nunca acessam o TSE diretamente.

---

## 2. Decomposição e roadmap

| # | Subprojeto | Quando | Situação |
|---|---|---|---|
| 0 | Plataforma base (marca, layout, home, componentes, dados comuns, infraestrutura) | até 12/10/2026 | **esta spec** |
| 1 | Módulo Eleições 2026 (análises A–E + ao vivo) | até 22/10 (ensaio) / 25/10 | **esta spec** |
| 2 | Monitor do Congresso (votações, fidelidade, blocos) | nov/2026 | spec própria futura |
| 3 | Gastos dos parlamentares | após o 2 | spec própria futura |
| 4 | Rumo a 2028/2030 | 2027 | spec própria futura |
| 5 | Dinheiro das campanhas | após prestações de contas finais | spec própria futura |
| 6 | Governo eleito | a partir de jan/2027 | spec própria futura |

A plataforma deve **comportar** os módulos 2–6 (estrutura de pastas, navegação, cartões "em breve"), sem implementá-los.

---

## 3. Fontes de dados (verificadas em 04/10/2026)

| Fonte | Uso | Formato / endereço |
|---|---|---|
| TSE — resultados ao vivo 2026 | 1º turno consolidado; 2º turno ao vivo | JSON em `resultados.tse.jus.br/oficial/ele2026/<cd_eleicao>/dados/<uf>/<arquivo>` |
| TSE — índice de eleições | descobrir códigos de eleição (1º turno: federal **6257**, estadual **6259**; 2º turno: a descobrir no índice) | `resultados.tse.jus.br/oficial/comum/config/ele-c.json` |
| TSE — Dados Abertos 2022 | votos por município/zona, comparecimento, abstenção, brancos/nulos | `cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_2022.zip` (~640 MB) e `detalhe_votacao_munzona_2022.zip` |
| TSE — Perfil do eleitorado 2026 | idade, escolaridade, gênero por município | `cdn.tse.jus.br/estatistica/sead/odsele/perfil_eleitorado/perfil_eleitorado_2026.zip` |
| IBGE — Censo 2022 | renda, urbanização, população por município | API SIDRA / downloads IBGE |

**Fatos observados nos arquivos ao vivo de 2026:**
- Arquivo de resultado por abrangência: `<uf|br>[<cod_municipio_tse>]-c<cargo 4 dígitos>-e<eleicao 6 dígitos>-u.json` (ex.: `br/br-c0001-e006257-u.json`, `go/go93734-c0001-e006257-u.json`).
- Arquivo de andamento da apuração: `br/br-e006257-ab.json` (percentual de municípios/seções totalizados por UF).
- Estrutura aninhada: `carg[] → agr[] (agremiação) → par[] (partido) → cand[]`, com `vap` (votos) e `pvap` (percentual, vírgula decimal). Campo `idg` muda a cada nova versão.
- Codificação de texto não é UTF-8 limpo (acentos corrompidos ao ler como UTF-8) — o leitor deve tratar a codificação explicitamente.
- **Sem cabeçalho CORS** → acesso direto pelo navegador é inviável (confirma a arquitetura com robô intermediário).
- Os arquivos ao vivo de 2022 **não** estão mais nesse servidor; 2022 vem só do Dados Abertos.
- Formato de 2026 difere do formato de 2022 (`dados-simplificados/...-r.json` não existe mais).

---

## 4. Arquitetura

```
           FONTES PÚBLICAS                  PROCESSAMENTO                  PUBLICAÇÃO
  TSE Dados Abertos 2022  ─┐
  TSE Perfil Eleitorado   ─┼─▶ Pipeline Python (GitHub Actions) ─┐
  IBGE Censo 2022         ─┘    normaliza → analisa → JSON       ├─▶ Cloudflare R2 (JSONs) ─▶ Site estático Astro
  TSE resultados ao vivo  ───▶ Robô ao vivo (Cloudflare Worker,  ─┘                            (Cloudflare Pages + CDN)
                                cron 1 min) busca → projeta → JSON
```

### Unidades e responsabilidades

1. **Pipeline Python** (`modulos/eleicoes-2026/pipeline/`): baixa fontes, normaliza, executa análises A, C, D, E e o resultado consolidado; gera JSONs pequenos (um por abrangência/cargo/análise). Executado sob demanda ou diariamente via GitHub Actions. Python + pandas.
2. **Robô ao vivo** (`modulos/eleicoes-2026/robo/`): Cloudflare Worker em TypeScript, cron de 1 minuto, ativo apenas no dia do 2º turno (16h45 até apuração 100%). Lê o arquivo de andamento, baixa apenas arquivos cujo `idg` mudou, recalcula a projeção (análise B), grava JSON no R2.
3. **Site** (`site/`): Astro, páginas estáticas geradas a partir dos JSONs; a página ao vivo busca o JSON do R2 periodicamente no navegador.
4. **Dados comuns** (`dados-comuns/`): tabela de-para de municípios **TSE ↔ IBGE** (5.570), UFs, tabela de correspondência de partidos/federações 2022 ↔ 2026. Reutilizada pelos módulos futuros.

### Estrutura de pastas

```
D:\politicaBrasil\
  site/                    Astro: layout, home, componentes (mapa, gráficos, cartão de compartilhamento)
  dados-comuns/            municípios TSE↔IBGE, UFs, partidos
  modulos/
    eleicoes-2026/
      pipeline/            Python
      robo/                Worker TypeScript
      paginas/             páginas Astro do módulo
      testes/              amostras reais do TSE + testes
  docs/
```

Adicionar um módulo novo não altera os existentes.

### Tratamento de falhas

- TSE fora do ar ou arquivo inválido: robô mantém o último JSON válido; site mostra "atualizado às HH:MM" e aviso.
- Robô parado: site continua no ar com dado mais recente.
- **Botão de emergência:** variável de configuração que desliga a projeção e mantém apenas números oficiais.
- Divergência de totais (ver §7): publicação bloqueada automaticamente.

---

## 5. Análises (módulo Eleições 2026)

Unidade de análise: **município** (5.570). Seção/zona eleitoral fica fora desta spec.

### A) Migração 2022 → 2026
Para cada município, cargo (presidente, governador) e partido/federação: variação em pontos percentuais 2022 → 2026, troca de vencedor ("virada"). Saídas: mapa, ranking dos 50 municípios que mais mudaram (filtro por UF e porte).

### B) Projeção ao vivo do 2º turno
- Para cada município, parte apurada = dado oficial; parte não apurada = resultado do 1º turno 2026 do município + variação 1º→2º turno observada em **municípios semelhantes já apurados** (mesma UF, faixa de porte e perfil de voto 2022).
- Incerteza: reamostragem (bootstrap) das variações observadas → faixa com nível de confiança declarado.
- "Tendência definida" só quando a faixa inteira estiver de um lado de 50%.
- Exibida somente após 17h (Brasília), apenas com dados oficiais, com aviso explícito de que **não é pesquisa eleitoral**.
- **Validação obrigatória:** backtest simulando a apuração do 2º turno de 2022 a partir dos dados reais de 2022 (ordem de apuração simulada por UF/porte); medir erro por estágio de apuração e calibrar a faixa.

### C) Transferência 1º → 2º turno
Regressão ecológica entre municípios: relação entre votação de candidatos eliminados no 1º turno e crescimento dos finalistas no 2º. Apresentada como **estimativa agregada**, não voto individual. Produzida após 25/10. **É a primeira análise a ser adiada se o prazo apertar.**

### D) Abstenção, brancos e nulos
Variação 2022 → 2026 por município, cruzada com perfil do eleitorado (TSE) e Censo 2022 (IBGE). Pergunta-guia: "onde o eleitor deixou de votar, e quem é ele?"

### E) Forças políticas regionais
Partido do governador eleito × desempenho presidencial na UF; mapa de alinhamento governador/presidente eleito por partido; nº de estados governados por partido 2022 × 2026.

---

## 6. Páginas e experiência

| Página | Conteúdo |
|---|---|
| Home | Destaque do módulo ativo, busca de município, cartões "em breve" dos módulos 2–6. No dia 25/10 vira painel ao vivo. |
| `/eleicoes-2026` | Panorama 1º turno + principais mudanças desde 2022 |
| `/eleicoes-2026/presidente` | Resultado, mapa de migração, ranking de mudanças |
| `/eleicoes-2026/governador/[uf]` | 27 páginas |
| `/eleicoes-2026/municipio/[uf]/[cidade]` | 5.570 páginas: 2022 × 2026, abstenção, perfil |
| `/eleicoes-2026/ao-vivo` | Projeção com faixa, % apurado, horário da atualização |
| `/eleicoes-2026/analises/{abstencao,forcas-regionais,transferencia}` | Análises D, E, C |
| `/metodologia`, `/fontes`, `/sobre` | Transparência |

- **Celular primeiro**; modo claro/escuro; cores acessíveis a daltônicos; tabela alternativa a todo mapa.
- **Cartão de compartilhamento** (imagem Open Graph) gerado para cada página, com a frase-destaque da página (ex.: "Em Anápolis, o partido X caiu 8 pontos desde 2022").
- Sem login, comentários ou coleta de dados pessoais na fase 1 (LGPD simplificada; analytics sem cookies via Cloudflare Web Analytics).
- Identidade visual (logo, tipografia, paleta) definida no início da implementação, seguindo os princípios do §1; aprovação do dono antes do lançamento.

### Calendário de publicação

| Data | Entrega |
|---|---|
| ~12/10 | Home, presidente, governadores, páginas de município (1º turno × 2022) |
| ~18/10 | Análises D e E |
| 22/10 | Ensaio geral do ao vivo (backtest + teste de carga + teste do robô) |
| 25/10 | Ao vivo |
| após 25/10 | Análise C, consolidação do 2º turno |

---

## 7. Testes e verificação

1. **Leitores de dados:** testes automáticos com arquivos reais do TSE salvos como amostras (incluindo os de 04/10/2026); falham se o formato mudar.
2. **Conferência de totais:** totais nacional e por UF calculados pelo pipeline devem bater exatamente com os oficiais; caso contrário a publicação é bloqueada.
3. **Tabela de-para de municípios:** 5.570 municípios ligados TSE↔IBGE; qualquer ausência gera falha.
4. **Projeção:** backtest com 2022; registrar erro por estágio; faixa calibrada.
5. **Carga:** simulação de pico antes de 22/10.
6. **Robô:** teste ponta a ponta reproduzindo sequência de arquivos com `idg` crescente.

---

## 8. Operação e responsabilidades

**Dono do projeto (com passo a passo fornecido):** criar conta GitHub; criar conta Cloudflare e assinar Workers Paid; registrar `quemmandaaqui.com.br` no Registro.br (após consulta ao INPI); conectar contas para publicação.

**Claude:** código, testes, publicação, documentação, guia "o que fazer se..." em português simples; acompanhamento junto com o dono durante a apuração de 25/10.

**Recomendação:** revisão com advogado eleitoral antes da fase comercial (não bloqueia o lançamento).

---

## 9. Riscos

| Risco | Mitigação |
|---|---|
| Prazo de 21 dias | Ordem de publicação escalonada; análise C adiável |
| TSE mudar formato no 2º turno | Testes de leitura; ensaio de 22/10; botão de emergência |
| Correspondência de partidos 2022↔2026 (federações) | Tabela explícita e publicada na metodologia |
| Erro da projeção | Backtest, faixa de incerteza, "tendência" só com faixa inteira de um lado, botão de emergência |
| Pico de tráfego | Site estático em CDN; JSON ao vivo cacheado |
| Marca já registrada por terceiros | Consulta INPI antes do registro do domínio |

---

## 10. Decisões registradas (confirmadas pelo dono em 04/10/2026)

1. **Cores neutras:** gráficos e mapas não usam cores de partidos nem verde-amarelo.
2. **Métricas sem cookies:** Cloudflare Web Analytics (gratuito); sem banner de cookies.
3. **Identidade visual:** logo, tipografia e paleta definidos no início da implementação e aprovados pelo dono antes do lançamento.
4. **Marca mantida: "Quem Manda Aqui".** "Animal Político" foi avaliado e descartado (nome já usado por grande veículo de jornalismo político mexicano, animalpolitico.com; baixa exclusividade em buscas). A frase de Aristóteles entra como **manifesto** na página `/sobre`: *"O ser humano é um animal político. Aqui, você descobre quem manda — com dados."*

**Marca:** busca na base de **Marcas** do INPI em 04/10/2026 (dados até 29/09/2026) por "quem manda aqui": nenhum resultado. Recomendado depositar o pedido de registro da marca (classes 35, 38 e 41) após o lançamento.

---

## 11. Fora do escopo desta spec

Login, área de cliente, assinatura, API pública, newsletter, comentários; cargos de senador e deputados; análise por seção/zona; módulos 2–6.
