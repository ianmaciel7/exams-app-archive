"use strict";
const byId = id => document.getElementById(id);
let records = [];
const normalize = value => String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
function element(tag, value) {
  const node = document.createElement(tag);
  node.textContent = value;
  return node;
}
function render() {
  const tokens = normalize(byId("search").value).split(/\s+/).filter(Boolean);
  const matches = records.filter(r =>
    ["kind", "product", "availability"].every(k => !byId(k).value || r[k] === byId(k).value) &&
    tokens.every(t => normalize(JSON.stringify(r)).includes(t)));
  byId("status").textContent = matches.length + " de " + records.length + " registros";
  const out = document.createDocumentFragment();
  for (const r of matches) {
    const card = document.createElement("article");
    card.append(element("h2", r.title), element("p", [r.kind, r.product, r.availability, r.date, r.license].filter(Boolean).join(" · ")));
    if (r.description) card.append(element("p", r.description));
    card.append(element("p", r.id + " · " + r.catalog_path));
    for (const source of r.sources || []) {
      let url;
      try { url = new URL(source); } catch { continue; }
      if (url.protocol !== "https:" || url.username || url.password) continue;
      const link = element("a", url.hostname);
      link.href = url.href;
      link.rel = "noopener noreferrer";
      card.append(link, document.createTextNode(" "));
    }
    out.append(card);
  }
  byId("records").replaceChildren(out);
}
async function load() {
  const response = await fetch("./research.json");
  if (!response.ok) throw new Error("Catálogo indisponível");
  records = (await response.json()).records;
  for (const key of ["product", "availability"]) {
    for (const value of [...new Set(records.map(r => r[key]).filter(Boolean))].sort()) {
      const option = element("option", value); option.value = value; byId(key).append(option);
    }
  }
  for (const key of ["search", "kind", "product", "availability"]) byId(key).addEventListener("input", render);
  render();
}
load().catch(() => { byId("status").textContent = "Catálogo indisponível; execute a exportação pública."; });
