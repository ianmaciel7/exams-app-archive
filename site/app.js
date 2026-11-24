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
  const actions=element("div","result-actions"); if(row.graphId){const focus=element("button","copy","Ver no grafo");focus.addEventListener("click",()=>{focusId=row.graphId;activeGroup="";renderGraph();$("graph-panel").scrollIntoView({block:"start"});});actions.append(focus);} if(row.publicPath){const link=element("a","copy","Abrir");link.href="https://github.com/ianmaciel7/exams-app-archive/blob/main/"+row.publicPath;actions.append(link);} actions.append(copy);card.append(content,actions);
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
  focusId = null; activeGroup = ""; renderGraph();
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
      graphData=readGraph(parsed); graphOrigin="importado";
      state.records=graphData.nodes.map(n=>({repository:n.repo||"Grafo",kind:"node",sha:n.sha,path:n.path,summary:n.label,graphId:n.id}));
    } else {
      if (parsed.version !== 1 || !Array.isArray(parsed.records) || !parsed.records.length || parsed.records.some(r=>!isValidRecord(r))) throw new Error("Formato inválido.");
      graphData=null; graphOrigin="índice histórico"; state.records=parsed.records;
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

let graphData=null, focusId=null, activeGroup="", graphOrigin="catálogo público";
const palette=["#79a8ff","#54d6b1","#e7b56e","#a990f3","#ef8ca4","#6ac8e7","#c1d675","#f29b69","#9ca8d8","#77c5a0"];
let camera={x:0,y:0,z:1};
function readGraph(data){
  const nodes=[],seen=new Set(),communityMap=new Map();
  if(data.communities&&typeof data.communities==="object")for(const [id,members] of Object.entries(data.communities)){if(Array.isArray(members))for(const member of members)communityMap.set(String(member),id);}
  for(const n of data.nodes){if(!n||typeof n!=="object"||(n.node_id??n.id)==null)continue;const id=String(n.node_id??n.id);if(seen.has(id))continue;seen.add(id);const rawCommunity=n.community??n.community_id??communityMap.get(id);const repo=String(n.repo??"");const type=String(n.node_type??n.type??n.file_type??"Entity");nodes.push({id,label:String(n.label??n.name??id),repo,path:String(n.path??n.source_file??""),sha:String(n.commit_sha??""),type,community:rawCommunity==null?null:String(rawCommunity),communityName:String(n.community_name??data.community_labels?.[rawCommunity]??""),line:String(n.source_location??n.line??""),validity:String(n.validity_status??"")});}
  if(!nodes.length)throw Error("Grafo sem nós válidos.");
  const edges=(data.edges??data.links).filter(e=>e&&typeof e==="object").map(e=>({source:String(e.src_id??e._src??e.source??e.from),target:String(e.dst_id??e._tgt??e.target??e.to),type:String(e.edge_type??e.relation??e.type??"RELATED"),confidence:String(e.confidence??"UNSPECIFIED").toUpperCase(),evidence:String(e.source_file??e.commit_sha??"")})).filter(e=>seen.has(e.source)&&seen.has(e.target)&&e.source!==e.target);
  return {nodes,edges};
}
function structuralGraph(rows){
  const nodes=new Map(),edges=new Map();
  function add(id,label,type,r,path=""){if(!nodes.has(id))nodes.set(id,{id,label,type,repo:r.repository,path,sha:r.sha});}
  function connect(source,target,type){edges.set(JSON.stringify([source,target,type]),{source,target,type,confidence:"EXTRACTED"});}
  for(const r of rows.slice(0,2500)){
    const root="repo:"+r.repository;add(root,r.repository,"Repo",r);
    const parent=r.sha?"commit:"+r.repository+":"+r.sha:root;
    if(r.sha){add(parent,r.kind==="commit"?r.summary:r.sha.slice(0,10),"Commit",r);connect(root,parent,"HAS_COMMIT");}
    if(r.kind!=="commit"){const id="file:"+r.repository+":"+r.path;add(id,r.path.split("/").pop()||r.summary,r.kind==="image"?"Image":"File",r,r.path);connect(parent,id,r.sha?"INDEXED_AT":"CONTAINS");}
  }
  return {nodes:[...nodes.values()],edges:[...edges.values()]};
}
function svgNode(tag,attrs={}){const n=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));return n;}
const colorFor=i=>palette[i%palette.length];
function groupKey(n){return n.community!=null?"community:"+n.community:(n.repo||"Grafo")+" / "+(n.path?n.path.split("/")[0]:n.type);}
function groupName(n){return n.community!=null?(n.communityName||"Comunidade "+n.community):groupKey(n);}
function layout(nodes,edges,groups,degree){
  const pos=new Map(),keys=[...new Set(nodes.map(groupKey))];
  const centers=new Map(keys.map((k,i)=>{const a=i*2*Math.PI/Math.max(1,keys.length);return [k,keys.length===1?[450,280]:[450+Math.cos(a)*230,280+Math.sin(a)*140]];}));
  nodes.forEach((n,i)=>{const [cx,cy]=centers.get(groupKey(n));const a=i*2.399963,r=22+Math.sqrt(i+1)*12;pos.set(n.id,{x:cx+Math.cos(a)*r,y:cy+Math.sin(a)*r});});
  if(nodes.length===1){pos.set(nodes[0].id,{x:450,y:280});return pos;}
  for(let tick=0;tick<75;tick++){
    const cool=1-tick/80,delta=new Map(nodes.map(n=>[n.id,{x:0,y:0}]));
    for(let a=0;a<nodes.length;a++)for(let b=a+1;b<nodes.length;b++){const u=pos.get(nodes[a].id),v=pos.get(nodes[b].id),dx=u.x-v.x,dy=u.y-v.y,sq=Math.max(40,dx*dx+dy*dy),r=Math.sqrt(sq),f=2200/sq,px=dx/r*f,py=dy/r*f;delta.get(nodes[a].id).x+=px;delta.get(nodes[a].id).y+=py;delta.get(nodes[b].id).x-=px;delta.get(nodes[b].id).y-=py;}
    for(const e of edges){const a=pos.get(e.source),b=pos.get(e.target);if(!a||!b)continue;const dx=b.x-a.x,dy=b.y-a.y,r=Math.max(1,Math.hypot(dx,dy)),f=(r-78)*0.035;delta.get(e.source).x+=dx/r*f;delta.get(e.source).y+=dy/r*f;delta.get(e.target).x-=dx/r*f;delta.get(e.target).y-=dy/r*f;}
    for(const n of nodes){const p=pos.get(n.id),d=delta.get(n.id),center=centers.get(groupKey(n));p.x=Math.max(40,Math.min(860,p.x+(d.x+(center[0]-p.x)*.008)*cool));p.y=Math.max(35,Math.min(515,p.y+(d.y+(center[1]-p.y)*.008)*cool));}
  }
  return pos;
}
function applyCamera(){const layer=$("graph").querySelector(".graph-world");if(layer)layer.setAttribute("transform","translate("+camera.x+" "+camera.y+") scale("+camera.z+")");}
function zoom(f){const z=Math.max(.35,Math.min(5,camera.z*f)),r=z/camera.z;camera.x=450-(450-camera.x)*r;camera.y=280-(280-camera.y)*r;camera.z=z;applyCamera();}
function fit(){camera={x:0,y:0,z:1};applyCamera();}
function renderGraph(){
  const svg=$("graph");clear(svg);clear($("graph-neighbors"));clear($("graph-source"));clear($("graph-groups"));
  const g=graphData||structuralGraph(state.matches),all=new Map(g.nodes.map(n=>[n.id,n]));
  const groups=new Map(),degree=new Map(),adj=new Map(),conf=$("confidence").value;
  for(const n of g.nodes){const k=groupKey(n);if(!groups.has(k))groups.set(k,{label:groupName(n),members:[],color:colorFor(groups.size)});groups.get(k).members.push(n.id);}
  const eligible=g.edges.filter(e=>!conf||e.confidence===conf);
  for(const e of eligible){for(const [id,other] of [[e.source,e.target],[e.target,e.source]]){degree.set(id,(degree.get(id)||0)+1);if(!adj.has(id))adj.set(id,[]);adj.get(id).push({id:other,edge:e});}}
  const hasCommunity=g.nodes.some(n=>n.community!=null);
  $("group-title").textContent=hasCommunity?"Comunidades":"Grupos estruturais";
  $("group-description").textContent=hasCommunity?"Comunidades importadas do grafo.":"Por repositório e diretório/tipo, sem inferir comunidades semânticas.";
  for(const [key,item] of [...groups.entries()].sort((a,b)=>b[1].members.length-a[1].members.length).slice(0,60)){const button=element("button","group-filter");button.type="button";button.setAttribute("aria-pressed",String(activeGroup===key));const dot=element("span","group-dot");const dotSvg=svgNode("svg",{viewBox:"0 0 12 12",width:12,height:12,"aria-hidden":"true"});dotSvg.append(svgNode("circle",{cx:6,cy:6,r:5,fill:item.color}));dot.append(dotSvg);button.append(dot,element("span","group-name",item.label),element("span","group-count",String(item.members.length)));button.addEventListener("click",()=>{activeGroup=activeGroup===key?"":key;focusId=null;fit();renderGraph();});$("graph-groups").append(button);}
  let candidates=g.nodes.filter(n=>!activeGroup||groupKey(n)===activeGroup);
  const searching=!!$("query").value.trim()||!!$("repository").value||!!$("kind").value||$("deleted").checked;
  const matchIds=new Set(state.matches.map(r=>r.graphId).filter(Boolean));
  if(graphData&&searching&&!focusId)candidates=candidates.filter(n=>matchIds.has(n.id));
  const mode=$("graph-mode").value,aggregate=!focusId&&!activeGroup&&!searching&&(mode==="groups"||(mode==="auto"&&candidates.length>85));
  let visible=[],edges=[];
  if(aggregate){
    const counts=new Map(),idFor=k=>"aggregate:"+k;
    for(const n of candidates){const k=groupKey(n);counts.set(k,(counts.get(k)||0)+1);}
    visible=[...counts.entries()].sort((a,b)=>b[1]-a[1]).slice(0,100).map(([key,count])=>({id:idFor(key),label:groups.get(key).label,type:"Grupo",repo:"",path:"",sha:"",group:key,memberCount:count,community:null}));
    const ids=new Set(visible.map(n=>n.id)),combined=new Map();
    for(const e of eligible){const a=groupKey(all.get(e.source)),b=groupKey(all.get(e.target));if(a===b||!ids.has(idFor(a))||!ids.has(idFor(b)))continue;const key=JSON.stringify([a,b,e.confidence]);if(!combined.has(key))combined.set(key,{source:idFor(a),target:idFor(b),type:"0 conexões",confidence:e.confidence,count:0});const v=combined.get(key);v.count++;v.type=v.count+" conexões";}
    edges=[...combined.values()];
  }else{
    const ids=new Set(),allowed=new Set(candidates.map(n=>n.id)),rank=(a,b)=>(degree.get(b.id)||0)-(degree.get(a.id)||0)||a.label.localeCompare(b.label);
    if(focusId&&all.has(focusId)){
      ids.add(focusId);let front=[focusId];
      for(let hop=0;hop<Number($("graph-hops").value)&&front.length&&ids.size<100;hop++){const next=[];for(const id of front)for(const other of (adj.get(id)||[])){if(ids.size>=100)break;if(!ids.has(other.id)&&(!activeGroup||allowed.has(other.id))){ids.add(other.id);next.push(other.id);}}front=next;}
    }else{for(const n of candidates.slice().sort(rank).slice(0,100))ids.add(n.id);}
    visible=[...ids].map(id=>all.get(id)).filter(Boolean);edges=eligible.filter(e=>ids.has(e.source)&&ids.has(e.target)).slice(0,800);
  }
  const world=svgNode("g",{class:"graph-world"});svg.append(world);
  const pos=layout(visible,edges,groups,degree),maxDegree=Math.max(1,...visible.map(n=>n.memberCount||degree.get(n.id)||1));
  for(const e of edges){const a=pos.get(e.source),b=pos.get(e.target);if(!a||!b)continue;const line=svgNode("line",{x1:a.x,y1:a.y,x2:b.x,y2:b.y,class:e.confidence==="EXTRACTED"?"graph-edge":"graph-edge graph-dashed"});const tip=svgNode("title");tip.textContent=e.type+" · "+e.confidence;line.append(tip);world.append(line);}
  for(const n of visible){const p=pos.get(n.id),radius=7+Math.sqrt((n.memberCount||degree.get(n.id)||1)/maxDegree)*13;const group=svgNode("g",{class:"graph-node "+(n.id===focusId?"selected":""),tabindex:0,role:"button","aria-label":n.label});const hit=svgNode("circle",{cx:p.x,cy:p.y,r:Math.max(25,radius),fill:"transparent",class:"graph-hit"});const circle=svgNode("circle",{cx:p.x,cy:p.y,r:radius,fill:groups.get(n.group||groupKey(n))?.color||palette[0]});const label=svgNode("text",{x:p.x,y:p.y+radius+13,"text-anchor":"middle"});label.textContent=(n.label.length>29?n.label.slice(0,27)+"…":n.label)+(n.memberCount?" ("+n.memberCount+")":"");const title=svgNode("title");title.textContent=n.label;group.append(hit,circle,label,title);const select=()=>{if(n.group){activeGroup=n.group;focusId=null;}else focusId=n.id;fit();renderGraph();};group.addEventListener("click",select);group.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();select();}});world.append(group);}
  $("graph-meta").textContent=graphOrigin+" · "+g.nodes.length.toLocaleString("pt-BR")+" nós · "+g.edges.length.toLocaleString("pt-BR")+" relações · "+visible.length+" "+(aggregate?"grupos":"nós")+" visíveis";
  if(!visible.length){const txt=svgNode("text",{x:450,y:280,"text-anchor":"middle",fill:"#a9b4c5"});txt.textContent="Nenhum nó corresponde aos filtros.";world.append(txt);}
  const n=all.get(focusId);$("graph-detail").textContent=n?[n.label,n.type,n.repo,n.path,n.sha,n.line,n.validity].filter(Boolean).join(" · "):activeGroup?"Grupo: "+groups.get(activeGroup)?.label:"Selecione um nó ou grupo para inspecionar.";
  if(n){const count=element("p","graph-subtitle",(degree.get(n.id)||0)+" relações no filtro atual");$("graph-source").append(count);if(n.publicUrl){const a=element("a","graph-open","Abrir arquivo original ↗");a.href=n.publicUrl;a.target="_blank";a.rel="noopener noreferrer";$("graph-source").append(a);}for(const item of (adj.get(n.id)||[]).slice(0,60)){const other=all.get(item.id);if(!other)continue;const btn=element("button","neighbor");btn.append(element("strong","",other.label),element("span","",item.edge.type+" · "+item.edge.confidence+(item.edge.evidence?" · "+item.edge.evidence:"")));btn.addEventListener("click",()=>{focusId=other.id;activeGroup="";fit();renderGraph();});$("graph-neighbors").append(btn);}}
  applyCamera();
}
$("confidence").addEventListener("change",renderGraph);
$("graph-hops").addEventListener("change",renderGraph);
$("graph-mode").addEventListener("change",()=>{focusId=null;activeGroup="";fit();renderGraph();});
$("graph-reset").addEventListener("click",()=>{focusId=null;activeGroup="";fit();renderGraph();});
$("zoom-out").addEventListener("click",()=>zoom(1/1.25));$("zoom-in").addEventListener("click",()=>zoom(1.25));$("graph-fit").addEventListener("click",fit);
let drag=null;const graphSvg=$("graph");
graphSvg.addEventListener("pointerdown",e=>{if(e.target.closest(".graph-node"))return;drag={x:e.clientX,y:e.clientY};graphSvg.setPointerCapture(e.pointerId);});
graphSvg.addEventListener("pointermove",e=>{if(!drag)return;const rect=graphSvg.getBoundingClientRect(),scale=Math.min(rect.width/900,rect.height/560)||1;camera.x+=(e.clientX-drag.x)/scale;camera.y+=(e.clientY-drag.y)/scale;drag={x:e.clientX,y:e.clientY};applyCamera();});
for(const event of ["pointerup","pointercancel","lostpointercapture"])graphSvg.addEventListener(event,()=>drag=null);
graphSvg.addEventListener("wheel",e=>{if(!e.ctrlKey)return;e.preventDefault();zoom(e.deltaY<0?1.1:1/1.1);},{passive:false});
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
// Public, bounded snapshot paths. No private archive export is bundled.
const snapshots=[{"repo":"exams-app-old","sha":"b86b70c304e574022416e8e2ecdc3816f1b386f1","paths":["src/app/_components/web-vitals.tsx","src/app/error.tsx","src/app/global-error.tsx","src/app/layout.tsx","src/app/loading.tsx","src/app/not-found.tsx","src/app/page.tsx","docs/adr/0001-configure-agents-dev-cli.md","docs/adr/0002-add-basic-skills.md","docs/adr/0003-create-next-app.md","docs/adr/0004-native-nextjs-foundations.md","docs/adr/0005-production-baseline-and-testing.md","src/app/api/health/route.ts","src/app/globals.css","src/instrumentation-client.ts","src/instrumentation.ts","src/lib/env.ts","src/lib/flags.ts","src/proxy.ts","src/test/setup.ts"]},{"repo":"exams-app-antigo-2","sha":"b6ece41f0568c94c6ccb7655e8e973f926801afc","paths":["prototype/artifact-simulation.html","prototype/board-exam-app__index.html","prototype/boards/index.html","prototype/claude-storage-test__index.html","prototype/exam-app-0.1.0__index.html","prototype/exam-app-0.1.1__index.html","prototype/gallery.html","prototype/mestre.html","prototype/00-mapa-geral.md","prototype/0001-prototipo-estatico-sem-build.md","prototype/0002-ia-via-capacidade-sample.md","prototype/0003-persistencia-offline-first-outbox.md","prototype/01-produto-e-dominio.md","prototype/02-workspace-e-ux.md","prototype/03-fluxos-de-estudo.md","prototype/04-arquitetura-tecnica.md","prototype/05-pesquisa-e-decisoes.md","prototype/06-evidencias-e-qualidade.md","prototype/07-entrega-e-arquivo.md","prototype/231-skills-m3-apple.md","prototype/analise-examtopics.md","prototype/analise-qconcursos.md","prototype/app/README.md","prototype/archive/README.md","prototype/arquitetura-informacao-navegacao.md","prototype/board-mestre.md","prototype/BOARD.md","prototype/boards/01-produto/README.md","prototype/boards/02-design/README.md","prototype/boards/03-estudos/README.md","prototype/boards/04-arquitetura/README.md","prototype/boards/05-pesquisas/README.md","prototype/boards/06-evidencias/README.md","prototype/boards/06-evidencias/relatorios/issue278-phase2a.md","prototype/boards/06-evidencias/relatorios/issue278-phase2b.md","prototype/boards/07-releases-historico/README.md","prototype/boards/data/README.md","prototype/boards/README.md","prototype/c4.md","prototype/capacities-issue-32-2026-11-15.md","prototype/CATALOG.md","prototype/CLAUDE_STORAGE_API_INTEGRATION.md","prototype/CLAUDE_STORAGE_BRIDGE_INVESTIGATION.md","prototype/claude-storage-sync.js","prototype/claude-storage.md","prototype/comparacao-prototipo-dev.md","prototype/componentes-ui-padroes-2026.md","prototype/data-visualization-dashboards-2026.md","prototype/docs__architecture__adr__README.md","prototype/docs__architecture__README.md","prototype/docs__archives__README.md","prototype/docs__board__README.md","prototype/docs__features__README.md","prototype/docs__planning__README.md","prototype/docs__research__pesquisas__230-estrategia-questoes__README.md","prototype/dominio.md","prototype/estado-atual.md","prototype/evidencias-examtopics-2026-11-17.md","prototype/exam-app-0.1.0__pdf.min.js","prototype/exam-app-0.1.0__pdf.worker.min.js"]}];
function initialGraph(){
  const nodes=[],edges=[],seen=new Set();
  function add(n){if(!seen.has(n.id)){seen.add(n.id);nodes.push(n);}return n.id;}
  function edge(source,target){edges.push({source,target,type:"CONTAINS",confidence:"EXTRACTED"});}
  for(const s of [...snapshots,{repo:"exams-app-archive",sha:"",paths:catalog.map(x=>x[0])}]){
    const root=add({id:"repo:"+s.repo,label:s.repo,repo:s.repo,type:"Repo",path:"",sha:s.sha});
    for(const path of s.paths){const dir=path.includes("/")?path.split("/")[0]:"root";const folderId="dir:"+s.repo+":"+dir;const isNew=!seen.has(folderId);add({id:folderId,label:dir,repo:s.repo,type:"Directory",path:dir,sha:s.sha});if(isNew)edge(root,folderId);
      const id=add({id:"file:"+s.repo+":"+path,label:path.split("/").pop(),repo:s.repo,path,sha:s.sha,type:/\.(tsx|jsx)$/.test(path)?"Component":/\.md$/.test(path)?"Document":"File",publicUrl:"https://github.com/ianmaciel7/"+s.repo+"/blob/"+(s.sha||"main")+"/"+path.split("/").map(encodeURIComponent).join("/")});edge(folderId,id);
    }
  }
  return {nodes,edges};
}
graphData=initialGraph();
const descriptions=new Map(catalog);
state.records=graphData.nodes.map(n=>({repository:n.repo,kind:"node",sha:n.sha,path:n.path,summary:descriptions.get(n.path)||n.label,graphId:n.id,publicPath:n.repo==="exams-app-archive"&&descriptions.has(n.path)?n.path:undefined}));
$("dataset").textContent="Catálogo público · amostra verificada";
state.loaded=true;updateFilters();filter();
