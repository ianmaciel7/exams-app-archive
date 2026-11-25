"use strict";
const $ = (id) => document.getElementById(id);
const publicRepos = new Set();
const allowedRepos = new Set([
  "exams-app",
  "exams-app-old",
  "exams-app-antigo-2",
  "shadcn-template",
  "shadcn-firebase-template",
]);
const embed = new URLSearchParams(location.search).get("embed") === "1";
if (embed) document.body.classList.add("embedded-files");

const reviewed = {
  "src/app/error.tsx": {
    blob: "936e638aa231a2533e866c12e4d97a429c524d6c",
    page: "preview-error.html",
  },
  "src/app/loading.tsx": {
    blob: "5850f0972153976a33e3e42e0891f9f23ac8bad8",
    page: "preview-loading.html",
  },
};

function reviewedEntry(entry) {
  const item = reviewed[entry?.path];
  return state.mode === "public" && state.repo === "exams-app-old" && item && item.blob === entry.blob
    ? item
    : null;
}

let publicSnapshots = [];
let blobsBase = "";

async function loadPublicSources() {
  try {
    const r = await fetch("./catalog.json", { credentials: "omit", cache: "no-cache" });
    if (!r.ok) throw Error("HTTP " + r.status);
    const data = await r.json();
    if (data.version !== 2) throw Error("Formato inválido");
    publicSnapshots = data.snapshots || [];
    blobsBase = typeof data.blobs_base === "string" ? data.blobs_base.replace(/\/$/, "") : "";
    publicRepos.clear();
    for (const s of publicSnapshots) {
      if (allowedRepos.has(s.repo) && (s.files || []).length > 0) publicRepos.add(s.repo);
    }
    for (const s of publicSnapshots) {
      if (allowedRepos.has(s.repo)) publicRepos.add(s.repo);
    }
    const select = $("source-repo");
    const repoOrder = ["exams-app-old", "exams-app-antigo-2", "exams-app", "shadcn-template", "shadcn-firebase-template"];
    const sortedRepos = [...publicRepos].sort((a, b) => {
      const ia = repoOrder.indexOf(a);
      const ib = repoOrder.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib) || a.localeCompare(b);
    });
    select.replaceChildren(...sortedRepos.map((repo) => new Option(repo, repo)));
    refreshRefs();
    $("load-public").disabled = !publicRepos.size;
    const opened = await openRequestedFile();
    if (!opened && publicRepos.size) {
      await loadSelectedSnapshot(true);
    } else if (!publicRepos.size) {
      status("Nenhum repositório público disponível. Use uma pasta local.");
    }
  } catch (e) {
    status("Catálogo indisponível: " + e.message + ". Use uma pasta local.");
  }
}

function refreshRefs() {
  const repo = $("source-repo").value;
  const sel = $("source-ref");
  sel.replaceChildren();
  const snaps = publicSnapshots
    .filter((s) => s.repo === repo)
    .sort((a, b) => (b.files?.length || 0) - (a.files?.length || 0));
  for (const s of snaps) {
    const cleanRefs = (s.refs || []).map((r) => r.replace(/^branch:/, "")).join(", ");
    const label = cleanRefs + " (" + (s.files?.length || 0) + ")";
    sel.append(new Option(label, s.sha));
  }
}

const state = { mode: "", repo: "", sha: "", entries: [], selected: null, expanded: new Set(), epoch: 0, url: null };
const limit = 2 * 1024 * 1024;
const isReact = (p) => /\.(tsx|jsx)$/i.test(p);
const isHtml = (p) => /\.html?$/i.test(p);
const mime = (p) =>
  ({ png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", webp: "image/webp", gif: "image/gif", svg: "image/svg+xml" }[
    p.split(".").pop().toLowerCase()
  ] || "");

function node(tag, text, cls) {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (cls) n.className = cls;
  return n;
}
function status(s) {
  $("file-status").textContent = s;
}
function pathEncoded(path) {
  return path.split("/").map(encodeURIComponent).join("/");
}

async function api(repo, endpoint) {
  if (!publicRepos.has(repo)) throw Error("Origem não permitida.");
  const response = await fetch("https://api.github.com/repos/ianmaciel7/" + repo + "/" + endpoint, {
    credentials: "omit",
    redirect: "error",
    referrerPolicy: "no-referrer",
    headers: { Accept: "application/vnd.github+json" },
  });
  if (!response.ok) throw Error("GitHub HTTP " + response.status + " (repositório arquivado ou limite público)");
  return response.json();
}

async function fetchBlobBytes(entry) {
  if (state.mode === "local") {
    return new Uint8Array(await entry.file.arrayBuffer());
  }
  if (blobsBase && entry.blob && /^[0-9a-f]{40}$/.test(entry.blob)) {
    const localUrl = blobsBase + "/" + entry.blob.slice(0, 2) + "/" + entry.blob;
    const res = await fetch(localUrl, { credentials: "omit" });
    if (res.ok) return new Uint8Array(await res.arrayBuffer());
  }
  const data = await api(state.repo, "git/blobs/" + entry.blob);
  if (data.encoding !== "base64") throw Error("Formato de blob não suportado.");
  return Uint8Array.from(atob(data.content.replace(/\s/g, "")), (c) => c.charCodeAt(0));
}

function resetPreview() {
  const frame = $("preview-frame");
  frame.removeAttribute("srcdoc");
  frame.removeAttribute("src");
  frame.setAttribute("sandbox", "");
  frame.hidden = true;
  $("preview-image").hidden = true;
  $("preview-image").removeAttribute("src");
  if (state.url) {
    URL.revokeObjectURL(state.url);
    state.url = null;
  }
}

function clearSelection() {
  state.selected = null;
  resetPreview();
  $("file-evidence").hidden = true;
  $("selected-path").textContent = "Selecione um arquivo na árvore";
  $("source-code").textContent = "Selecione um arquivo na árvore à esquerda para ver o código ou preview.";
  $("source-info").textContent = "";
  $("source-link").hidden = true;
  $("copy-code").hidden = true;
  $("split-tab").disabled = true;
  $("preview-tab").disabled = true;
  $("viewport-group").hidden = true;
  $("render-preview").hidden = true;
  $("render-tsx").hidden = true;
  $("render-reviewed").hidden = true;
  $("render-live").hidden = true;
  $("component-help").hidden = true;
  setMode("code");
}

function setMode(mode) {
  const stage = $("viewer-stage");
  if (stage) stage.dataset.mode = mode;
  $("source-code").hidden = mode === "preview";
  $("preview-area").hidden = mode === "code";
  $("code-tab").setAttribute("aria-pressed", String(mode === "code"));
  $("split-tab").setAttribute("aria-pressed", String(mode === "split"));
  $("preview-tab").setAttribute("aria-pressed", String(mode === "preview"));
  const vpGroup = $("viewport-group");
  if (vpGroup) vpGroup.hidden = mode === "code";
}

function tab(preview) {
  setMode(preview ? "preview" : "code");
}

function svgIcon(kind) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("width", "14");
  svg.setAttribute("height", "14");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.8");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("tree-svg", "tree-svg-" + kind);
  const paths = {
    folder: ["M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"],
    react: ["M12 12m-2 0a2 2 0 1 0 4 0a2 2 0 1 0 -4 0", "M12 5c5 0 9 3.1 9 7s-4 7-9 7-9-3.1-9-7 4-7 9-7z"],
    file: ["M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z", "M14 2v4a2 2 0 0 0 2 2h4"],
  }[kind] || [];
  for (const d of paths) {
    const p = document.createElementNS(ns, "path");
    p.setAttribute("d", d);
    svg.append(p);
  }
  return svg;
}

function renderTree() {
  const root = $("tree");
  root.replaceChildren();
  const query = $("tree-search").value.trim().toLowerCase();
  const only = $("components-only").checked;
  const filtered = state.entries.filter(
    (e) => (!only || isReact(e.path)) && (!query || e.path.toLowerCase().includes(query))
  );
  const tree = { children: new Map(), entry: null };
  for (const e of filtered) {
    let cur = tree;
    for (const part of e.path.split("/")) {
      if (!cur.children.has(part)) cur.children.set(part, { children: new Map(), entry: null });
      cur = cur.children.get(part);
    }
    cur.entry = e;
  }
  let shown = 0;
  function walk(parent, branch, prefix, depth) {
    const entries = [...branch.children.entries()].sort((a, b) => {
      const fa = a[1].children.size > 0;
      const fb = b[1].children.size > 0;
      if (fa !== fb) return fa ? -1 : 1;
      const da = a[0].startsWith(".");
      const db = b[0].startsWith(".");
      if (da !== db) return da ? 1 : -1;
      if (a[0] === "src") return -1;
      if (b[0] === "src") return 1;
      return a[0].localeCompare(b[0]);
    });
    for (const [name, item] of entries) {
      if (shown++ >= 1500) return;
      const path = prefix ? prefix + "/" + name : name;
      const folder = item.children.size > 0;
      const row = node("button", undefined, "tree-row");
      row.type = "button";
      row.style.paddingLeft = String(8 + Math.min(depth, 10) * 14) + "px";
      if (folder) {
        const open = state.expanded.has(path) || !!query;
        row.append(node("span", open ? "▾" : "▸", "tree-chevron"), svgIcon("folder"), node("span", name, "tree-name"));
        row.title = path;
        row.setAttribute("aria-expanded", String(open));
        row.addEventListener("click", () => {
          if (state.expanded.has(path)) state.expanded.delete(path);
          else state.expanded.add(path);
          renderTree();
        });
        parent.append(row);
        if (open) walk(parent, item, path, depth + 1);
      } else {
        row.append(node("span", "", "tree-chevron"), svgIcon(isReact(path) ? "react" : "file"), node("span", name, "tree-name"));
        row.title = path;
        row.setAttribute("aria-current", String(state.selected?.path === path));
        row.addEventListener("click", () => select(item.entry));
        parent.append(row);
      }
    }
  }
  walk(root, tree, "", 0);
  if (!filtered.length) root.append(node("p", "Nenhum arquivo nesta seleção.", "hint"));
  if (shown >= 1500) root.append(node("p", "Exibição limitada; use o filtro para restringir.", "hint"));
  const activeRow = root.querySelector('.tree-row[aria-current="true"]');
  if (activeRow) {
    const targetTop = activeRow.offsetTop - root.offsetTop - 80;
    if (targetTop > 0) root.scrollTop = targetTop;
  }
}

function install(mode, entries, repo = "", sha = "") {
  state.mode = mode;
  state.repo = repo;
  state.sha = sha;
  state.entries = entries;
  state.expanded = new Set();
  for (const e of entries) {
    const first = e.path.split("/")[0];
    if (first === "src" || first === "app" || first === "components") state.expanded.add(first);
  }
  $("tree-search").value = "";
  $("components-only").checked = false;
  clearSelection();
  renderTree();
  status(
    entries.length.toLocaleString("pt-BR") +
      " arquivos · " +
      (mode === "public" ? repo + " @ " + sha.slice(0, 12) : "pasta local")
  );
}

async function loadSelectedSnapshot(autoPick = false) {
  const epoch = ++state.epoch;
  const repo = $("source-repo").value;
  const ref = $("source-ref").value;
  try {
    const snapshot = publicSnapshots.find((s) => s.repo === repo && s.sha === ref);
    if (!snapshot) throw Error("Revisão não encontrada no catálogo.");
    if (epoch !== state.epoch) return;
    const entries = snapshot.files.map((x) => ({ path: x.path, size: x.size, blob: x.blob, cached: !!x.cached }));
    install("public", entries, repo, ref);
    if (autoPick && entries.length) {
      const preferred =
        entries.find((e) => /sidebar\.tsx$/i.test(e.path) && !/test/i.test(e.path)) ||
        entries.find((e) => /sidebar/i.test(e.path) && isReact(e.path)) ||
        entries.find((e) => isReact(e.path)) ||
        entries.find((e) => /readme\.md$/i.test(e.path)) ||
        entries[0];
      if (preferred) {
        const parts = preferred.path.split("/");
        for (let i = 1; i < parts.length; i++) state.expanded.add(parts.slice(0, i).join("/"));
        await select(preferred);
        if (isReact(preferred.path)) {
          setMode("split");
        }
      }
    }
  } catch (e) {
    if (epoch === state.epoch) status(e.message);
  }
}

$("load-refs").addEventListener("click", loadPublicSources);
$("source-repo").addEventListener("change", () => {
  refreshRefs();
  loadSelectedSnapshot(true);
});
$("source-ref").addEventListener("change", () => loadSelectedSnapshot(true));
$("load-public").addEventListener("click", () => loadSelectedSnapshot(false));

function loadLocal(files) {
  const list = [...files]
    .filter((f) => !/(^|\/)(node_modules|\.git)\//.test(f.webkitRelativePath || f.name))
    .map((f) => ({ path: (f.webkitRelativePath || f.name).replace(/^\/+/, ""), size: f.size, file: f }));
  if (!list.length) {
    status("Nenhum arquivo selecionado.");
    return;
  }
  install("local", list);
}
$("local-folder").addEventListener("change", (e) => loadLocal(e.target.files || []));
$("local-files").addEventListener("change", (e) => loadLocal(e.target.files || []));
$("tree-search").addEventListener("input", renderTree);
$("components-only").addEventListener("change", renderTree);

async function select(entry) {
  const epoch = ++state.epoch;
  state.selected = entry;
  renderTree();
  resetPreview();
  setMode("code");
  $("selected-path").textContent = (state.mode === "public" ? state.repo + " / " : "") + entry.path.split("/").join(" / ");
  $("source-info").textContent = [
    state.sha ? state.sha.slice(0, 12) : "",
    entry.blob ? "blob " + entry.blob.slice(0, 12) : "",
    Number(entry.size || 0).toLocaleString("pt-BR") + " bytes",
  ]
    .filter(Boolean)
    .join(" · ");
  $("source-link").hidden = state.mode !== "public";
  if (state.mode === "public") {
    $("source-link").href =
      "https://github.com/ianmaciel7/" + state.repo + "/blob/" + state.sha + "/" + pathEncoded(entry.path);
  }
  $("copy-code").hidden = true;
  $("split-tab").disabled = true;
  $("preview-tab").disabled = true;
  $("render-preview").hidden = true;
  $("render-tsx").hidden = true;
  $("render-reviewed").hidden = true;
  $("render-live").hidden = true;
  $("component-help").hidden = !isReact(entry.path);
  $("source-code").textContent = "Carregando…";
  try {
    if (entry.size > limit) throw Error("Arquivo maior que 2 MiB; abra no GitHub ou localmente.");
    const bytes = await fetchBlobBytes(entry);
    if (epoch !== state.epoch) return;
    const imageType = mime(entry.path);
    if (imageType) {
      state.url = URL.createObjectURL(new Blob([bytes], { type: imageType }));
      $("preview-image").src = state.url;
      $("preview-image").hidden = false;
      $("preview-note").textContent = "Imagem original do repositório arquivado.";
      $("source-code").textContent = "Arquivo de imagem (" + imageType + ").";
      $("preview-tab").disabled = false;
      setMode("preview");
      return;
    }
    if (bytes.includes(0)) throw Error("Arquivo binário sem visualização.");
    entry.text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    $("source-code").textContent = entry.text;
    $("copy-code").hidden = false;
    $("file-evidence").hidden = !embed;
    $("excerpt-start").value = "1";
    $("excerpt-end").value = String(Math.min(80, entry.text.split(/\r?\n/).length));
    $("excerpt-status").textContent = "";

    const approved = reviewedEntry(entry);
    if (approved) {
      $("split-tab").disabled = false;
      $("preview-tab").disabled = false;
      $("render-reviewed").hidden = false;
      $("render-tsx").hidden = false;
      $("preview-bar").hidden = false;
      $("preview-note").textContent = "Build React revisado disponível.";
      setMode("split");
      renderReviewedComponent(approved);
    } else if (isReact(entry.path)) {
      $("split-tab").disabled = false;
      $("preview-tab").disabled = false;
      $("render-tsx").hidden = false;
      if (state.mode === "public") {
        $("preview-bar").hidden = true;
        setMode("split");
        renderTsxExperimental();
      } else {
        $("preview-bar").hidden = false;
        $("preview-note").textContent = "Arquivo local React/TSX. Clique em Recarregar preview para executar.";
      }
    }
    if (isHtml(entry.path)) {
      $("split-tab").disabled = false;
      $("preview-tab").disabled = false;
      $("preview-bar").hidden = false;
      $("render-preview").hidden = false;
      $("render-live").hidden = state.mode !== "local";
      $("preview-note").textContent = "HTML isolado. Scripts bloqueados no modo estático.";
      setMode("split");
    }
  } catch (e) {
    if (epoch === state.epoch) $("source-code").textContent = e.message;
  }
}

$("copy-code").addEventListener("click", async () => {
  const entry = state.selected;
  if (!entry || typeof entry.text !== "string") return;
  try {
    await navigator.clipboard.writeText(entry.text);
    $("copy-code").textContent = "Copiado";
    setTimeout(() => {
      $("copy-code").textContent = "Copiar";
    }, 1500);
  } catch {
    status("Não foi possível copiar automaticamente.");
  }
});

$("code-tab").addEventListener("click", () => setMode("code"));
$("split-tab").addEventListener("click", () => setMode("split"));
$("preview-tab").addEventListener("click", () => setMode("preview"));
$("vp-desktop")?.addEventListener("click", () => {
  $("preview-stage-wrap").dataset.vp = "desktop";
  $("vp-desktop").setAttribute("aria-pressed", "true");
  $("vp-mobile").setAttribute("aria-pressed", "false");
});
$("vp-mobile")?.addEventListener("click", () => {
  $("preview-stage-wrap").dataset.vp = "mobile";
  $("vp-desktop").setAttribute("aria-pressed", "false");
  $("vp-mobile").setAttribute("aria-pressed", "true");
});

function render(live) {
  const entry = state.selected;
  if (!entry || !isHtml(entry.path) || typeof entry.text !== "string") return;
  if (
    live &&
    (state.mode !== "local" ||
      !confirm(
        "Executar este build local? Use apenas código que você revisou. O sandbox reduz riscos, mas não substitui isolamento de sistema."
      ))
  )
    return;
  resetPreview();
  const frame = $("preview-frame");
  frame.setAttribute("sandbox", live ? "allow-scripts" : "");
  const policy =
    "default-src 'none'; script-src " +
    (live ? "'unsafe-inline'" : "'none'") +
    "; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'";
  frame.srcdoc = '<!doctype html><meta http-equiv="Content-Security-Policy" content="' + policy + '">' + entry.text;
  frame.hidden = false;
}

async function renderTsxExperimental() {
  const entry = state.selected;
  if (!entry || !isReact(entry.path) || typeof entry.text !== "string") return;
  resetPreview();
  $("preview-note").textContent = "Carregando dependências locais do snapshot e transpilando TSX…";

  const fileMap = {};
  const importRegex = /from\s+["'](\.[^"']+|@\/[^"']+)["']/g;
  const toFetch = [];
  let match;
  while ((match = importRegex.exec(entry.text)) !== null) {
    const spec = match[1];
    const baseParts = entry.path.split("/").slice(0, -1);
    let prefix = "";
    if (spec.startsWith("@/")) {
      prefix = spec.slice(2);
    } else {
      const parts = [...baseParts];
      for (const seg of spec.split("/")) {
        if (!seg || seg === ".") continue;
        if (seg === "..") parts.pop();
        else parts.push(seg);
      }
      prefix = parts.join("/");
    }
    const exts = ["", ".tsx", ".ts", ".jsx", ".js", "/index.tsx", "/index.ts", "/index.jsx", "/index.js"];
    const wanted = new Set();
    for (const ext of exts) {
      wanted.add(prefix + ext);
      wanted.add("src/" + prefix + ext);
    }
    const candidate = state.entries.find((e) => e.path !== entry.path && wanted.has(e.path));
    if (candidate && toFetch.length < 12) {
      toFetch.push(candidate);
    }
  }

  for (const dep of toFetch) {
    try {
      const b = await fetchBlobBytes(dep);
      if (!b.includes(0)) fileMap[dep.path] = new TextDecoder("utf-8").decode(b);
    } catch {
      // Fallback proxy will handle missing dependency
    }
  }

  const runtimeUrl = new URL("./tsx-preview-runtime.js", location.href).href;
  const tailwindUrl = new URL("./archive-tailwind.css", location.href).href;
  const payload = JSON.stringify({ path: entry.path, code: entry.text, files: fileMap }).replace(/<\//g, "<\\/");
  const previewCss = [
    ".pv-error{margin:16px;padding:14px;border:1px solid #fecaca;background:#fef2f2;color:#991b1b;border-radius:8px;font-size:13px}",
    ".pv-error pre{white-space:pre-wrap;font-size:12px;margin:8px 0 0}",
    ".pv-info{margin:16px;padding:14px;border:1px solid #cbd5e1;background:#f8fafc;border-radius:8px;font-size:13px}",
  ].join("");

  const html =
    "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>" +
    "<link rel='stylesheet' href='" + tailwindUrl + "'>" +
    "<style>" + previewCss + "</style>" +
    "<script src='" + runtimeUrl + "'></script></head>" +
    "<body><div id='root'></div>" +
    "<script id='pv-data' type='application/json'>" + payload + "</script>" +
    "<script>" +
    "(function(){var d=JSON.parse(document.getElementById('pv-data').textContent);" +
    "if(typeof window.renderArchiveComponent==='function'){window.renderArchiveComponent(document.getElementById('root'),d.path,d.code,d.files);}" +
    "else{document.getElementById('root').innerHTML='<div class=\"pv-info\">Runtime TSX indisponivel neste ambiente local. Publique via GitHub Pages ou execute o build de preview.</div>';}" +
    "})();</script></body></html>";

  const frame = $("preview-frame");
  frame.setAttribute("sandbox", "allow-scripts");
  frame.srcdoc = html;
  frame.hidden = false;
  $("preview-note").textContent = "Preview TSX experimental renderizado em iframe isolado.";
}

$("render-preview").addEventListener("click", () => render(false));
$("render-live").addEventListener("click", () => render(true));
$("render-tsx").addEventListener("click", renderTsxExperimental);

let requestedOpened = false;
async function openRequestedFile() {
  if (requestedOpened) return false;
  requestedOpened = true;
  const params = new URLSearchParams(location.search);
  const repo = params.get("repo");
  const sha = params.get("sha");
  const path = params.get("path");
  if (!repo || !sha || !path || !publicRepos.has(repo)) return false;
  const snapshot = publicSnapshots.find((s) => s.repo === repo && s.sha === sha);
  if (!snapshot) return false;
  const match = snapshot.files.find((f) => f.path === path);
  if (!match) return false;
  $("source-repo").value = repo;
  refreshRefs();
  $("source-ref").value = sha;
  install(
    "public",
    snapshot.files.map((x) => ({ path: x.path, size: x.size, blob: x.blob, cached: !!x.cached })),
    repo,
    sha
  );
  for (const part of path
    .split("/")
    .slice(0, -1)
    .map((_, i) => path.split("/").slice(0, i + 1).join("/"))) {
    state.expanded.add(part);
  }
  await select(state.entries.find((x) => x.path === path));
  return true;
}

function renderReviewedComponent(item) {
  if (!item) return;
  resetPreview();
  const frame = $("preview-frame");
  frame.setAttribute("sandbox", "allow-scripts");
  frame.src = "./" + item.page;
  frame.hidden = false;
}

$("render-reviewed").addEventListener("click", () => {
  renderReviewedComponent(reviewedEntry(state.selected));
});

$("send-excerpt").addEventListener("click", () => {
  const entry = state.selected;
  if (!embed || !entry || typeof entry.text !== "string" || window.parent === window) return;
  const lines = entry.text.split(/\r?\n/);
  const start = Math.max(1, Math.min(lines.length, Math.floor(Number($("excerpt-start").value) || 1)));
  const end = Math.max(start, Math.min(lines.length, start + 199, Math.floor(Number($("excerpt-end").value) || start)));
  const text = lines.slice(start - 1, end).join("\n");
  if (text.length > 12000) {
    $("excerpt-status").textContent = "Reduza o trecho a 12.000 caracteres.";
    return;
  }
  window.parent.postMessage(
    {
      type: "archive-evidence",
      repository: state.mode === "public" ? state.repo : "local",
      commit: state.sha,
      path: entry.path,
      blob: entry.blob || null,
      start,
      end,
      text,
    },
    location.origin
  );
  $("excerpt-status").textContent = "Trecho enviado ao contexto desta aba.";
});

loadPublicSources();
