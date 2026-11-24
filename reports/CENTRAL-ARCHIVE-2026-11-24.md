# Centralização final — 24/11/2026

## Resultado

Os complementos anteriormente exclusivos dos repositórios de origem foram preservados em quatro releases do arquivo central. O destino permanece público; os novos arquivos são criptografados com GnuPG (AES-256). O teste local baixou novamente cada ciphertext do destino, comparou SHA-256 e descriptografou o TAR, comparando seu SHA-256 com o original. As quatro releases estão publicadas, não em rascunho.

| Release | Bytes do ciphertext | SHA-256 |
|---|---:|---|
| [Git atual](https://github.com/ianmaciel7/exams-app-archive/releases/tag/encrypted-current-git-20261124-central) | 310241460 | `8969619d5685ca0d38b709668a28567c9b08fc7b1f9a74b2f002c62bf7bf3be1` |
| [Metadados atuais](https://github.com/ianmaciel7/exams-app-archive/releases/tag/encrypted-current-platform-20261124-central) | 29071545 | `67bbc0b160aeecf4b73320635781ee0d6208e9fd6a13d4d450040e3a1231acda` |
| [Releases das origens](https://github.com/ianmaciel7/exams-app-archive/releases/tag/encrypted-source-releases-20261124-central) | 645017784 | `4927b15ed6ea4b53ee9e1e665a1ad9b10f6398636c08d70ef49bc7c80d9e244f` |
| [Evidências recentes](https://github.com/ianmaciel7/exams-app-archive/releases/tag/encrypted-recent-evidence-20261124-central) | 493383864 | `7805051cf44a0eabaafd02b72514ece12ae6fe62f478784c6b38e74b5265e692` |

Total: 1.477.714.653 bytes criptografados. A conferência final comparou todas as 52 releases e os IDs/tamanhos dos 102 assets com a origem. Os espelhos Git restaurados passaram em fsck e a comparação final com as refs anunciadas confirmou 123/123 refs do Notes e 5/5 do Exams. Foram recuperados 84/84 arquivos de evidências recentes, incluindo os que inicialmente falharam. Os manifestos internos dos pacotes registram origem e integridade.

A reconciliação histórica dos logs anterior também está completa: 23/23 lotes, 10.156 IDs únicos inventariados, 9.515 ZIPs salvos, 641 indisponíveis na origem, zero registros aguardando retry. [Auditoria anterior](https://github.com/ianmaciel7/notes-app/actions/runs/45476513728) (link de proveniência, não requisito para restaurar os arquivos copiados).

## Recuperação sem depender das origens

1. Baixe `archive.tar.gpg` da release desejada diretamente do arquivo central.
2. Confira SHA-256 usando a tabela acima.
3. Em ambiente local confiável, execute `gpg --output archive.tar --decrypt archive.tar.gpg` e forneça a frase secreta local no prompt, sem registrá-la em comandos ou logs.
4. Examine o TAR com `tar -tf archive.tar` e extraia em diretório privado. Use os manifestos internos para verificar os arquivos. Os bundles Git podem ser restaurados com `git clone --mirror caminho.bundle restaurado.git` e verificados com `git -C restaurado.git fsck --full`.

A frase secreta foi criada no computador do proprietário e não foi enviada ao GitHub. O proprietário precisa manter uma cópia segura da frase secreta independente do computador e do GitHub; sem ela os novos pacotes não podem ser recuperados. Não envie a chave para a issue, release ou repositório público.

## Limites

Este resultado confirma a centralização do material inventariado e recuperado, não a recuperação de informações já apagadas/expiradas, anexos externos não inventariados ou serviços externos. Não há nova certificação de segurança de todos os dados anteriormente publicados. Os plugins que consultam índices via Notes ainda podem precisar de adaptação para consultar os pacotes locais descriptografados; preservar bytes não equivale a manter os serviços ativos. Nenhuma exclusão das duas origens restantes foi executada nesta etapa.
