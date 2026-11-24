# Consolidar releases sem tornar o arquivo privado

O destino permanece público. O script `scripts/consolidate_encrypted_releases.py` cria um TAR com os assets originais e metadados das releases de Notes e Exams, criptografa com age, verifica a descriptografia local, publica somente o ciphertext e confere o download e a descriptografia novamente antes de publicar a release.

## Execução

Em terminal confiável com Python 3.11+, GitHub CLI autenticado (leitura das origens e escrita no destino), age e armazenamento temporário criptografado:

```sh
python scripts/consolidate_encrypted_releases.py
python scripts/consolidate_encrypted_releases.py --apply
```

Escolha uma frase secreta forte no prompt do age e guarde-a fora dos repositórios. Não coloque a frase secreta em commits, logs, argumentos, chat ou Actions. A perda da frase secreta impede a recuperação. Não execute o script em runner público.

## Recuperação

```sh
gh release download TAG -R ianmaciel7/exams-app-archive --pattern source-releases.tar.age
age -d -o source-releases.tar source-releases.tar.age
tar -tf source-releases.tar
```

Compare os hashes com os registros de cada release antes de considerar a restauração concluída. Extraia o TAR somente em diretório privado. O script não executa nenhuma exclusão.

## Aceite pendente

- Executar a migração real e confirmar o download e a descriptografia do ciphertext publicado.
- Comparar a cobertura de refs Git atuais e os metadados não incluídos nas releases com os backups existentes.
- Validar a restauração sem acesso às origens.
- Manter a frase secreta recuperável independentemente do GitHub.
- Não excluir origens antes de confirmar a cobertura e a recuperação.

Este procedimento foi preparado, não executado contra as releases reais. A consulta ao GitHub confirmou 52 releases e 102 assets de Notes em 24/11/2026; as releases são um complemento aos backups existentes, não uma prova independente de toda a cobertura histórica.
