---
name: sync-bridge
description: Use when the user modifies, audits, updates or asks to synchronize the Exams Archive ChatGPT plugin and its GitHub source. Enforce two-way source mirroring, version checks, evidence of equality, and safe conflict handling for each material plugin change.
---

# Exams Archive — sincronização bidirecional controlada

## Identidade e limites

- Plugin ChatGPT privado: `plugins_6b04aaa9fd848191a24525011f76e2bb` (`exams-archive-native`). Ler pelo **Plugin Creator** autorizado.
- Espelho de fonte: `ianmaciel7/exams-app-archive@main:plugins/exams-archive-native/`. Ler/escrever pelo **GitHub conectado**.
- **NÃO confundir** com `plugins/exams-archive/`, o plugin Codex histórico `exams-archive` v0.1.x; preservá-lo com seus scripts e testes. Não substituir um pelo outro.
- `manifests/`, `inventory/`, `reports/`, `docs/`, releases e bundles do repositório são evidências/backup, não arquivos de plugin sincronizáveis. Nunca alterá-los só para "sincronizar".
- O repositório foi tornado público em 24/11/2026; Pages deve publicar apenas interface e evidências explicitamente revisadas. Nunca enviar dados privados ao espelho público. Não copiar segredos, URLs assinadas, tokens nem dados autenticados para o plugin/commits.

## Contrato de uso (em todas as modificações pertinentes)

1. **Antes** de qualquer alteração material no plugin ou nos arquivos de espelho, ler `get_plugin_files` (release ID, versão e caminhos), `get_repo` e o estado atual de `plugins/exams-archive-native/` em `main` (commit SHA); confrontar manifests e conteúdo. Verificar se já há PR em andamento.
2. **Mudança no ChatGPT → GitHub:** atualizar o plugin via Plugin Creator com `expected_release_id`, confirmar nova release lendo seus arquivos, gerar espelho byte-for-byte dos arquivos relevantes no repositório, comparar conteúdo/SHA e publicar a diferença em branch/PR (ou commit protegido por lease após autorização). Não atualizar backups nem o plugin Codex legado.
3. **Mudança no GitHub → ChatGPT:** buscar arquivos atuais de `plugins/exams-archive-native/` na branch escolhida, avaliar alterações com relação à release instalada, reconstruir um overlay ZIP com manifesto válido e publicar via Plugin Creator com release ID esperado. Ler novamente a versão instalada; registrar quais arquivos estão idênticos ao GitHub.
4. **Mudanças concorrentes:** comparar sempre o último baseline conhecido e os dois lados; se ambos alteraram o mesmo arquivo, **não usar last-write-wins**. Apresentar diff e resolução; jamais executar force push ou sobrescrever uma release atualizada em paralelo.
5. **Após sincronizar:** comparar caminhos e hashes de conteúdo de `plugin.json`, `.codex-plugin/plugin.json`, `README.md`, `agents/`, `skills/` e arquivos compartilhados. Informar versão, release ID, commit GitHub, arquivos sincronizados e pendências; não afirmar 'em sincronia' se o espelho está apenas numa PR pendente.
6. **Duas vias não significam webhook autônomo:** este plugin de skills não possui serviço de escuta nem endpoint de publicação automática. Não alegar que commits GitHub instalam releases sozinhos ou que atualizações no plugin criam commits sozinhas. Executar o protocolo durante operações pelo ChatGPT; para execução contínua exige infraestrutura e credenciais oficiais a validar.

## Política de atualização

- Preferir PR revisável para alterações não triviais. Caminhos do archive que guardam evidências e história permanecem intactos.
- Nunca remover um arquivo do plugin só porque está ausente no espelho antigo; a primeira sincronização é uma **migração aditiva** com comparação explícita.
- Editar sempre a versão semântica nos dois manifests; versões e conteúdos divergentes devem ser marcados como drift.
- Não depender de computador local nem usar credenciais expostas na conversa. Só ferramentas GitHub e Plugin Creator conectadas.
- Em caso de falha num dos lados, manter o outro íntegro, relatar a divergência e fornecer a operação segura para completar depois.

## Pacote multiagente v0.7.0

- A fonte canônica de código do plugin é `ianmaciel7/exams-app-archive@main:plugins/exams-archive-native/`, com manifests nativos de quatro clientes. Modificações por qualquer agente devem ser propostas ao GitHub como PR validada. **Não atualizar cópias concorrentes como fonte independente**.
- O CLI FTS5 histórico agora também está neste pacote em `scripts/archive_query.py`, e a skill `archive-search` descreve o uso local com autenticação `gh`. No ChatGPT sem executor local, usar GitHub conectado e leitura GitHub já documentada (não escrever queries privadas em branch pública).
- Toda release ChatGPT deve ser gerada da árvore canônica aprovada. Comparar hash byte a byte de cada arquivo de origem; salvar a release no registro `.sync-state.json` externo ao pacote. Plugin Creator não fornece atualização automática em contas pessoais.
- Não presumir que claude/agy/codex estão instalados ou que uma atualização Git instala no usuário sem refresh. CI estática não é teste end-to-end de cliente.

- O pacote 0.7.0 adiciona a skill `component-explorer` e a CLI `components` em paridade com a fonte canônica. Os módulos `scripts/component_catalog.py` e `scripts/archive_mcp.py` permanecem na raiz do checkout; a instalação do plugin de skills não instala um MCP local ou remoto automaticamente.
