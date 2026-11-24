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
  meta.append(element("span", "pill", {commit: "COMMIT", file: "ARQUIVO", image: "IMAGEM", node: "ENTIDADE"}[row.kind]));
  meta.append(element("span", "repo", row.repository));
  if (row.deleted) meta.append(element("span", "pill", "EXCLUÍDO"));
  const title = element("div", "summary", row.summary && ["commit","node"].includes(row.kind) ? row.summary : row.path);
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
  if (row.publicPath) { const link=element("a","copy","Abrir"); link.href="https://github.com/ianmaciel7/exams-app-archive/blob/main/"+row.publicPath; card.append(content,link,copy); } else card.append(content, copy);
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
  focusId = null; renderGraph();
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
    if (Array.isArray(parsed.nodes) && (Array.isArray(parsed.edges)||Array.isArray(parsed.links))) {
      graphData=readGraph(parsed);
      state.records=graphData.nodes.map(n=>({repository:n.repo||"Grafo",kind:"node",sha:n.sha,path:n.path,summary:n.label,graphId:n.id}));
    } else {
      if (parsed.version !== 1 || !Array.isArray(parsed.records) || !parsed.records.length || parsed.records.some(r=>!isValidRecord(r))) throw new Error("Formato inválido.");
      graphData=null; state.records=parsed.records;
    }
    $("query").value=""; $("kind").value=""; $("deleted").checked=false; $("confidence").value="";
    state.loaded=true;
    $("dataset").textContent=state.records.length.toLocaleString("pt-BR")+" registros locais";
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

let graphData=null, focusId=null;
function readGraph(data) {
  const nodes=[], seen=new Set();
  for(const n of data.nodes){if(!n||typeof n!=="object"||(n.node_id??n.id)==null)continue;const id=String(n.node_id??n.id);if(seen.has(id))continue;seen.add(id);nodes.push({id,label:String(n.label??n.name??id),repo:String(n.repo??""),path:String(n.path??n.source_file??""),sha:String(n.commit_sha??""),type:String(n.node_type??n.type??n.file_type??"Entity")});}
  if(!nodes.length)throw new Error("Grafo sem nós válidos.");
  const edges=(data.edges??data.links).filter(e=>e&&typeof e==="object").map(e=>({source:String(e.src_id??e.source),target:String(e.dst_id??e.target),type:String(e.edge_type??e.relation??e.type??"RELATED"),confidence:String(e.confidence??"UNSPECIFIED").toUpperCase()})).filter(e=>seen.has(e.source)&&seen.has(e.target)&&e.source!==e.target);
  return {nodes,edges};
}
function structuralGraph(rows){
  const nodes=new Map(),edges=new Map();
  function add(id,label,type,r,path=""){if(!nodes.has(id))nodes.set(id,{id,label,type,repo:r.repository,path,sha:r.sha});}
  function connect(source,target,type){edges.set(JSON.stringify([source,target,type]),{source,target,type,confidence:"EXTRACTED"});}
  for(const r of rows.slice(0,14)){
    const root="repo:"+r.repository;add(root,r.repository,"Repo",r);
    const parent=r.sha?"commit:"+r.repository+":"+r.sha:root;
    if(r.sha){add(parent,r.kind==="commit"?r.summary:r.sha.slice(0,10),"Commit",r);connect(root,parent,"HAS_COMMIT");}
    if(r.kind!=="commit"){const id="file:"+r.repository+":"+r.path;add(id,r.path.split("/").pop()||r.summary,r.kind==="image"?"Image":"File",r,r.path);connect(parent,id,r.sha?"INDEXED_AT":"CONTAINS");}
  }
  return {nodes:[...nodes.values()],edges:[...edges.values()]};
}
function svgNode(tag,attrs){const n=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));return n;}
function renderGraph(){
  const svg=$("graph");clear(svg);clear($("graph-neighbors"));
  const g=graphData||structuralGraph(state.matches);
  const all=new Map(g.nodes.map(n=>[n.id,n])),conf=$("confidence").value;
  const eligible=g.edges.filter(e=>!conf||e.confidence===conf);
  let ids=new Set(focusId&&all.has(focusId)?[focusId]:graphData?state.matches.slice(0,10).map(r=>r.graphId):g.nodes.slice(0,30).map(n=>n.id));
  const seeds=new Set(ids);
  for(const e of eligible){if(ids.size>=30)break;if(seeds.has(e.source)||seeds.has(e.target)){ids.add(e.source);ids.add(e.target);}}
  const nodes=[...ids].filter(id=>all.has(id)).slice(0,30).map(id=>all.get(id));
  const positions=new Map();
  nodes.forEach((n,i)=>{const angle=i*2.399963;const radius=i===0?0:Math.sqrt(i/Math.max(1,nodes.length-1));positions.set(n.id,[400+Math.cos(angle)*330*radius,220+Math.sin(angle)*178*radius]);});
  const edges=eligible.filter(e=>positions.has(e.source)&&positions.has(e.target));
  for(const e of edges){const [x1,y1]=positions.get(e.source),[x2,y2]=positions.get(e.target);const line=svgNode("line",{x1,y1,x2,y2,class:e.confidence==="EXTRACTED"?"graph-edge":"graph-edge graph-dashed"});const tip=svgNode("title",{});tip.textContent=e.type+" · "+e.confidence;line.append(tip);svg.append(line);}
  for(const n of nodes){const [x,y]=positions.get(n.id);const group=svgNode("g",{class:"graph-node "+(n.id===focusId?"selected":""),tabindex:0,role:"button","aria-label":n.label});const hit=svgNode("circle",{cx:x,cy:y,r:30,fill:"transparent",class:"graph-hit"});const circle=svgNode("circle",{cx:x,cy:y,r:n.type==="Repo"?14:10,fill:n.type==="Repo"?"#9d83e8":n.type==="Commit"?"#e2b56c":n.type==="Image"?"#68c7a0":"#83b6ed"});const label=svgNode("text",{x,y:y+22,"text-anchor":"middle"});label.textContent=n.label.length>29?n.label.slice(0,27)+"…":n.label;const tip=svgNode("title",{});tip.textContent=n.label;group.append(hit,circle,label,tip);const select=()=>{focusId=n.id;renderGraph();};group.addEventListener("click",select);group.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();select();}});svg.append(group);}
  $("graph-meta").textContent=(graphData?"Grafo importado":"Relações estruturais do catálogo/índice")+" · "+nodes.length+" nós · "+edges.length+" relações";
  const n=all.get(focusId);$("graph-detail").textContent=n?[n.label,n.type,n.repo,n.path,n.sha].filter(Boolean).join(" · "):"Selecione um nó para explorar.";
  if(n)for(const e of eligible.filter(e=>e.source===n.id||e.target===n.id).slice(0,25)){const other=all.get(e.source===n.id?e.target:e.source);if(!other)continue;const btn=element("button","neighbor",other.label+" · "+e.type+" · "+e.confidence);btn.addEventListener("click",()=>{focusId=other.id;renderGraph();});$("graph-neighbors").append(btn);}
}
$("confidence").addEventListener("change",renderGraph);
$("graph-reset").addEventListener("click",()=>{focusId=null;renderGraph();});
const catalog=[
 ["README.md","Visão geral · archive histórico backups"],
 ["docs/EXTRACTION-GUIDE.md","Recuperação de arquivos originais git bundles"],
 ["reports/FULL-INDEX.md","Índice FTS5 pesquisa commits imagens"],
 ["docs/ENHANCEMENT-INTEGRATION-MATRIX.md","Graphify grafo contexto AST search"],
 ["docs/AGENT-ACCESS.md","CLI MCP agentes configuração"],
 ["docs/DELETE-READINESS.md","Verificação de backups"],
 ["scripts/graph_linker.py","Grafo relações extraídas inferidas"],
 ["scripts/context_linker.py","Contexto histórico e timeline"],
 ["scripts/archive_mcp.py","MCP local stdio"]
];
state.records=catalog.map(([path,summary])=>({repository:"exams-app-archive",kind:"file",sha:"",path,summary,publicPath:path}));
state.loaded=true;updateFilters();filter();
