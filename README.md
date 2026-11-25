# Exams App Archive

## Centralização verificada — 24/11/2026

**[Relatório final e instruções de recuperação](reports/CENTRAL-ARCHIVE-2026-11-24.md)**: quatro pacotes criptografados publicados e validados por download, SHA-256 e descriptografia. Incluem Git atualizado, 52 releases/102 assets das origens, metadados e 84 evidências recentes. Os pacotes podem ser baixados diretamente deste repositório, sem depender dos repositórios de origem, mediante a frase secreta mantida pelo proprietário. O destino permanece público. Os relatórios anteriores são snapshots históricos; a consulta remota dos índices pelos plugins ainda pode exigir reconfiguração.

## Auditoria atual — 24/11/2026

Consultar [estado de aceite atualizado](reports/ARCHIVE-STATUS-2026-11-24.md): 161 PRs de exams-app-old reconciliados, complemento das worktrees restaurado e índice autenticado validado (595 refs). O arquivo permanece público; complementos privados ficam no Notes App. Logs históricos integrais e classificação de credenciais ainda têm limitações.

**[Abrir busca e grafo interativo](https://ianmaciel7.github.io/exams-app-archive/)** · [Interface em site/](https://ianmaciel7.github.io/exams-app-archive/site/) (quando Pages usa a branch).

Arquivo verificável e pesquisável de versões históricas. O repositório não é o aplicativo ativo.

## Situação verificada em 24/11/2026

> **Segurança:** o destino está público. Não publicar novos dados privados, executar consultas privadas remotas ou criar índices privados neste destino enquanto a visibilidade não for corrigida. Revisar a exposição histórica e rotacionar credenciais potencialmente expostas. O Pages deve ser separado do armazenamento privado.

Escopo principal: seis repositórios; os dois projetos auxiliares não entram nas métricas de aceite. A conferência autenticada de refs encontrou **69/69 branches, 519/519 refs de PR e 5/5 tags**, com SHAs correspondentes aos manifestos das releases. O backup Git de Notes foi concluído após os relatórios iniciais; o manifesto registra verificação, fsck, restauração e download de retorno. A verificação de 24/11 comparou os hashes declarados dos assets, sem repetir o download integral.

Decisão do proprietário (24/11/2026): manter o arquivo público; cópia no Google Drive não é requisito de aceite do arquivamento. A ausência de cópia independente continua sendo risco de perda e não autoriza exclusão das origens. Auditoria binária: 29/29 jobs aprovados, seis bundles restaurados, SHA-256 recalculados e 16 partições CI verificadas ([execução](https://github.com/ianmaciel7/exams-app-archive/actions/runs/45432868764)). Pendências: reconciliar três PRs de exams-app-old, destinos de gitlinks históricos de Notes, logs/anexos externos, triagem privada de candidatos a segredos e índice integral sanitizado. Dados expirados ou apagados não são recuperáveis apenas pelo Git.

**Nenhuma exclusão está autorizada.** Os relatórios datados de 23/11 são snapshots históricos e não substituem esta conferência.

## Comece por aqui

| Recurso | Para que serve |
|---|---|
| **[Verificação independente de arquivamento](docs/VERIFICATION-2026-11-23.md)** | Snapshot histórico; consultar a situação atual acima |
| [Critérios para excluir repositórios antigos](docs/DELETE-READINESS.md) | Gate: restauração, histórico de PRs, evidências do GitHub Actions e backup independente antes da exclusão |
| [Auditoria dos 9 repositórios](docs/AUDIT-COVERAGE-2026-11-23.md) | Cobertura e lacunas, com 71 branch heads inventariados |
| [Backup completo de exams-app](https://github.com/ianmaciel7/exams-app-archive/releases/tag/exams-app-2026-11-23-complete) | **Todas as 4 branches**, refs de PR, imagens, documentos, inventário e metadados GitHub |
| [Relatório e catálogo exams-app](docs/EXAMS-APP-COMPLETE.md) | Contagem de arquivos por branch e instruções de recuperação |
| [Auditoria de objetos Git, mídia e LFS](reports/EXAMS-APP-VERIFY.md) | `git fsck --full`, 4 branches, TAR de dev, 3.870 objetos examinados, 0 ponteiros LFS e 0 submódulos |
| [Logs CI originais do exams-app](https://github.com/ianmaciel7/exams-app-archive/releases/tag/exams-app-2026-11-23-ci-logs) | Dois logs recuperados do GitHub Actions, comprimidos e verificados por SHA-256 |
| [Artefatos históricos de CI de repos antigos](https://github.com/ianmaciel7/exams-app-archive/releases/tag/legacy-ci-artifacts-2026-11-23-bulk) | **2.883/2.883 ZIPs de evidência** guardados em 16 TARs com SHA-256 e manifesto global; restauração real testada |
| [Backup Git dos demais projetos públicos](https://github.com/ianmaciel7/exams-app-archive/releases/tag/archive-2026-11-23-all-refs) | Versões antigas, templates e referências de PR preservadas |
| [Índice SQLite FTS5 mais recente](https://github.com/ianmaciel7/exams-app-archive/releases/tag/index-2026-11-23-exams-complete) | Índice histórico anterior ao backup completo de Notes; cobertura parcial |
| [Relatório da busca completa](reports/FULL-INDEX.md) | Resultados e métricas reais da indexação |
| [Verificação dos 15 bundles internos](reports/embedded-bundles-audit.md) | Preservação de 12 branches `notes-app-old*` e três backups Exams Old |
| [Guia prático de recuperação](docs/EXTRACTION-GUIDE.md) | Consultar índices e restaurar arquivos originais por commit + caminho |

## Escopo histórico validado em 23/11/2026

- **7 repositórios públicos**: os cinco projetos principais (exams-app, exams-app-old,
  exams-app-antigo-2 e dois templates), mais dois repositórios auxiliares.
- **523 referências Git** preservadas ao combinar o backup público geral com o backup completo do `exams-app`, incluindo **469 refs de PR**. As duas branches antes omitidas do `exams-app` agora estão preservadas.
- **12 versões históricas de Notes** (`old` e `old-1` a `old-11`) recuperadas
  a partir dos bundles internos; os **15/15 bundles** históricos tiveram integridade
  verificada e heads correspondentes às branches atuais.
- **19 fontes Git pesquisáveis** em um SQLite FTS5 reconstruído exclusivamente das releases privadas. Os valores atualizados estão em [reports/FULL-INDEX.md](reports/FULL-INDEX.md); incluem as quatro branches originais de `exams-app`.

**Retificação 24/11:** o backup Git posterior de Notes está documentado no manifesto. A publicação e consulta privada permanecem bloqueadas até corrigir a visibilidade.

## ChatGPT nativo: pesquisa privada FTS5

- [Consulta remota via GitHub Actions](docs/PRIVATE-CHATGPT-SEARCH.md): perguntas FTS5 e inventário de imagens pelo GitHub conectado, sem PC e sem novo servidor MCP. Usa a branch `archive-search-queries`; não executar enquanto o destino estiver público.

## Explorador local e plugin Codex

- [Plugin Codex privado](plugins/exams-archive/README.md): consulta autenticada por SQLite FTS5, imagens, recuperação por SHA + path e exportação JSON local. Marketplace do repositório em `.agents/plugins/marketplace.json`.
- [GitHub Pages — explorador local](site/README.md): interface estática que abre um JSON escolhido no navegador. **O Pages deve publicar somente interface estática sanitizada, sem dados históricos privados.**
- [Workflow do Pages](.github/workflows/archive-pages.yml): deploy somente de quatro arquivos permitidos; a publicação requer GitHub Pages habilitado em Settings → Pages com Source = GitHub Actions.

## Busca com poucos tokens

O relatório Markdown pode ser consultado diretamente pelo GitHub conectado.
Para consultas completas, baixe o SQLite comprimido da release e execute:

```bash
python scripts/archive_index.py --db /caminho/full-index.sqlite search "fsrs"
python scripts/archive_index.py --db /caminho/full-index.sqlite search "grafo"
python scripts/archive_index.py --db /caminho/full-index.sqlite images --deleted-only
```

O índice retorna proveniência (repo, SHA, caminho e tipo) e **não duplica todos os
blobs históricos**. Para recuperar um arquivo original, baixe o bundle Git
correspondente e use o comando `recover` documentado no guia.

## Princípios

- Não alterar bundles originais nem apagar os repositórios de origem.
- Não declarar histórico completo sem verificar branches, PR refs, tags, LFS e
  objetos realmente alcançáveis.
- Preservar SHAs, checksums e referências de arquivos, documentos e imagens.
- Não executar código antigo automaticamente; código histórico serve como referência.
- Não copiar credenciais, segredos ou arquivos de ambiente para a base de pesquisa.
- Não adicionar servidor MCP nem embeddings se GitHub + SQLite FTS5 já atendem.

## Organização

- `inventory/`: estado observado de refs e tags.
- `manifests/`: lista de bundles, hashes e classificação das refs preservadas.
- `reports/`: auditorias, resultados reais e relatórios de busca.
- `scripts/`: indexação, validação, bundles, busca e recuperação histórica.
- `tests/`: testes sintéticos e verificações reprodutíveis.
- `docs/`: guia operacional e decisões de preservação.

**Fora do Git:** bundles grandes e índices ficam em releases. A visibilidade pública é intencional; não presuma confidencialidade das releases ou branches. Não publique novos dados privados ou índices não sanitizados.

## External UI/UX references

- [Grok Bot — UI and motion research](docs/references/grok-bot/README.md): official references, visual media links, original interactive lab, animated SVG/GIF and state sheet. External research, not recovered project source.

## General-purpose interface pattern library

- [Expanded UI/UX pattern library](https://github.com/ianmaciel7/exams-app-archive/tree/main/docs/references/interface-pattern-library): general visual languages, interaction, motion, AI UX and data visualization; structured records, provenance and validation. Independent of project-specific proposals.
