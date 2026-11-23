# Como encontrar e recuperar informações antigas

O `exams-app-archive` é privado. Ele preserva metadados de origem e todos os objetos
alcançáveis pelas refs anunciadas no espelho dos sete repositórios públicos, incluindo
refs de PR. As 12 branches `notes-app-old*` foram preservadas dentro de bundles
históricos. O histórico privado corrente de Notes permanece parcial.

## Nível 1 — Pesquisa rápida no ChatGPT / GitHub

Leia apenas o relatório mais relevante, sem colocar o banco no contexto do agente:

- [Relatório de cobertura](AUDIT-COVERAGE-2026-11-23.md)
- [Índice completo — fontes e consultas](../reports/FULL-INDEX.md)
- [Resultado da prova inicial](../reports/POC.md)
- [Manifests de bundles](../manifests/ALL-REFS.md)
- [Auditoria dos 15 backups antigos](../reports/embedded-bundles-audit.md)

## Nível 2 — Pesquisa no SQLite FTS5 completo

Em um terminal com `gh` autenticado e Python 3:

```powershell
gh release download index-2026-11-23-all-refs --repo ianmaciel7/exams-app-archive --pattern full-index.sqlite.gz --dir .cache/archive
python -c "import gzip,shutil;shutil.copyfileobj(gzip.open('.cache/archive/full-index.sqlite.gz','rb'),open('.cache/archive/full-index.sqlite','wb'))"
python scripts/archive_index.py --db .cache/archive/full-index.sqlite stats
python scripts/archive_index.py --db .cache/archive/full-index.sqlite search "fsrs"
python scripts/archive_index.py --db .cache/archive/full-index.sqlite search "qconcursos"
python scripts/archive_index.py --db .cache/archive/full-index.sqlite search "capacit"
python scripts/archive_index.py --db .cache/archive/full-index.sqlite images --deleted-only --limit 10
```

O arquivo completo ocupa cerca de **37,33 MiB** e o download cerca de **5,88 MiB**
(23/11/2026). O índice contém **mensagens de commit e caminhos históricos**:
não é um modelo semântico sobre todo o texto das versões dos arquivos.
Os resultados incluem o nome da fonte e o commit SHA.

## Nível 3 — Restaurar código, documentos e imagens

Para versões antigas de `exams-app-antigo-2`, use o bundle **completo com PR refs**:

```powershell
gh release download archive-2026-11-23-all-refs --repo ianmaciel7/exams-app-archive --pattern exams-app-antigo-2.bundle --dir .cache/archive
git clone --mirror .cache/archive/exams-app-antigo-2.bundle .cache/archive/old2.git
python scripts/archive_index.py recover --repo .cache/archive/old2.git --sha 65ce2ab7ac95e8fc4e1be998eb0aa593049bf2c8 --path prototypes/board-exam-app/assets/issue68_graph_toolbar_1366.png --output .cache/recovered/issue68_graph_toolbar_1366.png
```

Essa imagem histórica foi recuperada em teste real, com hash de conteúdo e hash
Git verificados. A recuperação funciona com binários e documentos também.

Para código do Notes App antigo, baixe o bundle individual da release inicial:

```powershell
gh release download archive-2026-11-23-initial --repo ianmaciel7/exams-app-archive --pattern notes-app-old-10.bundle --dir .cache/archive
git clone --mirror .cache/archive/notes-app-old-10.bundle .cache/archive/notes-old-10.git
python scripts/archive_index.py recover --repo .cache/archive/notes-old-10.git --sha cabcec2e8227fc7f06aa5c9c5afcc0e8944802c6 --path src/domain/recall.ts --output .cache/recovered/recall.ts
```

Outros 11 bundles antigos de Notes estão contidos no backup Git do
`exams-app-antigo-2` e foram verificados individualmente. Seus SHAs originais
podem ser encontrados em [embedded-bundles-audit.json](../reports/embedded-bundles-audit.json).

## Rastreamento e limitações

- Os objetos históricos vivem nas releases; o SQLite é **reconstruível** e
  não armazena cópias de todos os blobs.
- O backup principal `all-refs` inclui refs de PR que os primeiros backups
  `--branches --tags` deixaram de fora. Prefira a release `all-refs` para
  recuperar o histórico público mais completo.
- `git bundle verify` comprova integridade do bundle recebido, mas não garante
  que objetos já inacessíveis no servidor tenham sido recuperados.
- Os quatro branches atuais `main`, `dev`, `stag`, `firebase/file` do
  `notes-app` privado e suas três tags ainda não foram incorporados integralmente.
- Issues, descrições e comentários de PRs, metadados de CI, Git LFS externo,
  discussões e releases de origem não fazem parte automaticamente de Git Bundles.
  Faça exportação específica antes de apagar repositórios originais.
- Não executar código antigo sem revisão, nem incorporar automaticamente
  implementações obsoletas ao aplicativo atual.
