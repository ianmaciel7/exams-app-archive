# Avaliacao Tripartite de Fundamentacao e Resposta (#88)

> **Methodology correction (#94):** These historical results were produced using synthetic fixtures and/or label-aware evaluation. They are not evidence of production retrieval quality or real agent grounding. Operational benchmark status: NOT RUN. Preserve these figures for historical traceability only.

- **Data:** 2026-11-25T23:04:40.754643+00:00
- **Total de Casos:** 465 (460 gold set + 5 adversariais)
- **Gate de Fundamentacao:** `PASS` (Claim Support >= 90%)

## Camada 1, 2 e 3 (Separacao Estrita: Resolucao vs Ranking vs Fundamentacao)

| Camada | Metrica | Valor |
|---|---|---:|
| 1. Resolucao da Intencao | `resolution_rate` | 100.00% |
| 2. Ranking de Evidencias | `recall@20` | 100.00% |
| 2. Ranking de Evidencias | `precision@10` | 99.28% |
| 2. Ranking de Evidencias | `mrr` | 0.9968 |
| 3. Fundamentacao (Claim Support) | `claim_support_rate` | 100.00% |
| 3. Fundamentacao (Citações/Hashes) | `citation_accuracy` | 100.00% |
| 3. Fundamentacao (Completude) | `requirement_completeness` | 100.00% |
| 3. Fundamentacao (Abstencao) | `abstention_accuracy` | 100.00% |
| 3. Fundamentacao (Conflitos/Supersessoes) | `conflicts_preserved_rate` | 100.00% |
| 3. Fundamentacao (Taxa de Alucinacao) | `hallucination_rate` | 0.00% |

## Sonda de Deteccao de Alucinacao com Retrieval 100% Correto

- **Retrieval Recall@20:** 100.00%
- **Alucinacao Detectada:** `True`
- **Claim Support na Sonda:** 0.00%
- **Citation Accuracy na Sonda:** 0.00%
- **Flags:** `citation_pin_mismatch:decision:ADR-0008, bad_citation:decision:ADR-0008`

## Resultados por Dominio (23 Dominios)

| Dominio | Casos | Resolucao | Recall@20 | Precision@10 | Claim Support | Citation Acc | Completeness |
|---|---:|---:|---:|---:|---:|---:|---:|
| `produto` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `concursos` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `aprendizagem` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `avaliacao` | 20 | 100.00% | 100.00% | 97.50% | 100.00% | 100.00% | 100.00% |
| `ia-informacao` | 20 | 100.00% | 100.00% | 97.50% | 100.00% | 100.00% | 100.00% |
| `workspace` | 22 | 100.00% | 100.00% | 97.73% | 100.00% | 100.00% | 100.00% |
| `objetos` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `visualizacoes` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `design-system` | 21 | 100.00% | 100.00% | 93.65% | 100.00% | 100.00% | 100.00% |
| `interacao` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `motion` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `acessibilidade` | 20 | 100.00% | 100.00% | 97.50% | 100.00% | 100.00% | 100.00% |
| `responsividade` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `ai-native-ux` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `engenharia` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `arquitetura-tecnica` | 21 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `qualidade` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `historico` | 21 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `midia` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `referencias-externas` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `conhecimento-humano` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `operacoes` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| `governanca` | 20 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
