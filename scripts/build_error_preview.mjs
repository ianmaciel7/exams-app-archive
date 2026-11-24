// Interactive build of one explicitly reviewed historical React component.
import {createRequire} from "node:module";
import {readFileSync,writeFileSync,mkdirSync} from "node:fs";
import {resolve,dirname} from "node:path";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";
const [deps,output]=process.argv.slice(2);
if(!deps||!output)throw Error("Usage: node scripts/build_error_preview.mjs DEPS OUTPUT");
const sourcePath=fileURLToPath(new URL("../previews/error/source.tsx",import.meta.url));
const source=readFileSync(sourcePath);
const blob=createHash("sha1").update("blob "+source.length+"\0").update(source).digest("hex");
if(blob!=="936e638aa231a2533e866c12e4d97a429c524d6c")throw Error("Unreviewed source");
const req=createRequire(resolve(deps,"package.json"));
const esbuild=req("esbuild");
const entry=`import React,{useState} from "react";
import {createRoot} from "react-dom/client";
import ErrorBoundary from ${JSON.stringify(sourcePath)};
function Fixture(){const [count,setCount]=useState(0);const [dark,setDark]=useState(false);
return <><header className="fixture"><span>Historical component · ErrorBoundary</span><button type="button" onClick={()=>{document.documentElement.dataset.theme=dark?"light":"dark";setDark(!dark)}}>{dark?"Light":"Dark"} theme</button></header><main id="component-root"><ErrorBoundary error={new Error("Fixture error")} reset={()=>setCount(n=>n+1)}/></main><footer className="fixture" role="status" id="retry-status">Fixture reset calls: {count}</footer></>;}
createRoot(document.getElementById("root")).render(<Fixture/>);`;
const result=await esbuild.build({stdin:{contents:entry,loader:"tsx",resolveDir:dirname(sourcePath)},nodePaths:[resolve(deps,"node_modules")],bundle:true,write:false,jsx:"automatic",platform:"browser",format:"iife",minify:true,define:{"process.env.NODE_ENV":'"production"'}});
const script=result.outputFiles[0].text.replace(/<\/script/gi,"<\\/script");
const hash=createHash("sha256").update(script).digest("base64");
const css=`*{box-sizing:border-box}html{color-scheme:light}body{margin:0;background:white;color:#171717;font-family:Arial,Helvetica,sans-serif}html[data-theme=dark]{color-scheme:dark}html[data-theme=dark] body{background:#0a0a0a;color:#ededed}.fixture{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:14px 18px;font:13px system-ui;border-bottom:1px solid #8885}.fixture button{font:inherit;padding:6px 12px}.flex{display:flex}.flex-col{flex-direction:column}.items-center{align-items:center}.justify-center{justify-content:center}.p-4{padding:1rem}.min-h-\\[50vh\\]{min-height:50vh}h2,p{margin:0}.text-xl{font-size:1.25rem;line-height:1.75rem}.font-semibold{font-weight:600}.text-muted-foreground{color:#777}.mt-1{margin-top:.25rem}.text-sm{font-size:.875rem;line-height:1.25rem}.mt-4{margin-top:1rem}.rounded{border-radius:.25rem}.bg-black{background:#000}.px-4{padding-inline:1rem}.py-2{padding-block:.5rem}.text-white{color:#fff}button{cursor:pointer;border:0;font-family:inherit}html[data-theme=dark] .dark\\:bg-white{background:#fff}html[data-theme=dark] .dark\\:text-black{color:#000}footer.fixture{border-top:1px solid #8885;border-bottom:0}`;
mkdirSync(dirname(resolve(output)),{recursive:true});
writeFileSync(output,`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'sha256-${hash}'; style-src 'unsafe-inline'; object-src 'none'; base-uri 'none'; form-action 'none'; connect-src 'none'"><title>ErrorBoundary · interactive React</title><style>${css}</style></head><body><div id="root"></div><script>${script}</script></body></html>`);
console.log("Built reviewed interactive source",blob);
