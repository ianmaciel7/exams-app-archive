# Exams App Archive

**Arquivo privado, verificável e pesquisável de versões antigas do Exam App.**
Este repositório não é o aplicativo ativo; contém apenas ferramentas, manifestos
e índices. Históricos grandes ficam em **Git Bundles anexados a releases privadas**,
não em dezenas de branches.

## Situação atual do arquivamento integral

**Ainda não é 100%.** Git público verificado (54/54 branches), 12/12 branches antigas
de `notes-app` restauráveis. Faltam os **objetos Git** das 4 branches privadas
`main`, `dev`, `stag`, `firebase/file` e das 3 tags de Notes, apesar de seus
SHAs já constarem do inventário.

Enquanto a autorização para clonar o repositório privado não está configurada,
a integração GitHub conectada copiou para
[inventory/notes-app/](inventory/notes-app/README.md) as descrições de 50 PRs,
37 submissões de review, 100 comentários inline, 10 comentários de conversa,
153 eventos, 1.889 registros de alterações de arquivos, 3 releases e
**1.130 registros de execução de Actions**. Isto não inclui os logs binários de CI.

- [Auditoria de 30.098 objetos Git públicos](reports/PUBLIC-GIT-EXTERNALS.md):
  nenhum ponteiro LFS ou submódulo encontrado nos sete bundles públicos.
- [Backup de Notes com acesso mínimo](https://github.com/ianmaciel7/exams-app-archive/actions/workflows/archive-private-notes.yml):
  requer configurar o secret `NOTES_READ_TOKEN` na aba Actions do arquivo.
- [Exportação de metadados dos projetos públicos](https://github.com/ianmaciel7/exams-app-archive/releases/tag/public-metadata-2026-11-23):
  execução concluída para sete repositórios, com ZIPs, manifesto e checksums.
  A ocorrência HTTP 500 na exportação de reviews do PR #248 de `exams-app-antigo-2`
  foi verificada separadamente: a coleção possui zero reviews, conforme
  [suplemento arquivado](inventory/exams-app-antigo-2/pr-248-reviews-supplement.json).

**Não apague repositórios originais antes de concluir e testar essas pendências.**

## Comece por aqui

| Recurso | Para que serve |
|---|---|
| **[Verificação independente de arquivamento](docs/VERIFICATION-2026-11-23.md)** | **Situação atual: Git público íntegro; 4 branches privadas e 3 tags ainda pendentes, além de metadados de PR/CI** |
| [Critérios para excluir repositórios antigos](docs/DELETE-READINESS.md) | Gate: restauração, histórico de PRs, evidências do GitHub Actions e backup independente antes da exclusão |
| [Auditoria dos 9 repositórios](docs/AUDIT-COVERAGE-2026-11-23.md) | Cobertura e lacunas, com 71 branch heads inventariados |
| [Backup completo de exams-app](https://github.com/ianmaciel7/exams-app-archive/releases/tag/exams-app-2026-11-23-complete) | **Todas as 4 branches**, refs de PR, imagens, documentos, inventário e metadados GitHub |
| [Relatório e catálogo exams-app](docs/EXAMS-APP-COMPLETE.md) | Contagem de arquivos por branch e instruções de recuperação |
| [Auditoria de objetos Git, mídia e LFS](reports/EXAMS-APP-VERIFY.md) | `git fsck --full`, 4 branches, TAR de dev, 3.870 objetos examinados, 0 ponteiros LFS e 0 submódulos |
| [Logs CI originais do exams-app](https://github.com/ianmaciel7/exams-app-archive/releases/tag/exams-app-2026-11-23-ci-logs) | Dois logs recuperados do GitHub Actions, comprimidos e verificados por SHA-256 |
| [Artefatos históricos de CI de repos antigos](https://github.com/ianmaciel7/exams-app-archive/releases/tag/legacy-ci-artifacts-2026-11-23-bulk) | **2.883/2.883 ZIPs de evidência** guardados em 16 TARs com SHA-256 e manifesto global; restauração real testada |
| [Backup Git dos demais projetos públicos](https://github.com/ianmaciel7/exams-app-archive/releases/tag/archive-2026-11-23-all-refs) | Versões antigas, templates e referências de PR preservadas |
| [Índice SQLite FTS5 mais recente](https://github.com/ianmaciel7/exams-app-archive/releases/tag/index-2026-11-23-exams-complete) | Busca histórica em todos os projetos e nas quatro branches de exams-app |
| [Relatório da busca completa](reports/FULL-INDEX.md) | Resultados e métricas reais da indexação |
| [Verificação dos 15 bundles internos](reports/embedded-bundles-audit.md) | Preservação de 12 branches `notes-app-old*` e três backups Exams Old |
| [Guia prático de recuperação](docs/EXTRACTION-GUIDE.md) | Consultar índices e restaurar arquivos originais por commit + caminho |

## Escopo validado em 23/11/2026

- **7 repositórios públicos**: os cinco projetos principais (exams-app, exams-app-old,
  exams-app-antigo-2 e dois templates), mais dois repositórios auxiliares.
- **523 referências Git** preservadas ao combinar o backup público geral com o backup completo do `exams-app`, incluindo **469 refs de PR**. As duas branches antes omitidas do `exams-app` agora estão preservadas.
- **12 versões históricas de Notes** (`old` e `old-1` a `old-11`) recuperadas
  a partir dos bundles internos; os **15/15 bundles** históricos tiveram integridade
  verificada e heads correspondentes às branches atuais.
- **19 fontes Git pesquisáveis** em um SQLite FTS5 reconstruído exclusivamente das releases privadas. Os valores atualizados estão em [reports/FULL-INDEX.md](reports/FULL-INDEX.md); incluem as quatro branches originais de `exams-app`.

**Pendente:** o backup integral do `notes-app` privado para `main`, `dev`, `stag`,
`firebase/file` e tags `v0.1.0`, `v0.2.0`, `v0.3.0`. O token do GitHub Actions
deste repositório não possui acesso automático para clonar outro repositório privado.
Não tornar o `notes-app` público para contornar isso.

## ChatGPT nativo: pesquisa privada FTS5

- [Consulta remota via GitHub Actions](docs/PRIVATE-CHATGPT-SEARCH.md): perguntas FTS5 e inventário de imagens pelo GitHub conectado, sem PC e sem novo servidor MCP. Usa a branch privada `archive-search-queries` separada da `main` e a release verificada.

## Explorador local e plugin Codex

- [Plugin Codex privado](plugins/exams-archive/README.md): consulta autenticada por SQLite FTS5, imagens, recuperação por SHA + path e exportação JSON local. Marketplace do repositório em `.agents/plugins/marketplace.json`.
- [GitHub Pages — explorador local](site/README.md): interface estática que abre um JSON escolhido no navegador. **O Pages pode ser público mesmo com o repositório privado; nenhum índice, bundle ou dado histórico é publicado.**
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

**Fora do Git:** bundles grandes e o índice completo comprimido ficam em releases
privadas. Requere-se autenticação GitHub para acessá-los.
