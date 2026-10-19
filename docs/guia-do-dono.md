# Guia do dono — Quem Manda Aqui

## Endereços
- Site: https://quemmandaaqui.com.br (reserva: https://quem-manda-aqui.pages.dev)
- Código e Issues: https://github.com/rotamgyn/quem-manda-aqui

## Como ver se o site está no ar
1. Abra o endereço do site no celular. Se a página inicial carregar, está no ar.
2. Para ver o último envio: abra o repositório no GitHub, clique na aba **Actions** e veja a primeira linha da lista "Publicar site". Bolinha verde = publicado; X vermelho = falhou.

## Como atualizar os dados (botão "Atualizar dados")
1. Abra https://github.com/rotamgyn/quem-manda-aqui/actions
2. Na coluna da esquerda, clique em **Atualizar dados**.
3. Clique no botão **Run workflow** (à direita), deixe "main" selecionado.
4. Marque "Baixar tudo de novo" só se pedirem. Clique no botão verde **Run workflow**.
5. Se os dados mudaram, o robô grava e o site é republicado sozinho em cerca de 10 minutos. Se nada mudou, termina sem fazer nada.

## Se um workflow ficar vermelho
1. Clique na linha vermelha e depois no passo que tem o X para ler a mensagem.
2. Atualizar dados vermelho com mensagem de "divergência": os números não bateram com o total oficial do TSE. Isso é proposital: nada é publicado. Espere uns minutos e rode de novo (às vezes o TSE ainda está atualizando). O site continua com os dados anteriores.
3. Publicar site vermelho: clique em **Re-run all jobs** (canto superior direito). Se falhar de novo, chame o Claude e cole o link da página.
4. O site que já está no ar não sai do ar por causa de um workflow vermelho.

## Correções e contato do público
A página /sobre aponta para as **Issues** do repositório (https://github.com/rotamgyn/quem-manda-aqui/issues). Lá as pessoas abrem pedidos de correção. Você recebe aviso por e-mail do GitHub. Responda e feche a Issue quando resolver.

## Domínio
O domínio fica ligado ao projeto "quem-manda-aqui" no Cloudflare Pages (painel Cloudflare > Workers & Pages > quem-manda-aqui > Domínios personalizados).
