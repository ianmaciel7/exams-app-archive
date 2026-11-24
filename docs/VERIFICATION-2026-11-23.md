# Verificação independente do exams-app-archive — 23/11/2026

> **Retificação de 24/11/2026:** este documento é um snapshot histórico. A conferência mais recente de cobertura, segurança e lacunas está no [README](../README.md). O backup Git posterior de Notes já possui manifesto verificado; isso não implica que o índice antigo foi reconstruído, que a privacidade esteja garantida ou que a exclusão esteja autorizada.


## Veredito

**Arquivo Git público validado, porém a consolidação TOTAL ainda não terminou.** A integridade dos objetos Git já preservados é forte; a auditoria não deve declarar 100% do acervo enquanto houver as lacunas abaixo.

Escopo: os oito repositórios de origem atualmente acessíveis na conta GitHub, o repositório privado de destino, as Releases do arquivo e as referências Git dos backups.

## Resultado por repositório

| Origem | Branches na origem | Branches arquivadas (HEAD atual coincidente) | Situação |
|---|---:|---:|---|
| `exams-app` | 4 | 4 | ✅ Bundle completo, PR #1, snapshot dev, arquivos/imagens, CI original |
| `exams-app-old` | 6 | 6 | ✅ Git completo; ❌ metadados de PR/CI não exportados |
| `exams-app-antigo-2` | 28 | 28 | ✅ Git completo; ❌ issues, PRs e CI não exportados |
| `shadcn-template` | 7 | 7 | ✅ Git completo; ❌ PRs e CI não exportados |
| `shadcn-firebase-template` | 7 | 7 | ✅ Git completo; ❌ PRs e CI não exportados |
| `fcc-responsive-web-design` | 1 | 1 | ✅ Git completo |
| `ianmaciel7` | 1 | 1 | ✅ Git completo |
| `notes-app` (privado) | 16 | 12 | ❌ Faltam 4 branches e 3 tags; metadados/release notes não foram exportados |
| **Total (8 origens)** | **70** | **66** | **4 branches privadas pendentes** |

A comparação de SHA de cada head foi feita entre a API GitHub atual e os manifestos da release `archive-2026-11-23-all-refs`, a release corrigida `exams-app-2026-11-23-complete` e o relatório dos 15 bundles internos. **Não apareceu nenhuma divergência de HEAD nas 66 branches contempladas.**

As 12 branches antigas de Notes (`old` e `old-1..old-11`) foram verificadas independentemente dos repositórios originais, a partir dos bundles contidos em `exams-app-antigo-2`, com SHA idêntico aos branches atuais.

## Integridade e permanência das Releases

Comparados **nome, tamanho, SHA-256 informado pelo GitHub e status de upload** com os manifestos armazenados no arquivo:

| Release | Arquivos principais conferidos | Erros |
|---|---:|---:|
| `archive-2026-11-23-initial` | 9/9 | 0 |
| `archive-2026-11-23-audit-complements` | 4/4 | 0 |
| `archive-2026-11-23-all-refs` | 7/7 | 0 |
| `exams-app-2026-11-23-complete` | 4/4 | 0 |
| `exams-app-2026-11-23-ci-logs` | 2/2 | 0 |

As cinco releases estão publicadas no repositório privado. Foram também confirmadas a existência e publicação de `index-2026-11-23-exams-complete` e `exams-app-2026-11-23-verification`. Os testes anteriores já incluíam `git bundle verify`, restauração e SHA-256 de retorno de assets selecionados; **esta auditoria de manifestos não substitui uma nova descarga e validação binária integral de todos os assets**.

No `exams-app`, a auditoria anterior passou em `git fsck --full`, conferiu a árvore TAR contra `dev`, todos os refs e arquivos das quatro branches e 3.870 objetos Git, sem detectar ponteiros LFS ou submódulos. Os dois logs de Actions do repositório foram posteriormente preservados e conferidos.

## Lacunas confirmadas

### P0 — notas privadas não estão integralmente no arquivo

O `notes-app` privado contém `main`, `dev`, `stag`, `firebase/file` e as três tags `v0.1.0`, `v0.2.0`, `v0.3.0` que **não estão preservadas como objetos/refs de um Git Bundle completo** no `exams-app-archive`. Existem apenas seus nomes e SHAs no inventário, o que não é backup.

Há três Releases originais de Notes com descrições, sem assets binários. Essas descrições não foram exportadas para o repositório de arquivo. O `GITHUB_TOKEN` do arquivo não lê automaticamente outros repositórios privados; é preciso conceder **acesso de leitura específico e revogável** ao Notes e escrita ao arquivo, sem expor tokens/cookies.

### P1 — metadados da plataforma GitHub fora do Git

Git Bundles preservam commits alcançáveis pelas refs exportadas, **não** preservam automaticamente descrições/comentários/revisões de PR, issues, discussões, metadados de runs, logs, artefatos expirados, Releases ou wiki.

Inventário observado na auditoria:

- `exams-app-old`: 161 PRs e aproximadamente 739 execuções de Actions;
- `exams-app-antigo-2`: 200 PRs, 88 issues independentes e aproximadamente 7.290 execuções de Actions;
- `shadcn-template`: 26 PRs, aproximadamente 169 execuções;
- `shadcn-firebase-template`: 65 PRs, aproximadamente 821 execuções;
- `notes-app`: 50 PRs e aproximadamente 1.130 execuções;
- `exams-app`: PR #1 e dois runs, com metadados e logs salvos.

Os números de Actions são contagens fornecidas pela API no momento da verificação; podem variar. As refs de PR que ainda existem no Git público foram preservadas pelo bundle `all-refs`, mas **não** seus textos e discussões da plataforma. Logs de CI antigos podem já estar expirados.

### P2 — fontes externas e facilidade de pesquisa

- O índice SQLite FTS5 cobre as 19 fontes preservadas, com mensagens de commit e nomes/caminhos históricos. **Não** indexa todas as versões completas dos textos nem descreve semanticamente imagens.
- Ponteiros Git LFS foram auditados no bundle de `exams-app`; não há comprovação exaustiva do mesmo tipo para todos os repositórios.
- Objetos Git já inacessíveis/pruned em upstream, recursos externos referenciados em documentos, wikis externas e assets expirados não podem ser considerados preservados só pelo `git bundle verify`.

## Recomendações e critério de conclusão

1. **Não excluir nenhuma origem ainda.** Preservar as quatro branches privadas e as três tags de `notes-app` num bundle verificado, com ref/SHA comparado e recuperação real de arquivo.
2. Exportar pelo menos metadados JSON paginados de issues, PRs, comentários e Releases dos demais repositórios; guardar logs e artefatos selecionados, com retenção e volume explícitos.
3. Fazer uma verificação binária independente de todos os bundles das releases prioritárias e detectar possíveis ponteiros LFS de todas as fontes.
4. Só declarar arquivamento completo após um manifesto de cobertura sem faltas, testes de restauração, SHA-256, e uma política explícita para itens fora do Git.

## Links

- [Repositório de arquivo](https://github.com/ianmaciel7/exams-app-archive)
- [Backup completo de exams-app](https://github.com/ianmaciel7/exams-app-archive/releases/tag/exams-app-2026-11-23-complete)
- [Backup all-refs público](https://github.com/ianmaciel7/exams-app-archive/releases/tag/archive-2026-11-23-all-refs)
- [Verificação dos 15 bundles antigos](../reports/embedded-bundles-audit.md)
- [Índice SQLite pesquisável](https://github.com/ianmaciel7/exams-app-archive/releases/tag/index-2026-11-23-exams-complete)

**Nenhuma branch ou repositório de origem foi apagado nesta verificação.**

## Adendo — progresso da preservação privada e metadados, 23/11/2026

A integração GitHub autenticada copiou diretamente, para
[inventory/notes-app/](../inventory/notes-app/README.md), as listas de 50 PRs,
50 registros de issues/PRs, 3 releases, 3 referências de tags,
37 submissões de review, 100 comentários inline,
10 comentários de conversa, 153 eventos de issues/PRs,
1.889 registros de arquivos alterados em PRs e **1.130 runs de Actions**
(em doze páginas de JSON). Essas cópias contêm **metadados**, não os objetos
Git faltantes nem os arquivos de logs e artifacts de CI.

Foi criada a automação privada
[archive-private-notes.yml](https://github.com/ianmaciel7/exams-app-archive/actions/workflows/archive-private-notes.yml),
mas sua execução comprovou a ausência do secret `NOTES_READ_TOKEN`.
O teste de sintaxe do script Python passou. O usuário precisa adicionar um token
fine-grained, somente de leitura, limitado ao repositório `notes-app` para que
a automação consiga clonar o histórico Git privado e salvar uma release com
validação de SHA, refs, tags e restauração.

A [auditoria externa de sete Git Bundles](../reports/PUBLIC-GIT-EXTERNALS.md)
examinou **30.098 objetos** e não encontrou ponteiros LFS nem submódulos;
também não encontrou repositórios Wiki Git acessíveis.

O workflow [export-public-platform-metadata.yml](https://github.com/ianmaciel7/exams-app-archive/actions/workflows/export-public-platform-metadata.yml)
foi iniciado para exportar metadados de plataforma dos sete repositórios públicos,
mas **não deve ser considerado concluído** até existir release final e manifesto
com checksums verificados. O limite da API Actions pode impedir exportação
integral em uma única execução; erros precisam permanecer documentados.

**Status atual:** a cobertura histórica **não é 100%**; não excluir as origens.
