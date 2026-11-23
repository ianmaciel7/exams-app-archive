# Exams App Archive

**Repositório privado para preservação e pesquisa de versões históricas do Exam App.**
O aplicativo ativo não está neste repositório. Arquivos antigos nunca devem ser
copiados por cima do projeto atual sem análise e testes.

## Prova de conceito (Git + SQLite FTS5)

Este repositório contém um indexador histórico leve, apenas com Python 3,
SQLite FTS5 e Git. Sem embeddings, banco vetorial, serviços pagos ou MCP novo.

A primeira execução automatizada avalia:

1. `exams-app-old` — repositório público e sua história de commits/branches;
2. `exams-app-antigo-2` — protótipos, imagens e histórico amplo;
3. `notes-app-old-10.bundle` — backup histórico extraído do segundo repositório.

O relatório e o índice ficam em [`reports/`](./reports/POC.md) após a execução.
A busca funciona por assuntos de commit e nomes históricos de arquivos, inclusive
arquivos removidos. A recuperação usa SHA + caminho diretamente dos objetos Git.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/run_poc.py
python3 scripts/archive_index.py --db reports/archive-index.sqlite search "grafo"
python3 scripts/archive_index.py --db reports/archive-index.sqlite images --deleted-only
```

**Importante:** a primeira execução testa extração e cria índice reconstruível;
**não** copia automaticamente todos os repositórios nem seus `.bundle` para
GitHub. A história original ainda depende das fontes até que seja migrada e
verificada com uma etapa de preservação separada. Não descartar repositórios
originais antes disso.

## Regras de preservação

- Manter histórico e documentação com origem, branch, commit SHA e hash.
- Manter o destino privado; `notes-app` e seus históricos podem conter dados privados.
- Não criar dezenas de branches transitórias neste arquivo.
- Para referências visuais, manter o binário original recuperável e pesquisar
  imagens removidas, não somente as que aparecem em `dev`.
- Evitar reindexar conteúdo já validado; adicionar índice incremental somente
  após prova de ganho real.
- Não expor servidor MCP até que exista necessidade comprovada. O GitHub MCP
  conectado já lê relatórios e scripts desse repositório.

## Limitações conhecidas

GitHub Actions executa com `GITHUB_TOKEN` deste repositório, que não pode clonar
automaticamente `notes-app` privado sem uma autorização de acesso entre
repositórios. O bundle histórico já presente no projeto antigo permite validar
uma parte do histórico, mas não comprova cobertura completa.

## Organização

- `scripts/archive_index.py` — indexador e busca/recuperação pela CLI.
- `scripts/run_poc.py` — prova executada contra fontes Git reais.
- `tests/test_archive_index.py` — testes determinísticos, incluindo imagem removida.
- `reports/` — inventário e evidências da execução, inclusive SQLite FTS5.
- `sources/` — reservado para futuros backups Git verificados e aprovados.