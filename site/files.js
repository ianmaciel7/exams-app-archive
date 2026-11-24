"use strict";
const $=id=>document.getElementById(id);
const publicRepos=new Set();
let publicSnapshots=[];
async function loadPublicSources(){try{const r=await fetch("./catalog.json",{credentials:"omit",cache:"no-cache"});if(!r.ok)throw Error("HTTP "+r.status);const data=await r.json();if(data.version!==2)throw Error("Formato inválido");publicSnapshots=data.snapshots;for(const s of publicSnapshots){if(/^[A-Za-z0-9_.-]+$/.test(s.repo))publicRepos.add(s.repo);}const select=$("source-repo");select.replaceChildren(...[...publicRepos].sort().map(r=>new Option(r,r)));refreshRefs();$("load-public").disabled=!publicRepos.size;status("Catálogo público carregado.");}catch(e){status("Catálogo indisponível: "+e.message+". Use uma pasta local.");}}
function refreshRefs(){const repo=$("source-repo").value,sel=$("source-ref");sel.replaceChildren();for(const s of publicSnapshots.filter(s=>s.repo===repo))for(const ref of s.refs)sel.append(new Option(ref,s.sha));}
const state={mode:"",repo:"",sha:"",entries:[],selected:null,expanded:new Set(),epoch:0,url:null};
const limit=2*1024*1024;
const isReact=p=>/\.(tsx|jsx)$/i.test(p);
const isHtml=p=>/\.html?$/i.test(p);
const mime=p=>({png:"image/png",jpg:"image/jpeg",jpeg:"image/jpeg",webp:"image/webp",gif:"image/gif"}[p.split(".").pop().toLowerCase()]||"");
function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function status(s){$("file-status").textContent=s;}
function pathEncoded(path){return path.split("/").map(encodeURIComponent).join("/");}
async function api(repo,endpoint){
  if(!publicRepos.has(repo))throw Error("Origem não permitida.");
  const response=await fetch("https://api.github.com/repos/ianmaciel7/"+repo+"/"+endpoint,{credentials:"omit",redirect:"error",referrerPolicy:"no-referrer",headers:{Accept:"application/vnd.github+json"}});
  if(!response.ok)throw Error("GitHub HTTP "+response.status+" (limite público ou revisão indisponível)");
  return response.json();
}
function resetPreview(){const frame=$("preview-frame");frame.removeAttribute("srcdoc");frame.setAttribute("sandbox","");frame.hidden=true;$("preview-image").hidden=true;$("preview-image").removeAttribute("src");if(state.url){URL.revokeObjectURL(state.url);state.url=null;}}
function clearSelection(){state.selected=null;resetPreview();$("selected-path").textContent="Nenhum arquivo selecionado";$("source-code").textContent="Selecione um arquivo na árvore.";$("source-info").textContent="";$("source-link").hidden=true;$("preview-tab").disabled=true;$("component-help").hidden=true;tab(false);}
function tab(preview){$("source-code").hidden=preview;$("preview-area").hidden=!preview;$("code-tab").setAttribute("aria-pressed",String(!preview));$("preview-tab").setAttribute("aria-pressed",String(preview));}
function renderTree(){
  const root=$("tree");root.replaceChildren();
  const query=$("tree-search").value.trim().toLowerCase(),only=$("components-only").checked;
  const filtered=state.entries.filter(e=>(!only||isReact(e.path))&&(!query||e.path.toLowerCase().includes(query)));
  const tree={children:new Map(),entry:null};
  for(const e of filtered){
    let cur=tree;for(const part of e.path.split("/")){if(!cur.children.has(part))cur.children.set(part,{children:new Map(),entry:null});cur=cur.children.get(part);}cur.entry=e;
  }
  let shown=0;
  function walk(parent,branch,prefix,depth){
    const entries=[...branch.children.entries()].sort((a,b)=>Number(!a[1].children.size)-Number(!b[1].children.size)||a[0].localeCompare(b[0]));
    for(const [name,item] of entries){
      if(shown++>=1500)return;
      const path=prefix?prefix+"/"+name:name,folder=item.children.size>0;
      const row=node("button",undefined,"tree-row");row.type="button";
      const indent=node("span",undefined,"tree-indent");indent.textContent="\u00a0".repeat(Math.min(depth,12)*3);row.append(indent,node("span",folder?(state.expanded.has(path)||query?"▾":"▸"):(isReact(path)?"R":"·"),"tree-glyph"),node("span",name,"tree-name"));row.title=path;
      if(folder){const open=state.expanded.has(path)||!!query;row.setAttribute("aria-expanded",String(open));row.addEventListener("click",()=>{if(state.expanded.has(path))state.expanded.delete(path);else state.expanded.add(path);renderTree();});parent.append(row);if(open)walk(parent,item,path,depth+1);}
      else{row.setAttribute("aria-current",String(state.selected?.path===path));row.addEventListener("click",()=>select(item.entry));parent.append(row);}
    }
  }
  walk(root,tree,"",0);
  if(!filtered.length)root.append(node("p","Nenhum arquivo nesta seleção.","hint"));
  if(shown>=1500)root.append(node("p","Exibição limitada; use o filtro para restringir.","hint"));
}
function install(mode,entries,repo="",sha=""){
  state.mode=mode;state.repo=repo;state.sha=sha;state.entries=entries;state.expanded=new Set();$("tree-search").value="";$("components-only").checked=false;clearSelection();renderTree();status(entries.length+" arquivos · "+(mode==="public"?repo+" @ "+sha.slice(0,12):"pasta local"));
}
$("load-refs").addEventListener("click",loadPublicSources);
$("source-repo").addEventListener("change",refreshRefs);
$("load-public").addEventListener("click",async()=>{
  const epoch=++state.epoch,repo=$("source-repo").value,ref=$("source-ref").value;
  try{const snapshot=publicSnapshots.find(s=>s.repo===repo&&s.sha===ref);if(!snapshot)throw Error("Revisão não encontrada no catálogo.");if(epoch!==state.epoch)return;install("public",snapshot.files.map(x=>({path:x.path,size:x.size,blob:x.blob})),repo,ref);
  }catch(e){if(epoch===state.epoch)status(e.message);}
});
for(const id of ["local-folder","local-files"]){$(id).addEventListener("change",e=>{++state.epoch;const files=[...e.target.files];if(files.length)install("local",files.map(file=>({path:file.webkitRelativePath||file.name,size:file.size,file})));e.target.value="";});}
$("tree-search").addEventListener("input",renderTree);$("components-only").addEventListener("change",renderTree);
async function select(entry){
  if(!entry)return;const epoch=++state.epoch;resetPreview();state.selected=entry;renderTree();tab(false);$("selected-path").textContent=entry.path;$("source-info").textContent=(entry.size??0).toLocaleString("pt-BR")+" bytes · "+(state.mode==="public"?state.sha:"Local");
  $("source-code").textContent="Carregando…";$("component-help").hidden=!isReact(entry.path);$("preview-tab").disabled=true;$("source-link").hidden=state.mode!=="public";
  if(state.mode==="public")$("source-link").href="https://github.com/ianmaciel7/"+state.repo+"/blob/"+state.sha+"/"+pathEncoded(entry.path);
  try{
    if(entry.size>limit)throw Error("Arquivo acima de 2 MiB. Abra o original ou recupere localmente.");
    let bytes;
    if(state.mode==="local")bytes=new Uint8Array(await entry.file.arrayBuffer());
    else{const data=await api(state.repo,"git/blobs/"+entry.blob);if(data.encoding!=="base64")throw Error("Formato de blob não suportado.");bytes=Uint8Array.from(atob(data.content.replace(/\s/g,"")),c=>c.charCodeAt(0));}
    if(epoch!==state.epoch)return;
    const imageType=mime(entry.path);
    if(imageType){state.url=URL.createObjectURL(new Blob([bytes],{type:imageType}));$("preview-image").src=state.url;$("preview-image").hidden=false;$("render-preview").hidden=true;$("render-live").hidden=true;$("preview-note").textContent="Imagem original.";$("source-code").textContent="Arquivo de imagem binário.";$("preview-tab").disabled=false;tab(true);return;}
    if(bytes.includes(0))throw Error("Arquivo binário sem visualização.");
    entry.text=new TextDecoder("utf-8",{fatal:true}).decode(bytes);$("source-code").textContent=entry.text;
    if(isHtml(entry.path)){$("preview-tab").disabled=false;$("render-preview").hidden=false;$("render-live").hidden=state.mode!=="local";$("preview-note").textContent="HTML isolado. Scripts bloqueados no modo estático. Builds locais revisados podem ser executados por escolha explícita.";}
  }catch(e){if(epoch===state.epoch)$("source-code").textContent=e.message;}
}
$("code-tab").addEventListener("click",()=>tab(false));$("preview-tab").addEventListener("click",()=>tab(true));
function render(live){
  const entry=state.selected;if(!entry||!isHtml(entry.path)||typeof entry.text!=="string")return;
  if(live&&(state.mode!=="local"||!confirm("Executar este build local? Use apenas código que você revisou. O sandbox reduz riscos, mas não substitui isolamento de sistema.")))return;
  resetPreview();const frame=$("preview-frame");
  frame.setAttribute("sandbox",live?"allow-scripts":"");
  const policy="default-src 'none'; script-src "+(live?"'unsafe-inline'":"'none'")+"; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'";
  frame.srcdoc='<!doctype html><meta http-equiv="Content-Security-Policy" content="'+policy+'">'+entry.text;frame.hidden=false;
}
$("render-preview").addEventListener("click",()=>render(false));$("render-live").addEventListener("click",()=>render(true));

loadPublicSources();
