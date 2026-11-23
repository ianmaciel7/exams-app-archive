#!/usr/bin/env python3
"""Audit and readiness safety gate for branch and repository cleanup across source repositories."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "inventory/source-refs-2026-11-23.json"
REPORT_MD_PATH = ROOT / "reports/BRANCH-CLEANUP-READINESS.md"
REPORT_JSON_PATH = ROOT / "reports/BRANCH-CLEANUP-READINESS.json"

CATEGORIES = [
    "ativa/infraestrutura",
    "contém alterações únicas",
    "integrada (incluindo squash/cherry-pick)",
    "backup histórico",
    "temporária concluída",
    "temporária bloqueada",
    "desconhecida"
]

# Archive specific branches observed on 2026-11-23
ARCHIVE_AUX_BRANCHES = [
    {
        "repo": "ianmaciel7/exams-app-archive",
        "branch": "main",
        "sha": "380daee36d54811f00ebcb1fa07bb918033f260e",
        "category": "ativa/infraestrutura",
        "evidence": "Branch padrao do arquivo, fonte de scripts, testes e workflows",
        "proposed_action": "Preservar",
        "blockers": "Infraestrutura ativa; nunca excluir"
    },
    {
        "repo": "ianmaciel7/exams-app-archive",
        "branch": "archive-search-queries",
        "sha": "d475d53b50b5416555359d7ade55bf0be24f6b13",
        "category": "ativa/infraestrutura",
        "evidence": "Workflow archive-private-search.yml utiliza como fila de requests/results privados",
        "proposed_action": "Preservar com politica de retencao de dados processados",
        "blockers": "Infraestrutura ativa de consulta privada; nao excluir"
    },
    {
        "repo": "ianmaciel7/exams-app-archive",
        "branch": "feat/archive-pages-codex-plugin-20261123",
        "sha": "2feb3f9327fcd2f1fd30254538b7f6079d5eebee",
        "category": "contém alterações únicas",
        "evidence": "PR #1 mesclado, mas a branch tem arquivo ausente na main: .github/workflows/export-archive-for-offsite.yml (verificado com git diff --name-status)",
        "proposed_action": "Revisar e integrar o workflow exclusivo via PR (relacionado a issue #4) antes de qualquer limpeza",
        "blockers": "Alteracao unica nao integrada; proibido excluir"
    },
    {
        "repo": "ianmaciel7/exams-app-archive",
        "branch": "feat/chatgpt-native-archive-search-20261123",
        "sha": "1869d0628426225590845ff226a7c9d7ccafc93a",
        "category": "desconhecida",
        "evidence": "PR #2 mesclado e nenhum arquivo exclusivo na branch, porem equivalencia por patch/commit nao foi comprovada",
        "proposed_action": "Comparar patch-id dos commits com a main antes de classificar",
        "blockers": "Equivalencia nao comprovada; bloqueado por padrao"
    },
    {
        "repo": "ianmaciel7/exams-app-archive",
        "branch": "notes-private-import",
        "sha": "019c67284606c7c47029154d71b27101914a44da",
        "category": "temporária bloqueada",
        "evidence": "Contem TRANSFER-MANIFEST.json e partes part-*.b64 da transferencia de Notes privado",
        "proposed_action": "Concluir recebimento de todas as partes, validar bundle e release antes de limpar",
        "blockers": "Transferencia de backup pendente (Issue #3); proibido excluir"
    }
]


def audit_branches():
    if not INVENTORY_PATH.is_file():
        raise RuntimeError(f"Inventory file not found: {INVENTORY_PATH}")

    with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    # First add archive repository branches
    for item in ARCHIVE_AUX_BRANCHES:
        rows.append(item)

    # Process all repositories from inventory
    for repo_info in data.get("repositories", []):
        repo_name = repo_info.get("repo", repo_info.get("name"))
        branches = repo_info.get("branches", {})

        if repo_name == "ianmaciel7/exams-app-archive":
            continue

        for branch_name, sha in branches.items():
            if repo_name == "ianmaciel7/notes-app":
                if branch_name.startswith("old"):
                    category = "backup histórico"
                    evidence = f"Preservada em release de bundles internos verificados ({branch_name})"
                    proposed_action = "Preservar; manter copia no acervo"
                    blockers = "Nao excluir origem sem copia independente externa confirmada"
                else:
                    category = "temporária bloqueada"
                    evidence = f"Branch principal ou ativa de {repo_name}; objetos pendentes no arquivo"
                    proposed_action = "Bloquear qualquer exclusao; concluir transferencia da issue #3"
                    blockers = "Aguardando conclusao da transferencia (Issue #3) e autorizacao explicita"
            elif repo_name in ("ianmaciel7/exams-app", "ianmaciel7/fcc-responsive-web-design", "ianmaciel7/ianmaciel7"):
                category = "ativa/infraestrutura"
                evidence = f"Repositorio ou branch em producao/ativo ({branch_name})"
                proposed_action = "Preservar integralmente; fora do escopo de exclusao"
                blockers = "Repositorio ativo, nao e alvo de exclusao"
            elif repo_name in ("ianmaciel7/exams-app-antigo-2", "ianmaciel7/exams-app-old"):
                if branch_name in ("main", "dev"):
                    category = "backup histórico"
                    evidence = f"Bundle Git preservado em archive-2026-11-23-all-refs, CI e metadados arquivados"
                    proposed_action = "Candidato a arquivamento/exclusao somente apos copia externa e gate"
                    blockers = "Copia externa independente pendente; requer aprovacao manual expressa"
                elif branch_name.startswith("backup/") or branch_name.startswith("claude/") or branch_name.startswith("chore/") or branch_name.startswith("feat/") or branch_name.startswith("fix/") or branch_name.startswith("docs/"):
                    category = "backup histórico"
                    evidence = f"Commit preservado no bundle e inventario de refs 2026-11-23"
                    proposed_action = "Candidato a arquivamento/exclusao somente apos copia externa e gate"
                    blockers = "Copia externa independente pendente; requer aprovacao manual expressa"
                else:
                    category = "backup histórico"
                    evidence = f"Ref inventariada em archive-2026-11-23-all-refs"
                    proposed_action = "Avaliar apos consolidacao externa"
                    blockers = "Requer copia externa independente e aprovacao manual"
            elif repo_name in ("ianmaciel7/shadcn-template", "ianmaciel7/shadcn-firebase-template"):
                if branch_name == "main":
                    category = "backup histórico"
                    evidence = "Head preservado em bundle publico e CI arquivado"
                    proposed_action = "Candidato a arquivamento somente leitura"
                    blockers = "Copia externa independente pendente; requer aprovacao manual"
                else:
                    category = "backup histórico"
                    evidence = f"Branch auxiliar/dependabot preservada em bundle de refs"
                    proposed_action = "Candidata a remocao apos copia externa independente"
                    blockers = "Requer copia externa independente e aprovacao manual"
            else:
                category = "desconhecida"
                evidence = "Ref sem classificacao previa documentada"
                proposed_action = "Inspecionar antes de qualquer alteracao"
                blockers = "Classificacao desconhecida; bloqueado por seguranca"

            rows.append({
                "repo": repo_name,
                "branch": branch_name,
                "sha": sha,
                "category": category,
                "evidence": evidence,
                "proposed_action": proposed_action,
                "blockers": blockers
            })

    return rows


def generate_markdown_report(rows):
    lines = [
        "# Relatório de Prontidão e Auditoria de Branches (Branch Cleanup Readiness)",
        "",
        "Data de auditoria: 2026-11-23.",
        "",
        "> [!IMPORTANT]",
        "> Regra Mandatória de Segurança: **Nenhuma branch ou repositório de origem é excluído automaticamente.**",
        "> Branches ativas, ramos de infraestrutura de consulta privada e transferências de backup em andamento estão bloqueadas por padrão.",
        "",
        "## Resumo por Categoria",
        ""
    ]

    counts = {cat: 0 for cat in CATEGORIES}
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1

    lines.append("| Categoria | Quantidade | Ação Geral |")
    lines.append("| --- | --- | --- |")
    lines.append(f"| `ativa/infraestrutura` | {counts['ativa/infraestrutura']} | Preservar; bloqueio permanente de exclusao |")
    lines.append(f"| `temporária bloqueada` | {counts['temporária bloqueada']} | Bloqueada aguardando conclusao de transferencias |")
    lines.append(f"| `backup histórico` | {counts['backup histórico']} | Preservado em bundles/releases; exclusao bloqueada sem copia externa |")
    lines.append(f"| `integrada (incluindo squash/cherry-pick)` | {counts['integrada (incluindo squash/cherry-pick)']} | Elegivel para limpeza de branches locais/remotas apos aprovacao |")
    lines.append(f"| `contém alterações únicas` | {counts['contém alterações únicas']} | Bloqueada; exige integracao previa ou confirmacao de backup |")
    lines.append(f"| `temporária concluída` | {counts['temporária concluída']} | Elegivel para limpeza com aprovacao |")
    lines.append(f"| `desconhecida` | {counts['desconhecida']} | Bloqueada por seguranca |")
    lines.append(f"| **Total de Branches Auditadas** | **{len(rows)}** | **Bloqueio padrao ativado** |")
    lines.append("")
    lines.append("## Inventário Completo por Repositório e Branch")
    lines.append("")
    lines.append("| Repositório | Branch | SHA | Classificação | Evidência | Ação Proposta | Bloqueios |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")

    for r in rows:
        short_sha = r["sha"][:10] if len(r["sha"]) >= 10 else r["sha"]
        lines.append(
            f"| `{r['repo']}` | `{r['branch']}` | `{short_sha}` | `{r['category']}` | "
            f"{r['evidence']} | {r['proposed_action']} | {r['blockers']} |"
        )

    lines.append("")
    lines.append("## Gate Automático de Não-Exclusão")
    lines.append("")
    lines.append("1. **Branches Ativas e Infraestrutura**: `main`, `dev`, `archive-search-queries` nunca podem ser apagadas.")
    lines.append("2. **Transferências Pendentes**: `notes-private-import` e branches de `notes-app` exigem término do fluxo da issue #3 e verificação de integridade antes de qualquer limpeza.")
    lines.append("3. **Repositórios Ativos**: `exams-app` e `notes-app` são projetos correntes fora do escopo de exclusão.")
    lines.append("4. **Cópia Externa Obrigatória**: Nenhum repositório antigo (`exams-app-antigo-2`, `exams-app-old`, etc.) pode ser removido sem cópia independente comprovada fora do GitHub.")
    lines.append("5. **Aprovação Explícita**: Somente o proprietário pode autorizar remoção de refs ou repositórios.")
    lines.append("")

    return "\n".join(lines)


def evaluate_safety_gate(repo, branch, rows):
    """Evaluates whether a branch can be safely deleted. Returns (can_delete, reason)."""
    match = next((r for r in rows if r["repo"] == repo and r["branch"] == branch), None)
    if not match:
        return False, f"Branch '{branch}' in '{repo}' is unknown or not audited."

    if match["category"] == "ativa/infraestrutura":
        return False, f"Branch '{branch}' is active infrastructure and must never be deleted."

    if match["category"] == "temporária bloqueada":
        return False, f"Branch '{branch}' is currently blocked: {match['blockers']}."

    if match["category"] == "contém alterações únicas":
        return False, f"Branch '{branch}' contains unique changes that are not yet reconciled."

    if repo in ("ianmaciel7/exams-app", "ianmaciel7/notes-app"):
        return False, f"Repository '{repo}' is an active project and cannot have active branches deleted."

    if match["category"] == "integrada (incluindo squash/cherry-pick)":
        return True, f"Branch '{branch}' is fully integrated and eligible for cleanup upon explicit user approval."

    # For historical backups, delete is forbidden without independent backup confirmation
    return False, f"Branch '{branch}' has blockers: {match['blockers']}."


def main():
    parser = argparse.ArgumentParser(description="Audit branches and evaluate cleanup readiness gate.")
    parser.add_argument("--check-gate", action="store_true", help="Run safety gate evaluation across all branches.")
    parser.add_argument("--repo", type=str, help="Repository name to check.")
    parser.add_argument("--branch", type=str, help="Branch name to check.")
    parser.add_argument("--generate-report", action="store_true", help="Generate reports/BRANCH-CLEANUP-READINESS.md.")
    args = parser.parse_args()

    rows = audit_branches()

    if args.generate_report or (not args.check_gate and not args.repo and not args.branch):
        md = generate_markdown_report(rows)
        REPORT_MD_PATH.write_text(md, encoding="utf-8")
        REPORT_JSON_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Generated report: {REPORT_MD_PATH} and {REPORT_JSON_PATH} ({len(rows)} branches audited).")

    if args.repo and args.branch:
        can_delete, reason = evaluate_safety_gate(args.repo, args.branch, rows)
        status = "ALLOWED (PENDING MANUAL APPROVAL)" if can_delete else "BLOCKED"
        print(f"[{status}] {args.repo}@{args.branch}: {reason}")
        if not can_delete:
            sys.exit(1)

    if args.check_gate:
        blocked = 0
        allowed = 0
        for r in rows:
            can_delete, _ = evaluate_safety_gate(r["repo"], r["branch"], rows)
            if can_delete:
                allowed += 1
            else:
                blocked += 1
        print(f"Gate Summary: {blocked} branches BLOCKED from deletion; {allowed} branches integrated/eligible.")


if __name__ == "__main__":
    main()
