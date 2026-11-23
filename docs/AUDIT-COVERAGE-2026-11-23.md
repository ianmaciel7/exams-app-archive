# Auditoria completa de cobertura — 23/11/2026

## Escopo e método

Fonte de verdade da auditoria: GitHub conectado, com inventário de SHA dos heads em [source-refs-2026-11-23.json](../inventory/source-refs-2026-11-23.json). A auditoria abrange **todos os nove repositórios acessíveis** (oito origens + o próprio arquivo), **71 branches** no momento da verificação e as três tags encontradas em `notes-app`.

A integridade dos bundles foi conferida na release privada por `git bundle verify`, comparação de SHA-256, comparação das refs e, em pelo menos um bundle de cada conjunto, download/validação de retorno. Os 15 bundles contidos no antigo repositório foram recuperados **da própria release privada**, sem depender das origens, e validados novamente.

## Cobertura atual

| Repositório | Visibilidade | Branches na origem | Cobertura de backup | Pendências |
|---|---|---:|---|---|
| [exams-app](https://github.com/ianmaciel7/exams-app) | Público | 4 | `main` e `dev` em bundle; a ref `claude/project-thread-o4dym1` aponta para ancestral de `dev` | A branch temporária `chore/consolidate-legacy-sources-20261123` (7 commits próprios) foi intencionalmente excluída para evitar duplicar milhares de snapshots públicos |
| [exams-app-old](https://github.com/ianmaciel7/exams-app-old) | Público | 6 | **6/6** no bundle completo | Nenhuma branch omitida |
| [exams-app-antigo-2](https://github.com/ianmaciel7/exams-app-antigo-2) | Público | 28 | **28/28** no bundle completo | Nenhuma branch omitida |
| [notes-app](https://github.com/ianmaciel7/notes-app) | Privado | 16 | **12/16** via bundles históricos `old` + `old-1` a `old-11`, validados e com SHA correspondente | Faltam `main`, `dev`, `stag`, `firebase/file` e tags `v0.1.0`, `v0.2.0`, `v0.3.0` |
| [shadcn-template](https://github.com/ianmaciel7/shadcn-template) | Público | 7 | **7/7** no bundle complementar, com todas as refs conferidas | Corrigido após auditoria |
| [shadcn-firebase-template](https://github.com/ianmaciel7/shadcn-firebase-template) | Público | 7 | **7/7** no bundle complementar, com todas as refs conferidas | Corrigido após auditoria |
| [fcc-responsive-web-design](https://github.com/ianmaciel7/fcc-responsive-web-design) | Público | 1 | **1/1** no bundle complementar | Fonte auxiliar, não é código de Exam App |
| [ianmaciel7](https://github.com/ianmaciel7/ianmaciel7) | Público | 1 | **1/1** no bundle complementar | Perfil GitHub; fonte auxiliar |
| [exams-app-archive](https://github.com/ianmaciel7/exams-app-archive) | Privado | 1 | É o **destino** (`main`), não uma origem | Evitar snapshot recursivo de si mesmo |

Observação: uma branch omitida pode ter commits alcançáveis a partir de outra ref já preservada, mas seu **nome de referência** não estará recriado dentro do bundle. É o caso da branch do Claude do `exams-app`; a branch `chore/consolidate-legacy-sources-20261123` foi intencionalmente deixada de fora por ser a cópia transitória criada nesta conversa, não a fonte original das informações.

## Releases verificadas

1. [archive-2026-11-23-initial](https://github.com/ianmaciel7/exams-app-archive/releases/tag/archive-2026-11-23-initial): cinco bundles dos projetos principais e quatro bundles `notes-app-old-*` destacados para acesso rápido. O bundle de `exams-app-antigo-2` também contém os **15 backups históricos** originais.
2. [archive-2026-11-23-audit-complements](https://github.com/ianmaciel7/exams-app-archive/releases/tag/archive-2026-11-23-audit-complements): versões completas de `shadcn-template` e `shadcn-firebase-template` incluindo as branches inicialmente omitidas; mais os dois repositórios auxiliares.

**Não são criadas branches antigas no repositório de arquivo.** Cada bundle guarda suas refs internamente. Checksums ficam em [manifests](../manifests/).

## Correção posterior — refs de PR inicialmente não incluídas

A auditoria por branches não era suficiente: os primeiros bundles exportavam apenas refs `heads`/`tags`. A indexação dos clones completos identificou commits adicionais alcançáveis por `refs/pull/*`, importantes para recuperar propostas não mescladas.

Foi publicada a release privada **[archive-2026-11-23-all-refs](https://github.com/ianmaciel7/exams-app-archive/releases/tag/archive-2026-11-23-all-refs)**, utilizando `git clone --mirror` + `git bundle create --all`. Todas as refs anunciadas pelos clones foram comparadas uma a uma por nome e SHA com o bundle final; foi feito também download e verificação de retorno de `exams-app-old.bundle`.

| Repositório público | Refs preservadas | Pull request refs |
|---|---:|---:|
| exams-app | 3 | 1 |
| exams-app-old | 167 | 161 |
| exams-app-antigo-2 | 234 | 206 |
| shadcn-template | 37 | 30 |
| shadcn-firebase-template | 78 | 71 |
| fcc-responsive-web-design | 1 | 0 |
| ianmaciel7 | 1 | 0 |
| **Total** | **521** | **469** |

O `exams-app` tinha cinco refs anunciadas no espelho. Foram deliberadamente removidas **somente do espelho temporário** a branch `chore/consolidate-legacy-sources-20261123` (uma cópia de migração, redundante) e `claude/project-thread-o4dym1` (antecessora de `dev`), resultando em três refs preservadas. As branches originais não foram apagadas.

**Para recuperar todo o histórico público anunciado pelo GitHub, a release `all-refs` passa a ser a fonte preferencial.** As duas releases anteriores continuam imutáveis como snapshots de auditoria.

## Testes feitos

- POC real com SQLite FTS5: 1.941 commits, 32.666 alterações de arquivos, 1.584 registros de imagens. Buscas por Firebase, grafo, QConcursos, Recall e termos parciais, com exemplos de recuperação de código e imagem histórica.
- [embedded-bundles-audit.md](../reports/embedded-bundles-audit.md): **15/15** bundles recuperados da release privada e aprovados no `git bundle verify`.
- Comparação das refs contidas nos 15 bundles com os SHA atuais das branches: **15/15 correspondências** (12 branches `old*` de Notes e três backups `backup/*` de Exams Old).
- Release complementar: todos os heads/tags dos dois templates e dos dois repositórios auxiliares comparados com os heads/tags do bundle; o asset `shadcn-template.bundle` também foi baixado e conferido por checksum e refs.

## Lacunas que continuam existindo

### Prioridade 1 — notes-app privado

A migração completa ainda depende de uma forma **autorizada** de copiar o histórico do repositório privado para o arquivo privado. O token padrão de GitHub Actions do `exams-app-archive` não tem automaticamente acesso ao repositório `notes-app`. A integração GitHub permite ler metadados e arquivos privados nesta conversa, mas não transfere essa credencial para GitHub Actions.

As quatro branches `main`, `dev`, `stag` e `firebase/file` e as três tags privadas precisam ser preservadas com seus objetos Git; registrar SHAs apenas no inventário não é backup. Não enfraquecer a visibilidade de nenhum repositório e não copiar tokens/cookies privados. Uma opção posterior é conceder a uma automação específica acesso de leitura ao `notes-app` e escrita à release privada, com credenciais de escopo mínimo e revogáveis.

### Prioridade 2 — pesquisa completa para IA

O índice de **prova de conceito** cobre `exams-app-old`, `exams-app-antigo-2` e `notes-app-old-10`. O fato de outros bundles estarem preservados não significa que já estejam pesquisáveis no SQLite. Expandir o indexador a todos os bundles apenas se as consultas de referência mostrarem benefício, com métricas de RAM, latência, recall e custo de tokens.

### Prioridade 3 — metadados fora do Git

Bundles não incluem automaticamente issues, comentários de PR, discussões, ações, releases de origem, artefatos de CI, wiki separada ou binários Git LFS externos. Fazer inventário e exportação seletiva quando houver material valioso. Não incluir segredos ou dados pessoais desnecessários.

## Decisão

- Preservar originais intactos; **não apagar branches ou repositórios** nesta fase.
- Não substituir o arquivo por copias textuais sem histórico.
- Manter `exams-app-archive` privado e com apenas `main`.
- Material histórico de 12 branches antigas de Notes **não foi esquecido**: os 12 HEADs foram recuperados dos bundles embutidos no backup de `exams-app-antigo-2`.
- **Pendente real:** quatro branches correntes + três tags de `notes-app`, e expansão do índice de busca.

## Retificação — preservação integral do `exams-app` (23/11/2026)

A exclusão anterior das branches `claude/project-thread-o4dym1` e
`chore/consolidate-legacy-sources-20261123` foi revertida em uma **nova release imutável**:
[exams-app-2026-11-23-complete](https://github.com/ianmaciel7/exams-app-archive/releases/tag/exams-app-2026-11-23-complete).

O backup foi gerado de um espelho Git do repositório público e inclui agora **as quatro
branches originais e a referência de PR**, com comparação exata de ref e SHA. Foram restauradas
as quatro branches para validar commits e contagem de arquivos. O bundle publicado foi
baixado e conferido novamente por SHA-256.

| Branch | Arquivos na árvore | Imagens/PDF |
|---|---:|---:|
| `main` | 1 | 0 |
| `dev` | 509 | 360 |
| `claude/project-thread-o4dym1` | 309 | 260 |
| `chore/consolidate-legacy-sources-20261123` | 2.837 | 811 |

Além de Git Bundle, a release inclui: snapshot extraível de `dev`, catálogo completo
de caminhos e blobs de cada branch, metadados públicos do PR #1 (incluindo 2.328 arquivos
alterados, comentários e revisões retornados pela API), manifestos e checksums.
A fonte possui 1 PR fechado, 0 releases e nenhuma issue separada do PR; a wiki remota
não pôde ser clonada (repositório wiki ausente ou indisponível). Git LFS externo ainda
não foi auditado exaustivamente.

**A release acima substitui, para `exams-app`, a versão anterior que excluía duas refs.**
Os backups anteriores seguem preservados como histórico de auditoria. A consolidação dos
demais repositórios e o backup integral do `notes-app` privado são questões separadas.
