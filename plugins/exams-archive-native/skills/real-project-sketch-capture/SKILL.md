---
name: real-project-sketch-capture
description: Use quando o usuário pedir para mostrar como ficou, mostrar tudo, tirar foto, rodar o Exams App real, capturar a tela atualizada, ou revisar um toggle no sketch existente. Exige evidência de execução e SHA, nunca imagem gerada substituta.
---

# Captura do projeto real e alteração localizada

Leia `../ui-fidelity/SKILL.md` e `../ui-fidelity/references/chat-preview-contract.md`. Confira `exams-app@dev` no início e no fim. A fonte canônica de design do componente é o Especialista em UI/UX, skill sketch-toggle-real-preview.

## Regra de fidelidade — 2026-11-26

“Mostre como ficou”, “mostre tudo” e “rodando o projeto real”, quando se referem a um projeto existente, pedem evidência da execução do código original atualizado, não geração de imagem, mock recriado, SVG genérico ou uma tela inventada. Preserve todos os elementos não abrangidos pela alteração. Use o renderer nativo do projeto, com capturas reais pelo navegador. Se não houver ambiente de execução, informe o bloqueio e identifique claramente capturas anteriores pelo SHA; não substitua por imagem gerada. Uma prévia isolada do componente serve para discutir uma ideia, mas nunca prova sua aplicação no projeto.

## Switch / toggle de baixa fidelidade

O switch Auto-check aprovado conceitualmente em 2026-11-26 usa trilho horizontal em cápsula (laterais arredondadas, segmentos superiores e inferiores quase retos), marcador interno circular preenchido, folga visível entre marcador e contorno, posição esquerda para OFF e direita para ON. Use o mesmo material, espessura proporcional e irregularidade discreta dos demais traços; evite elipse comprimida, botão encostado no contorno e textura decorativa. No estado ativo, tinta semântica pode complementar a posição, mas nunca depender apenas de cor. Mantenha rótulo estável e legível. Verifique os dois estados em Light e Dark; no sketch estático, o estado desenhado não equivale à interação implementada. Para implementação funcional, validar nome acessível, role switch, aria-checked, foco e teclado conforme https://www.w3.org/WAI/ARIA/apg/patterns/switch/; não alegar conformidade apenas por aparência.

## Evidência e limites

Caso Exams App v0.1.0: alteração restrita a `docs/releases/v0.1.0/sketch/db/elements/e126.json` (trilho) e `e127.json` (marcador), commit experimental https://github.com/ianmaciel7/exams-app/commit/36c5e10977b64a3a67efa36f96602c7add2c008e; execução real https://github.com/ianmaciel7/exams-app/actions/runs/45861522179. Capturas Light/Dark produzidas no Open Artifact com Chromium/Playwright. O board permanece estático, estado OFF; o estado ON foi discutido em prévia de componente, não validado como comportamento do projeto. A branch dev não recebeu essa alteração. O usuário rejeitou as imagens geradas que alteravam layout e pediu execução real; não reutilizar essas imagens como evidência ou referência positiva.

## Pipeline executável

1. Verificar branch dev, SHA e árvore; identificar board, elementos exatos e renderer. No caso v0.1.0, `scripts/open-boards.mjs` abre o board nativo e `scripts/marker-sketch*.mjs` preserva tinta/Excalifont. Evitar modificar dev sem autorização; usar branch experimental existente ou isolada quando autorizado.
2. Se alterar, restringir o diff à geometria solicitada, preservar meta e demais elementos. Validar integridade (`node scripts/check-boards.mjs` e testes do preset e checker). Não usar imagens geradas para alterar o board.
3. Executar renderer original e Chromium/Playwright localmente ou em GitHub Actions autorizado. No workflow experimental existente, usar Open Artifact v0.16.3, `scripts/open-boards.mjs`, fontes e esquema nativo; workflow captura `first-dark.png`, `first-light.png`, `overview-dark.png`, `overview-light.png`. Não instalar dependências ou iniciar workflows não relacionados.
4. Verificar conclusão, SHA do run, artefato e arquivos PNG reais. Inspecionar o tamanho final e comparar regiões alteradas e não alteradas, ambos os temas. Mostrar diretamente no chat as capturas verificadas (links para arquivos reais recuperados). Preferir primeira tela quando usuário pede a tela inteira; overview do board quando pede todo o board. Se o job ainda não terminou, comunicar status e link, sem fingir imagem nova. Não inventar caminhos sandbox; confirmar existência antes de citar.
5. Identificar claramente branch/commit/run e limitações: sketch editável ou estático não é aplicação funcional. Conferir dev no fim. Não confundir captura antiga, render adaptado, ilustração e screenshot real.
