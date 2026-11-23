# Exams App — verificação de preservação completa

Fonte: https://github.com/ianmaciel7/exams-app
Destino (privado): https://github.com/ianmaciel7/exams-app-archive

**Todas as quatro branches e todos os objetos alcançáveis pelas refs anunciadas no Git foram exportados.**
As refs originais permanecem no bundle; não foram criadas branches no repositório de arquivo.

| Branch | HEAD | Arquivos | Imagens/PDF |
|---|---|---:|---:|
| `chore/consolidate-legacy-sources-20261123` | `b67c7c1e36e0` | 2837 | 811 |
| `claude/project-thread-o4dym1` | `c6d50b2096e3` | 309 | 260 |
| `dev` | `dfc277cd9823` | 509 | 360 |
| `main` | `70247f40f149` | 1 | 0 |

- Referências Git no backup: **5**, incluindo 1 refs de PR.
- Issues (incluindo PR): 1; PRs: 1; releases de origem: 0.
- Wiki: wiki repository is empty, absent or inaccessible.
- LFS: no root .gitattributes found on the four branch heads; other pointers not exhaustively checked.

## Como recuperar

Acesse a [release privada](https://github.com/ianmaciel7/exams-app-archive/releases/tag/exams-app-2026-11-23-complete).

- `exams-app-all-refs.bundle` — backup Git com todas as branches, histórico e refs de PR.
- `exams-app-dev-snapshot.tar.gz` — arquivos da branch dev em arquivo extraível.
- `BRANCH-FILES.json` — todos os caminhos, tamanhos e hashes por branch.
- `GITHUB-METADATA.json` — issues, PRs, comentários, eventos, revisões e arquivos alterados.
- `MANIFEST.json` e `SHA256SUMS.txt` — rastreabilidade e checksums.

## Integridade

- `git bundle verify` aprovado.
- Todas as refs e seus commits no bundle conferem com o espelho.
- As quatro branches foram restauradas e tiveram heads e quantidade de arquivos comparados.
- O asset publicado foi baixado novamente e validado por SHA-256 e refs.

Arquivos grandes são armazenados em releases, e não duplicados no histórico Git do arquivo.
A presença de todos os arquivos dentro de Git Bundle não significa que cada arquivo
apareça individualmente na árvore do GitHub; consulte a lista em `inventory/`
ou extraia o snapshot para navegar pelos arquivos.

Metadados GitHub fora do Git, LFS remoto e objetos já eliminados do upstream podem
exigir preservação separada e não estão incluídos na garantia de Git Bundle.
