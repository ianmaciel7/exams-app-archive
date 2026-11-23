"use strict";
// No fetch, analytics, storage, cookies, or network calls. Imports stay in this tab.
const $ = (id) => document.getElementById(id);
const state = {records: [], matches: [], displayed: 0, loaded: false};
const PAGE_SIZE = 60;
const MAX_BYTES = 100 * 1024 * 1024;

function normalize(value) {
  return String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}
function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function clear(node) { node.replaceChildren(); }
function empty(title, message) {
  const card = element("div", "empty");
  card.append(element("h3", "", title), element("p", "", message));
  $("results").append(card);
}
function isValidRecord(row) {
  return row && typeof row === "object" &&
    typeof row.repository === "string" &&
    ["commit", "file", "image"].includes(row.kind) &&
    typeof row.sha === "string" &&
    typeof row.path === "string" &&
    typeof row.summary === "string";
}
function updateFilters() {
  const repos = [...new Set(state.records.map(r => r.repository))].sort();
  clear($("repository"));
  $("repository").append(new Option("Todos os repositórios", ""));
  for (const repo of repos) $("repository").append(new Option(repo, repo));
  for (const id of ["query", "repository", "kind", "deleted", "clear"]) $(id).disabled = false;
}
function renderCard(row) {
  const card = element("article", "result");
  const content = element("div");
  const meta = element("div");
  meta.append(element("span", "pill", {commit: "COMMIT", file: "ARQUIVO", image: "IMAGEM"}[row.kind]));
  meta.append(element("span", "repo", row.repository));
  if (row.deleted) meta.append(element("span", "pill", "EXCLUÍDO"));
  const title = element("div", "summary", row.summary && row.kind === "commit" ? row.summary : row.path);
  const details = element("div", "meta", row.sha.slice(0, 12) + (row.kind === "image" ? " · " + Number(row.bytes || 0).toLocaleString("pt-BR") + " bytes" : ""));
  content.append(meta, title, details);
  const copy = element("button", "copy", "Copiar ref.");
  copy.type = "button";
  copy.setAttribute("aria-label", "Copiar referência de " + row.repository);
  copy.addEventListener("click", async () => {
    const reference = [row.repository, row.sha, row.path, row.summary].filter(Boolean).join(" | ");
    try {
      await navigator.clipboard.writeText(reference);
      $("status").textContent = "Referência copiada.";
    } catch {
      $("status").textContent = "O navegador bloqueou a cópia. Selecione e copie a referência manualmente.";
    }
  });
  card.append(content, copy);
  return card;
}
function showMore() {
  const end = Math.min(state.displayed + PAGE_SIZE, state.matches.length);
  const fragment = document.createDocumentFragment();
  for (let i = state.displayed; i < end; i++) fragment.append(renderCard(state.matches[i]));
  $("results").append(fragment);
  state.displayed = end;
  $("more").hidden = end >= state.matches.length;
}
function filter() {
  if (!state.loaded) return;
  const terms = normalize($("query").value).split(/\s+/).filter(Boolean).slice(0, 8);
  const repo = $("repository").value, kind = $("kind").value, deleted = $("deleted").checked;
  state.matches = state.records.filter(r =>
    (!repo || r.repository === repo) &&
    (!kind || r.kind === kind) &&
    (!deleted || !!r.deleted) &&
    terms.every(t => normalize(r.repository + " " + r.path + " " + r.summary).includes(t))
  );
  state.displayed = 0;
  clear($("results"));
  $("status").textContent = state.matches.length.toLocaleString("pt-BR") + " resultados de " +
    state.records.length.toLocaleString("pt-BR") + " registros";
  if (!state.matches.length) {
    $("more").hidden = true;
    empty("Nenhum resultado encontrado", "Tente outro termo ou remova os filtros.");
  } else {
    showMore();
  }
}
$("file").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  if (file.size > MAX_BYTES) {
    $("status").textContent = "Arquivo maior que 100 MiB. Gere um índice menor.";
    return;
  }
  $("status").textContent = "Lendo arquivo local…";
  try {
    const parsed = JSON.parse(await file.text());
    if (parsed.version !== 1 || !Array.isArray(parsed.records) ||
        parsed.records.length === 0 || parsed.records.some(r => !isValidRecord(r))) {
      throw new Error("Formato inválido. Use o exportador do plugin.");
    }
    state.records = parsed.records;
    state.loaded = true;
    $("dataset").textContent = state.records.length.toLocaleString("pt-BR") + " registros carregados";
    updateFilters();
    filter();
  } catch (error) {
    $("status").textContent = "Não foi possível importar: " + error.message;
  }
});
for (const id of ["query", "repository", "kind", "deleted"]) {
  $(id).addEventListener(id === "query" ? "input" : "change", filter);
}
$("clear").addEventListener("click", () => {
  $("query").value = ""; $("repository").value = ""; $("kind").value = ""; $("deleted").checked = false;
  filter();
  $("query").focus();
});
$("more").addEventListener("click", showMore);
