# Prévia INTERATIVA no próprio ChatGPT — contrato de entrega

## Intenção

Quando o usuário pedir "quero ver preview aqui" ou "dentro do ChatGPT", a entrega **tem que aparecer nesta resposta**, sem exigir clique em GitHub, download, localhost, serviço paralelo ou navegação externa. Um link para HTML original é evidência complementar, não substituto do preview.

## Bloqueios absolutos (erros já observados)

- **NÃO** carregar HTML via `fetch()` de GitHub Raw/API/CORS, nem criar `iframe src="..."` ou `iframe srcdoc` com código obtido remotamente. O embed do chat pode bloquear `fetch`, iframes e recursos externos e o preview vira tela vazia.
- **NÃO** referenciar CSS, fontes, ícones, screenshots, script ou componentes remotos. Evitar `AsyncImage` como única imagem quando a intenção é mock interativo, e não presumir que `<img>` com URL do GitHub é autorizado/carregável no runtime.
- **NÃO** declarar "original" se a interface foi reduzida, traduzida manualmente, separada do shell ou reimplementada; nesse caso o termo correto é "adaptação baseada em fontes".
- **NÃO** usar badges de sucesso ou dizer "testado" sem navegador ou execução real que tenha comprovado o comportamento.
- **NÃO** prometer uma sidebar idêntica apenas com base em resumo, screenshot ilustrativo de terceiro, query de imagem ou código incompleto.

## Como implementar quando AppBlock interno estiver disponível

1. Primeiro selecionar **um benchmark visual** e as imagens originais inspecionadas, mais CSS/ícones e geometry do branch correto. Registrar o que será adaptado.
2. Criar um HTML/CSS/JS **100% autocontido** no bloco. Dê um ID exclusivo ao root, prefixe classes/seletores para não afetar o ChatGPT nem outros previews, use SVG inline próprio, sem fontes proprietárias embarcadas e sem rede.
3. Se o original tem 62 KB, não precisa transplantar tudo indiscriminadamente: defina quais interações podem ser **realmente implementadas e verificadas**. Para qualidade premium, preferir fidelidade de composição/espacamento/identidade visual e comportamentos essenciais, não 30 funções fake.
4. Nunca substituir ícones por Unicode/emoji se os SVGs originais podem ser recriados como SVG próprios ou referências abertas permitidas. Manter cor por tipo apenas quando a referência escolhida a usa. Usar design tokens CSS derivados dos valores verificados (old-4/old-5 ou outra ref explicitada), não cores genéricas inventadas.
5. Implemente somente ações honestas: Novo abre um menu funcional, busca filtra, item navega, seção expande, overflow funciona, tema alterna, mobile usa drawer. Se Grafo/PDF/Simulado não existir, sinalizar "demonstração" em vez de mostrar área vazia fingindo app pronto.
6. Popover tem ancoragem e ajuste aos limites da viewport do embed; `z-index` e `overflow` corretos. No mobile, sempre oferecer controles acessíveis sem hover. Ações internas ficam no protótipo, não modificam dados do usuário.
7. Evitar declarar compatibilidade com todos os clientes: só afirmar execução onde foi testada. Se AppBlock ausente/não renderizar, preferir controles DIL disponíveis e screenshots de evidência, explicitando limitação; não fingir implementação interativa.

## Gate de QA antes de mostrar ao usuário

- O script inicializa sem erro; o menu **Novo** abre e fecha; busca responde; seleção/expand altera a tela; tema funciona; mobile abre/fecha; menus não são cortados.
- Desktop (ex.: 1366 × 900) e celular (ex.: 390 × 844) com imagem capturada ou inspeção real, se houver ambiente de teste; controle de largura do embed não provoca scroll horizontal ou texto invisível.
- Contexto central não deve ser grande branco vazio se fonte original exibe home, tabs, cards e inspetor (ver `lowchrome_97_after_light_1366_sideopen_rightopen.png`).
- Compare pelo menos 2 capturas pertinentes no mesmo estado (ou declare sem comparação). Não copiar UI proprietária de ChatGPT/Claude como se estivesse no repo.
- Fonte + SHA + status "ADAPTAÇÃO"/"ORIGINAL" declarados em uma linha curta abaixo do preview.

## Antipadrões registrados de respostas anteriores

1. Recriar os itens do menu em Unicode e uma coluna de 220px sem preservar a densidade/3 painéis.
2. Tentar desenhar **somente** uma sidebar enquanto as imagens de referência têm 3 superfícies e trilha de abas.
3. Criar viewer com `fetch` de 62KB remotos e iframes; dentro do chat não é robusto.
4. Incluir dados fictícios incompatíveis com o espaço (Receita Federal no lugar de Dataprev) e chamar isso de "preview original".
5. Alegar teste Playwright feito agora quando o resultado só estava em `decisoes.md` antigo.

Referências: `visual-source-catalog.md`, `source-map.md`, `visual-qa.md`.

## Motion and interaction QA

Use `skills/ui-motion/SKILL.md` for source-backed timing: delay != duration, interaction trigger and state, reduced-motion and interruption, mobile focus, and animations supported by browser tests. Do not claim motion reproduction from a screenshot-only comparison.
