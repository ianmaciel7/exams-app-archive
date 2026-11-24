# Checklist de Backup Independente (Offsite) e Safety Gate de Exclusao

Data de referencia: 2026-11-24  
Politica de Seguranca: **Bloqueio por padrao (Block-by-default)**. Nenhuma exclusao e autorizada sem copia independente comprovada fora do GitHub e aprovacao explicita do proprietario.  
Regra de conformidade: **Zero Emoji Policy** aplicada rigorosamente em todo o documento e codigo.

---

## 1. Objetivo e Escopo

O objetivo deste checklist e eliminar o ponto unico de falha (SPOF) representado pela hospedagem exclusiva no GitHub, estabelecendo procedimentos rigorosos de auditoria para backups externos e implementando uma barreira tecnica automatizada (`safety gate`) que impede a exclusao acidental ou precipitada de repositorios antigos.

### Repositorios no Escopo (9 repositorios)

| Repositorio | Papel / Categoria | Status de Exclusao | Criterios para Exclusao |
|---|---|---|---|
| `exams-app-old` | Deprecated Candidate (Legado) | Bloqueado por padrao | Exige copia offsite verificada, restore comprovado e aprovacao manual |
| `exams-app-antigo-2` | Deprecated Candidate (Legado) | Bloqueado por padrao | Exige copia offsite verificada, 2.883 CI artifacts validados e aprovacao manual |
| `shadcn-template` | Deprecated Candidate (Legado) | Bloqueado por padrao | Exige copia offsite verificada, bundles auditados e aprovacao manual |
| `shadcn-firebase-template` | Deprecated Candidate (Legado) | Bloqueado por padrao | Exige copia offsite verificada, bundles auditados e aprovacao manual |
| `exams-app` | Active Infrastructure / Projeto Ativo | Bloqueio permanente | PROIBIDO EXCLUIR: Projeto em desenvolvimento continuo |
| `notes-app` | Active Infrastructure / Projeto Ativo | Bloqueio permanente | PROIBIDO EXCLUIR: Projeto corrente sob gestao de dados privados |
| `exams-app-archive` | Active Infrastructure / Repositorio Central | Bloqueio permanente | PROIBIDO EXCLUIR: Repositorio central de manifestos, ferramentas e logs |
| `fcc-responsive-web-design` | Auxiliary (Public Learning) | Bloqueado | Fora do escopo de exclusao; preservado como referencia publica |
| `ianmaciel7` | Auxiliary (Public Profile) | Bloqueado | Fora do escopo de exclusao; perfil publico do usuario |

---

## 2. Manifestos de Release e Cobertura de Artefatos

O arquivo consolida os seguintes manifestos em `manifests/`:

1. `release-2026-11-23.json`:
   - Release: `archive-2026-11-23-initial`
   - Bundles historicos com historico completo de branches para `exams-app`, `exams-app-old`, `exams-app-antigo-2`, `shadcn-template`, `shadcn-firebase-template`, e 4 snapshots do `notes-app`.
2. `release-2026-11-23-all-refs.json`:
   - Release: `archive-2026-11-23-all-refs`
   - Preservacao exaustiva de todas as refs Git (heads, tags e pull requests) com SHA-256 e contagem de refs.
3. `release-2026-11-23-audit-complements.json`:
   - Release: `archive-2026-11-23-audit-complements`
   - Complemento de branches secundarias e automacoes para templates e repositorios auxiliares.
4. `exams-app-complete-2026-11-23.json`:
   - Release: `exams-app-2026-11-23-complete`
   - Metadados completos do GitHub, `BRANCH-FILES.json` e snapshot tarball de desenvolvimento.
5. `notes-app-private-full.json`:
   - Release: `notes-app-2026-11-23-private-full`
   - Mapeamento completo de branches, tags e refs de PRs privadas.
6. `public-platform-metadata-2026-11-23.json`:
   - Release: `public-metadata-2026-11-23`
   - Metadados exportados de issues, PRs, workflow runs e registros de CI em arquivos ZIP.

---

## 3. Procedimentos de Verificacao Tecnica

### 3.1 Verificacao de Hashes SHA-256

Todo artefato exportado para armazenamento externo (AWS S3, Google Cloud Storage, disco local criptografado ou fita) deve ter seu hash SHA-256 validado bit a bit contra o manifesto correspondente.

Exemplo de comando manual:
```bash
sha256sum <arquivo_de_backup>
```

Via script automatizado:
```bash
python3 scripts/offsite_backup_checklist.py --manifests-dir manifests --verify-checksums /caminho/para/backup
```

### 3.2 Verificacao de Integridade de Git Bundles

Os bundles Git preservam objetos e referencias de forma autonoma. A validacao deve garantir que o arquivo nao foi corrompido durante transferencia:

Comandos Git:
```bash
# Verificar integridade estrutural e prerequisitos do bundle
git bundle verify exams-app-antigo-2.bundle

# Inspecionar cabecalhos e commits referenciados
git bundle list-heads exams-app-antigo-2.bundle
```

O bundle so e considerado integro quando `git bundle verify` retorna codigo 0 e registra mensagem indicando gravacao de historico completo ou lista de referencias intactas.

### 3.3 Teste de Restauracao Independente (Restore Test)

O teste de restauracao deve ser executado obrigatoriamente **sem acesso a rede ou conexao com o GitHub**, garantindo total independencia do provedor de origem:

1. Clonar a partir do bundle local para um diretorio isolado:
   ```bash
   git clone --mirror /caminho/para/backup/exams-app-antigo-2.bundle /tmp/restore-test.git
   ```
2. Verificar HEADs e integridade do repositorio bare:
   ```bash
   git --git-dir=/tmp/restore-test.git fsck --full --strict
   ```
3. Extrair uma amostra de codigo, uma imagem e um ZIP de evidencias de CI dos tars preservados.

---

## 4. Safety Gate de Exclusao: Regras de Bloqueio

A funcao `evaluate_safety_gate` em `scripts/offsite_backup_checklist.py` impoe uma politica de **bloqueio estrito por padrao**:

```text
Condicao Padrao: ready_for_deletion = FALSE
```

Para que qualquer repositorio legado passe para o estado `ELIGIBLE_PENDING_MANUAL_EXECUTION`, **todas as 6 condicoes cumulativas a seguir devem ser satisfeitas**:

1. **Classificacao de Deprecacao**: O repositorio deve pertencer ao grupo `DEPRECATED_CANDIDATES` (`exams-app-old`, `exams-app-antigo-2`, `shadcn-template`, `shadcn-firebase-template`). Repositorios de infraestrutura ativa (`exams-app`, `notes-app`, `exams-app-archive`) sao permanentemente bloqueados.
2. **Cobertura nos Manifestos**: Existencia de manifestos de release com hashes SHA-256 indexados cobrindo integralmente o repositorio.
3. **Destino Externo Confirmado Fora do GitHub**: O registro de copia externa deve especificar provedor independente (ex: bucket S3, cold storage criptografado) e proibir terminantemente URLs apontando para `github.com`.
4. **Hashes SHA-256 Verificados**: Confirmacao explicita de que os checksums foram calculados no destino externo e coincidem com os manifestos.
5. **Restore Independente Comprovado**: Evidencia documentada de restauracao bem-sucedida de codigo e evidencias sem consultar os servidores do GitHub.
6. **Autorizacao Explicita do Proprietario**: Consentimento manual formal do usuario `ianmaciel7`.

Se qualquer condicao faltar ou falhar, o status sera `BLOCKED`.

---

## 5. Uso do Utilitario CLI (`offsite_backup_checklist.py`)

O script `scripts/offsite_backup_checklist.py` oferece interface de linha de comando para auditoria rapida e integracao com pipelines CI/CD:

### 5.1 Inspecao de Manifestos e Safety Gate Padrao
```bash
python3 scripts/offsite_backup_checklist.py --manifests-dir manifests --check-safety-gate
```

### 5.2 Verificacao de Checksums em Diretorio de Backup
```bash
python3 scripts/offsite_backup_checklist.py --manifests-dir manifests --verify-checksums /caminho/para/backup
```

### 5.3 Saida Estruturada em JSON
```bash
python3 scripts/offsite_backup_checklist.py --manifests-dir manifests --check-safety-gate --json
```

### 5.4 Avaliacao de Repositorio Especifico com Registro Externo
```bash
python3 scripts/offsite_backup_checklist.py \
  --manifests-dir manifests \
  --repo exams-app-antigo-2 \
  --external-record config/offsite-receipt.json
```

Exemplo de formato para `config/offsite-receipt.json`:
```json
{
  "storage_location": "s3://secure-cold-storage/exams-app-archive-20261124/",
  "confirmed_date": "2026-11-24T12:00:00Z",
  "checksums_verified": true,
  "independent_restore_tested": true,
  "explicit_owner_approval": true,
  "approved_by": "ianmaciel7"
}
```

---

## 6. Recomendacoes para o Destino Externo

1. **Provedor**: Utilizar servico com durabilidade compativel com arquivamento de longo prazo (ex: AWS S3 com Object Lock ou Backblaze B2).
2. **Criptografia**: Criptografia em repouso com chave KMS gerenciada ou LUKS em unidades fisicas.
3. **Principio do Menor Privilegio**: As credenciais utilizadas para exportar o backup nao devem ter permissao para apagar arquivos no destino (`write-once, read-many`).
4. **Imutabilidade**: Ativar politicas de retencao temporal (retention period) para proteger contra ransomware ou exclusao acidental.

## Exportação local verificável (24/11/2026)

O script `scripts/offsite_export_and_restore.py` baixa as releases das seis origens principais e valida SHA-256 e tamanho de cada asset. Exige destino GitHub privado antes da transferência. Use um volume independente, criptografado ou sincronizado com um armazenamento privado. A execução com `--verify-only` não consulta GitHub e restaura os seis bundles e testa CRC dos 2.883 ZIPs de CI. A existência do script não prova a existência de uma segunda cópia.

```powershell
python scripts/offsite_export_and_restore.py --destination 'D:/Backups/exams-archive'
python scripts/offsite_export_and_restore.py --destination 'D:/Backups/exams-archive' --verify-only
```

Registre a evidência de persistência independente e o recibo `OFFSITE-RESTORE.json`; o script não autoriza exclusão.
