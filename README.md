# Exams App Archive

**Arquivo privado, verificável e pesquisável de versões antigas do Exam App.**
Este repositório não é o aplicativo ativo; contém apenas ferramentas, manifestos
e índices. Históricos grandes ficam em **Git Bundles anexados a releases privadas**,
não em dezenas de branches.

## Comece por aqui

| Recurso | Para que serve |
|---|---|
| [Auditoria dos 9 repositórios](docs/AUDIT-COVERAGE-2026-11-23.md) | Cobertura e lacunas, com 71 branch heads inventariados |
| [Backup Git com refs de PR](https://github.com/ianmaciel7/exams-app-archive/releases/tag/archive-2026-11-23-all-refs) | Fonte **preferencial** para todo histórico público anunciado pelo GitHub |
| [Índice SQLite FTS5 completo](https://github.com/ianmaciel7/exams-app-archive/releases/tag/index-2026-11-23-all-refs) | Buscar rapidamente código histórico por commits e caminhos, sem embeddings |
| [Relatório da busca completa](reports/FULL-INDEX.md) | Resultados e métricas reais da indexação |
| [Verificação dos 15 bundles internos](reports/embedded-bundles-audit.md) | Preservação de 12 branches `notes-app-old*` e três backups Exams Old |
| [Guia prático de recuperação](docs/EXTRACTION-GUIDE.md) | Consultar índices e restaurar arquivos originais por commit + caminho |

## Escopo validado em 23/11/2026

- **7 repositórios públicos**: os cinco projetos principais (exams-app, exams-app-old,
  exams-app-antigo-2 e dois templates), mais dois repositórios auxiliares.
- **521 referências Git** preservadas nos espelhos públicos, incluindo **469 refs de PR**
  não incluídas na primeira tentativa. Duas branches transitórias de `exams-app`
  foram propositalmente omitidas.
- **12 versões históricas de Notes** (`old` e `old-1` a `old-11`) recuperadas
  a partir dos bundles internos; os **15/15 bundles** históricos tiveram integridade
  verificada e heads correspondentes às branches atuais.
- **19 fontes Git pesquisáveis** em um SQLite FTS5 reconstruído exclusivamente das
  releases privadas. Os dados somam **3.995 registros de commits**, **77.530 alterações**
  e **3.121 registros de imagens**. O SQLite tem aproximadamente 37,33 MiB, comprimido
  para 5,88 MiB. Esses registros podem compartilhar ancestrais e imagens.

**Pendente:** o backup integral do `notes-app` privado para `main`, `dev`, `stag`,
`firebase/file` e tags `v0.1.0`, `v0.2.0`, `v0.3.0`. O token do GitHub Actions
deste repositório não possui acesso automático para clonar outro repositório privado.
Não tornar o `notes-app` público para contornar isso.

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
