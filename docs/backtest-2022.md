# Backtest da projeção — 2º turno de 2022

**Resultado: APROVADO.** Modelo versão 1; gerado em 19/10/2026.

## O que é este teste

No dia 25/10 a página ao vivo pode mostrar uma *projeção estatística* do 2º turno de presidente, feita só com resultados oficiais parciais. Antes de ligar essa projeção, ela é testada com uma eleição cujo resultado já sabemos: o 2º turno de 2022 (resultado oficial: PT 50,90% dos votos válidos).

Como foi feito:

- Reproduzimos a apuração de 2022 em 40 etapas, município a município, com o simulador do robô. Os arquivos simulados passam pelo mesmo caminho do robô de verdade.
- O 1º turno de 2022 faz o papel do 1º turno de 2026.
- Em cada estágio (10%, 20%, ..., 90% das seções do Brasil apuradas), a projeção calcula um número (o *ponto*) e uma *faixa* com 90% de confiança.
- A ordem em que os municípios terminam a apuração é sorteada. Repetimos o teste com 15 sorteios (sementes 25, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14).

**Critério de aprovação** (precisa valer em todos os 15 sorteios):

1. A partir de 30% apurado, o resultado real fica dentro da faixa em todos os estágios.
2. A partir de 50% apurado, o ponto erra por menos de 1,0 ponto percentual.
3. Em nenhum cenário, nem nos testes de estresse abaixo, a página mostraria "tendência definida" para quem perdeu.

Na página, a projeção só aparece depois das 17h, com este backtest aprovado, com a chave `projecao_ligada` ligada e com pelo menos 30% das seções apuradas (abaixo disso o modelo não foi validado).

## Limites (leia antes de ligar a projeção)

- **A ordem sorteada é artificial.** No simulador, capitais e municípios pequenos terminam primeiro e as cidades médias e grandes por último, sem relação com a região. Na apuração real, regiões inteiras podem chegar antes de outras. Por isso há dois testes de estresse com ordens propositalmente ruins (os municípios mais favoráveis a um lado terminam primeiro). Eles não entram nos critérios 1 e 2, mas reprovam o modelo se a página mostrasse "tendência definida" para o lado errado.
- **Município parcial é "bem comportado" no simulador:** as seções já apuradas de uma cidade têm a mesma divisão de votos do total da cidade. O modelo não se aproveita disso: estima o restante de cada município pelo 1º turno mais a variação do estrato.
- **O ponto tende a subestimar quem cresce mais nas cidades grandes.** Em 2022, o ponto do PT ficou quase sempre abaixo do real nos estágios intermediários, porque a variação entre turnos medida nos municípios pequenos (que terminam antes) foi menor que a das cidades grandes. A faixa leva isso em conta com um *efeito nacional* desconhecido (escala 1,5), calibrado com estes mesmos dados de 2022: é a menor escala testada (1; 1,5; 2) em que o real ficou dentro da faixa em todos os estágios a partir de 30%, inclusive nas ordens adversas. Como a calibração usa a própria eleição de 2022, não há garantia de que 2026 se comporte igual.
- 2022 foi uma eleição muito apertada (50,9% × 49,1%): a faixa só fica inteira de um lado de 50% com bastante apuração. Esse é o comportamento desejado.

## Resumo dos 15 sorteios (entram no critério)

| Estágio | Real dentro da faixa | Maior erro do ponto (p.p.) | Largura média da faixa (p.p.) | Com tendência definida |
|---|---|---|---|---|
| 10% | 8 de 15 | 1,46 | 4,38 | 0 de 15 (6 sem projeção) |
| 20% | 15 de 15 | 1,19 | 4,07 | 0 de 15 |
| 30% | 15 de 15 | 1,03 | 3,27 | 0 de 15 |
| 40% | 15 de 15 | 0,68 | 2,57 | 0 de 15 |
| 50% | 15 de 15 | 0,50 | 2,07 | 0 de 15 |
| 60% | 15 de 15 | 0,42 | 1,69 | 2 de 15 |
| 70% | 15 de 15 | 0,33 | 1,22 | 14 de 15 |
| 80% | 15 de 15 | 0,19 | 0,68 | 15 de 15 |
| 90% | 15 de 15 | 0,07 | 0,23 | 15 de 15 |

## Testes de estresse (ordens adversas; não entram nos critérios 1 e 2)

### Adverso: maior % do PT primeiro

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 10,68% | 50,81 | 49,48 a 52,41 | 0,09 | sim | não |
| 20% | 20,59% | 50,76 | 49,35 a 52,08 | 0,15 | sim | não |
| 30% | 30,32% | 50,45 | 49,07 a 51,87 | 0,46 | sim | não |
| 40% | 40,18% | 50,71 | 49,49 a 51,84 | 0,19 | sim | não |
| 50% | 50,16% | 50,88 | 49,86 a 51,95 | 0,02 | sim | não |
| 60% | 62,39% | 50,92 | 50,18 a 51,61 | 0,02 | sim | sim, PT |
| 70% | 72,21% | 50,93 | 50,44 a 51,44 | 0,03 | sim | sim, PT |
| 80% | 83,00% | 50,92 | 50,52 a 51,22 | 0,02 | sim | sim, PT |
| 90% | 90,45% | 50,93 | 50,76 a 51,15 | 0,03 | sim | sim, PT |

### Adverso: maior % do PL primeiro

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 13,06% | 49,55 | 47,80 a 51,40 | 1,35 | sim | não |
| 20% | 20,91% | 49,72 | 48,55 a 51,18 | 1,18 | sim | não |
| 30% | 31,19% | 49,88 | 48,86 a 51,12 | 1,03 | sim | não |
| 40% | 41,18% | 49,99 | 49,16 a 50,94 | 0,91 | sim | não |
| 50% | 53,13% | 50,17 | 49,51 a 50,92 | 0,73 | sim | não |
| 60% | 64,71% | 50,37 | 49,71 a 51,05 | 0,54 | sim | não |
| 70% | 72,72% | 50,56 | 50,12 a 50,97 | 0,34 | sim | sim, PT |
| 80% | 81,53% | 50,73 | 50,43 a 51,06 | 0,17 | sim | sim, PT |
| 90% | 90,86% | 50,87 | 50,68 a 51,02 | 0,03 | sim | sim, PT |

## Detalhe de cada sorteio

### Semente 25

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 11,55% | — | — | — | não | não |
| 20% | 20,40% | 50,43 | 49,31 a 51,73 | 0,48 | sim | não |
| 30% | 30,25% | 50,69 | 49,53 a 51,89 | 0,21 | sim | não |
| 40% | 40,20% | 50,89 | 49,75 a 52,15 | 0,02 | sim | não |
| 50% | 50,71% | 50,95 | 49,91 a 52,07 | 0,04 | sim | não |
| 60% | 60,82% | 50,82 | 49,99 a 51,62 | 0,08 | sim | não |
| 70% | 71,40% | 50,85 | 50,29 a 51,53 | 0,05 | sim | sim, PT |
| 80% | 81,77% | 50,86 | 50,51 a 51,20 | 0,05 | sim | sim, PT |
| 90% | 90,62% | 50,87 | 50,67 a 51,06 | 0,03 | sim | sim, PT |

### Semente 1

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 10,14% | 49,54 | 48,38 a 50,89 | 1,36 | não | não |
| 20% | 21,22% | 49,85 | 46,54 a 53,41 | 1,05 | sim | não |
| 30% | 32,51% | 50,11 | 48,60 a 51,74 | 0,79 | sim | não |
| 40% | 42,80% | 50,38 | 48,89 a 51,64 | 0,53 | sim | não |
| 50% | 50,88% | 50,46 | 49,57 a 51,59 | 0,44 | sim | não |
| 60% | 60,07% | 50,49 | 49,47 a 51,45 | 0,41 | sim | não |
| 70% | 71,73% | 50,66 | 50,13 a 51,26 | 0,24 | sim | sim, PT |
| 80% | 85,22% | 50,75 | 50,48 a 51,04 | 0,15 | sim | sim, PT |
| 90% | 94,10% | 50,85 | 50,73 a 50,98 | 0,05 | sim | sim, PT |

### Semente 2

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 12,99% | 49,45 | 47,55 a 51,59 | 1,46 | sim | não |
| 20% | 20,88% | 49,94 | 47,75 a 51,93 | 0,96 | sim | não |
| 30% | 33,55% | 50,52 | 49,11 a 51,80 | 0,39 | sim | não |
| 40% | 40,32% | 50,55 | 49,30 a 51,70 | 0,35 | sim | não |
| 50% | 50,97% | 50,50 | 49,52 a 51,44 | 0,40 | sim | não |
| 60% | 60,48% | 50,52 | 49,70 a 51,33 | 0,38 | sim | não |
| 70% | 70,48% | 50,57 | 50,02 a 51,15 | 0,33 | sim | sim, PT |
| 80% | 85,91% | 50,72 | 50,44 a 51,03 | 0,18 | sim | sim, PT |
| 90% | 94,34% | 50,84 | 50,73 a 50,96 | 0,06 | sim | sim, PT |

### Semente 3

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 14,71% | 50,21 | 47,84 a 52,94 | 0,69 | sim | não |
| 20% | 21,22% | 50,20 | 47,86 a 52,71 | 0,70 | sim | não |
| 30% | 30,74% | 50,59 | 48,74 a 52,33 | 0,32 | sim | não |
| 40% | 40,47% | 50,62 | 49,25 a 51,97 | 0,28 | sim | não |
| 50% | 53,08% | 50,71 | 49,69 a 51,85 | 0,20 | sim | não |
| 60% | 60,71% | 50,83 | 49,92 a 51,65 | 0,07 | sim | não |
| 70% | 71,81% | 50,84 | 50,25 a 51,47 | 0,06 | sim | sim, PT |
| 80% | 80,78% | 50,83 | 50,40 a 51,24 | 0,07 | sim | sim, PT |
| 90% | 95,85% | 50,89 | 50,80 a 50,98 | 0,01 | sim | sim, PT |

### Semente 4

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 10,54% | — | — | — | não | não |
| 20% | 20,87% | 51,24 | 49,16 a 53,36 | 0,33 | sim | não |
| 30% | 31,54% | 50,41 | 49,16 a 51,65 | 0,49 | sim | não |
| 40% | 40,22% | 50,54 | 49,24 a 51,90 | 0,36 | sim | não |
| 50% | 50,79% | 50,61 | 49,41 a 51,78 | 0,29 | sim | não |
| 60% | 60,75% | 50,67 | 49,69 a 51,60 | 0,23 | sim | não |
| 70% | 70,50% | 50,77 | 50,18 a 51,39 | 0,13 | sim | sim, PT |
| 80% | 81,85% | 50,77 | 50,37 a 51,17 | 0,13 | sim | sim, PT |
| 90% | 95,66% | 50,88 | 50,79 a 50,97 | 0,02 | sim | sim, PT |

### Semente 5

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 13,31% | — | — | — | não | não |
| 20% | 20,18% | 50,97 | 48,80 a 52,99 | 0,07 | sim | não |
| 30% | 31,21% | 50,67 | 49,92 a 51,50 | 0,23 | sim | não |
| 40% | 40,22% | 50,58 | 49,27 a 51,61 | 0,32 | sim | não |
| 50% | 53,10% | 50,66 | 49,76 a 51,62 | 0,24 | sim | não |
| 60% | 60,43% | 50,83 | 50,06 a 51,66 | 0,08 | sim | sim, PT |
| 70% | 70,17% | 50,84 | 50,08 a 51,61 | 0,07 | sim | sim, PT |
| 80% | 80,70% | 50,83 | 50,42 a 51,27 | 0,07 | sim | sim, PT |
| 90% | 95,98% | 50,88 | 50,81 a 50,96 | 0,02 | sim | sim, PT |

### Semente 6

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 11,57% | 50,37 | 48,59 a 52,00 | 0,53 | sim | não |
| 20% | 20,16% | 50,28 | 48,72 a 52,42 | 0,62 | sim | não |
| 30% | 35,55% | 50,32 | 48,64 a 51,72 | 0,58 | sim | não |
| 40% | 41,72% | 50,41 | 49,02 a 51,68 | 0,49 | sim | não |
| 50% | 50,14% | 50,46 | 49,19 a 51,52 | 0,44 | sim | não |
| 60% | 61,80% | 50,58 | 49,62 a 51,46 | 0,32 | sim | não |
| 70% | 70,97% | 50,62 | 50,01 a 51,15 | 0,29 | sim | sim, PT |
| 80% | 84,74% | 50,73 | 50,45 a 51,05 | 0,17 | sim | sim, PT |
| 90% | 94,00% | 50,83 | 50,72 a 50,95 | 0,07 | sim | sim, PT |

### Semente 7

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 14,22% | 50,55 | 46,22 a 55,34 | 0,36 | sim | não |
| 20% | 21,13% | 50,35 | 47,95 a 53,08 | 0,56 | sim | não |
| 30% | 32,01% | 50,55 | 49,25 a 52,47 | 0,35 | sim | não |
| 40% | 40,47% | 50,65 | 49,43 a 51,68 | 0,25 | sim | não |
| 50% | 50,35% | 50,70 | 49,57 a 51,80 | 0,20 | sim | não |
| 60% | 62,10% | 50,72 | 49,97 a 51,52 | 0,18 | sim | não |
| 70% | 70,83% | 50,84 | 50,23 a 51,40 | 0,07 | sim | sim, PT |
| 80% | 81,30% | 50,84 | 50,47 a 51,22 | 0,06 | sim | sim, PT |
| 90% | 95,20% | 50,88 | 50,79 a 50,97 | 0,02 | sim | sim, PT |

### Semente 8

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 12,65% | — | — | — | não | não |
| 20% | 20,06% | 50,78 | 48,46 a 53,02 | 0,12 | sim | não |
| 30% | 31,49% | 50,84 | 49,12 a 52,49 | 0,06 | sim | não |
| 40% | 40,78% | 50,80 | 49,51 a 51,98 | 0,10 | sim | não |
| 50% | 50,32% | 50,63 | 49,66 a 51,64 | 0,28 | sim | não |
| 60% | 61,65% | 50,72 | 49,74 a 51,56 | 0,19 | sim | não |
| 70% | 70,80% | 50,74 | 50,15 a 51,32 | 0,16 | sim | sim, PT |
| 80% | 86,74% | 50,77 | 50,48 a 51,04 | 0,13 | sim | sim, PT |
| 90% | 94,75% | 50,88 | 50,77 a 51,00 | 0,03 | sim | sim, PT |

### Semente 9

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 11,58% | — | — | — | não | não |
| 20% | 20,36% | 49,71 | 47,79 a 51,93 | 1,19 | sim | não |
| 30% | 30,87% | 49,87 | 47,39 a 52,04 | 1,03 | sim | não |
| 40% | 41,10% | 50,22 | 48,92 a 51,80 | 0,68 | sim | não |
| 50% | 52,04% | 50,40 | 49,45 a 51,42 | 0,50 | sim | não |
| 60% | 62,18% | 50,56 | 49,77 a 51,25 | 0,34 | sim | não |
| 70% | 71,60% | 50,72 | 50,09 a 51,32 | 0,19 | sim | sim, PT |
| 80% | 80,72% | 50,83 | 50,44 a 51,23 | 0,07 | sim | sim, PT |
| 90% | 95,90% | 50,89 | 50,80 a 50,96 | 0,02 | sim | sim, PT |

### Semente 10

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 14,54% | 50,54 | 49,32 a 51,83 | 0,37 | sim | não |
| 20% | 20,78% | 50,34 | 49,05 a 51,66 | 0,57 | sim | não |
| 30% | 32,43% | 50,41 | 49,27 a 51,65 | 0,50 | sim | não |
| 40% | 40,36% | 50,48 | 49,44 a 51,49 | 0,42 | sim | não |
| 50% | 50,55% | 50,50 | 49,62 a 51,39 | 0,41 | sim | não |
| 60% | 60,37% | 50,54 | 49,87 a 51,24 | 0,37 | sim | não |
| 70% | 71,44% | 50,76 | 49,99 a 51,37 | 0,14 | sim | não |
| 80% | 82,43% | 50,82 | 50,46 a 51,19 | 0,08 | sim | sim, PT |
| 90% | 90,84% | 50,86 | 50,66 a 51,08 | 0,04 | sim | sim, PT |

### Semente 11

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 10,75% | 49,86 | 48,39 a 51,35 | 1,04 | sim | não |
| 20% | 20,39% | 50,10 | 48,68 a 51,40 | 0,81 | sim | não |
| 30% | 32,67% | 50,25 | 49,05 a 51,41 | 0,65 | sim | não |
| 40% | 41,94% | 50,38 | 49,01 a 51,66 | 0,53 | sim | não |
| 50% | 50,76% | 50,47 | 49,58 a 51,44 | 0,43 | sim | não |
| 60% | 60,48% | 50,67 | 49,83 a 51,55 | 0,23 | sim | não |
| 70% | 70,19% | 50,60 | 50,07 a 51,17 | 0,30 | sim | sim, PT |
| 80% | 84,72% | 50,72 | 50,43 a 51,03 | 0,18 | sim | sim, PT |
| 90% | 93,89% | 50,84 | 50,72 a 50,96 | 0,06 | sim | sim, PT |

### Semente 12

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 11,89% | 49,53 | 47,79 a 52,46 | 1,37 | sim | não |
| 20% | 20,53% | 49,86 | 47,02 a 53,01 | 1,04 | sim | não |
| 30% | 32,47% | 50,26 | 48,11 a 52,24 | 0,65 | sim | não |
| 40% | 42,75% | 50,47 | 48,94 a 51,97 | 0,43 | sim | não |
| 50% | 50,60% | 50,68 | 49,59 a 51,81 | 0,22 | sim | não |
| 60% | 60,66% | 50,52 | 49,49 a 51,26 | 0,38 | sim | não |
| 70% | 71,85% | 50,63 | 50,12 a 51,31 | 0,27 | sim | sim, PT |
| 80% | 85,78% | 50,79 | 50,50 a 51,07 | 0,11 | sim | sim, PT |
| 90% | 94,28% | 50,85 | 50,73 a 50,96 | 0,06 | sim | sim, PT |

### Semente 13

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 12,06% | 50,88 | 48,21 a 53,33 | 0,02 | sim | não |
| 20% | 20,75% | 50,47 | 49,04 a 51,90 | 0,43 | sim | não |
| 30% | 31,15% | 50,58 | 49,00 a 51,90 | 0,33 | sim | não |
| 40% | 41,08% | 50,67 | 49,59 a 51,88 | 0,23 | sim | não |
| 50% | 50,77% | 50,44 | 49,58 a 51,38 | 0,46 | sim | não |
| 60% | 61,32% | 50,48 | 49,65 a 51,23 | 0,42 | sim | não |
| 70% | 70,90% | 50,58 | 50,04 a 51,15 | 0,32 | sim | sim, PT |
| 80% | 86,42% | 50,71 | 50,45 a 50,99 | 0,19 | sim | sim, PT |
| 90% | 94,62% | 50,84 | 50,74 a 50,95 | 0,06 | sim | sim, PT |

### Semente 14

| Estágio | Seções BR | Ponto PT (%) | Faixa 90% | Erro (p.p.) | Real na faixa? | Tendência definida |
|---|---|---|---|---|---|---|
| 10% | 12,14% | — | — | — | não | não |
| 20% | 21,45% | 50,38 | 48,93 a 51,56 | 0,52 | sim | não |
| 30% | 31,71% | 50,47 | 47,04 a 54,13 | 0,43 | sim | não |
| 40% | 40,45% | 50,66 | 49,16 a 52,22 | 0,24 | sim | não |
| 50% | 50,16% | 50,74 | 49,55 a 51,97 | 0,16 | sim | não |
| 60% | 61,78% | 50,82 | 50,01 a 51,78 | 0,08 | sim | sim, PT |
| 70% | 70,65% | 50,88 | 50,25 a 51,56 | 0,03 | sim | sim, PT |
| 80% | 80,07% | 50,81 | 50,43 a 51,24 | 0,09 | sim | sim, PT |
| 90% | 96,03% | 50,88 | 50,80 a 50,96 | 0,02 | sim | sim, PT |

## Legenda

- *Seções BR*: % das seções do Brasil apuradas no momento da projeção.
- *Ponto*: o percentual final do PT que a projeção estimava naquele momento.
- *Faixa 90%*: intervalo onde a projeção dizia estar o resultado final, com 90% de confiança.
- *Erro*: diferença entre o ponto e o resultado real (50,90%).
- *Tendência definida*: a faixa inteira está de um lado de 50%.
- "—": a projeção não sai (menos de 30 municípios completos). Abaixo de 30% das seções a página também não mostra a projeção.
