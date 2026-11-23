# Checklist de qualidade visual e de comportamento

Não declarar "prévia fiel" sem executar/verificar os itens pertinentes. Um protótipo recuperado e descrito não é um teste novo. Capture e compare imagens quando houver ambiente de navegador.

## Testes de imagem (originais vs render)

- [ ] Desktop claro normal: comparar com `d-light-1.png`.
- [ ] Desktop escuro normal: comparar com `d-dark-1.png`.
- [ ] Abrir menu de tipo (`d-light-2-menu-tipo.png`), contexto (`d-light-3-ctx.png`), Novo (`d-light-4-novo.png`) e switcher (`d-light-5-switcher.png`).
- [ ] Renomear (`d-light-6-renomear.png`), menu usuário (`d-light-7-usuario.png`), peek (`d-light-8-peek.png`).
- [ ] Loading, vazio, erro e lixeira com os 4 PNGs desktop específicos.
- [ ] Mobile claro e escuro: tela principal, gaveta e menu, 6 PNGs.
- [ ] Conferir tokens, fontes, ícones SVG, tamanhos/raios, espaçamento, densidade, truncamento, alinhamento, sombras, responsividade; não trocar SVGs por emoji ou Unicode em uma réplica.

## Testes funcionais

- [ ] Switcher de space (incluindo navegação por teclado e estado selecionado).
- [ ] Novo por tipo + filtro, foco e Esc; busca global; novos itens editáveis.
- [ ] Expandir/recolher seções e árvore Concurso → Edição → Cargo; leituras em estágios; tipos de objeto.
- [ ] Fixados, seções personalizadas, menus de linha e de seção, clique direito, `⋯`, renomear inline (F2, Enter, Esc).
- [ ] DnD e Alt+setas para reordenação, respeitando ordenação alfabética.
- [ ] Lixeira (mover, restaurar, excluir), confirmação para ação destrutiva quando aplicável.
- [ ] Recolher, peek 300/150ms, redimensionar 160–360px e double-click para reset, teclado.
- [ ] Drawer mobile, backdrop/Esc, sem ações inacessíveis por depender de hover.
- [ ] Foco visível, ARIA/teclado e `prefers-reduced-motion`, contraste adequado.
- [ ] Estados vazios, erro com retry, skeleton, sem loop infinito de loading.

## Classificação de qualidade

- `ORIGINAL CONFIRMADO`: bytes do arquivo original recuperados, sem reescrita, e renderização verificada; indicar se recursos externos faltam.
- `ADAPTAÇÃO VERIFICADA`: alterações explicitadas + regressão e comparação de capturas.
- `CONCEITO / MOCK`: visual criado a partir de especificações/resumos, não é cópia; não atribuir qualidade do original ao mock.
- `NÃO VERIFICADO`: só caminhos ou texto de descrição, sem bytes ou inspeção.

Nunca dizer que uma prévia improvisada é "o preview do repo". Se o ambiente não suporta execução integral e comparável, mostrar **capturas reais** e o arquivo standalone, e registrar a limitação em uma frase.

## Critérios adicionais após auditoria do GitHub (v0.4.0)

- [ ] Escolher **qual versão visual** é a fonte de verdade: (A) Capacities screenshot de sessão; (B) Notes old-4/old-5 React + tokens; (C) Exams 0.1.1 shell; (D) sidebar standalone de 62 KB. Não misturar cores, dimensões e hierarquias dessas fontes sem justificar.
- [ ] Comparar o shell inteiro: sidebar + trilha de abas + área de conteúdo + painel contextual. Capturas da matriz `lowchrome_97_after_*` em 768, 1024, 1366, claro/escuro e laterais abertas/fechadas.
- [ ] Validar geometria de referência **como estado histórico**, não universal: old-4 `docs/DESIGN.md` registra rail 46 px, gutter 10 px, painel 288 px, raio 12 px, menu de contexto 269 px, menu de criação com linhas 32 px e labels 14 px.
- [ ] Recuperar `src/components/ui/shared-styles.ts`, `compact-menu.tsx`, `src/app/_components/objects/object-icons.tsx` e `src/app/globals.css` de old-5 antes de inventar sombras, popovers ou ícones.
- [ ] Conferir que uso de SVG/tipografia não seja substituído por glifos Unicode genéricos, emoji, `span` placeholder ou cards adicionados para preencher espaço vazio.
- [ ] Para ChatGPT: abrir a prévia **na própria resposta**, com HTML/CSS/JS embutidos quando houver mecanismo adequado; nunca iframe GitHub/Raw, `fetch()` externo, `src` remota ou assets externos; sem promessa de equivalência com imagem não inspecionada.
- [ ] Testar em largura do embed e celular, inclusive abertura/fechamento de menu, posicionamento de popover em bordas, árvore com muitos itens, foco, sem scroll horizontal e render após alteração de tema.
- [ ] Dizer quais capturas foram realmente inspecionadas (nomes e ref), quais estados foram executados agora e quais são somente descritos no repositório. Capturas do Capacities de 2026 não garantem versão atual.
