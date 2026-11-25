#!/usr/bin/env node
/**
 * Build a self-contained, same-origin browser TSX/JSX preview runtime
 * using React, ReactDOM, and Sucrase (bundled via esbuild).
 *
 * Usage: node scripts/build_tsx_runtime.mjs <deps-prefix> <output-js>
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const [depsPrefix, outFile] = process.argv.slice(2);
if (!depsPrefix || !outFile) {
  console.error("Usage: node scripts/build_tsx_runtime.mjs <deps-prefix> <output-js>");
  process.exit(1);
}

const require = createRequire(path.resolve(depsPrefix, "node_modules", "esbuild", "package.json"));
const esbuild = require(path.resolve(depsPrefix, "node_modules", "esbuild"));

const entrySource = `
import * as React from "react";
import * as ReactDOM from "react-dom";
import { createRoot } from "react-dom/client";
import * as jsxRuntime from "react/jsx-runtime";
import { transform } from "sucrase";

function cn(...inputs) {
  const out = [];
  for (const x of inputs) {
    if (!x) continue;
    if (typeof x === "string") out.push(x);
    else if (Array.isArray(x)) out.push(cn(...x));
    else if (typeof x === "object") {
      for (const [k, v] of Object.entries(x)) if (v) out.push(k);
    }
  }
  return out.filter(Boolean).join(" ");
}

function makeIconProxy() {
  return new Proxy({}, {
    get(_, prop) {
      if (prop === "__esModule") return true;
      if (prop === "default") return makeIconProxy();
      const Icon = React.forwardRef(function ArchiveIcon(props, ref) {
        const size = props.size || 16;
        return React.createElement(
          "svg",
          {
            ref,
            width: size,
            height: size,
            viewBox: "0 0 24 24",
            fill: "none",
            stroke: "currentColor",
            strokeWidth: props.strokeWidth || 1.8,
            strokeLinecap: "round",
            strokeLinejoin: "round",
            className: props.className,
            style: props.style,
            "aria-hidden": "true",
            "data-icon": String(prop),
          },
          React.createElement("rect", { x: 4, y: 4, width: 16, height: 16, rx: 3 }),
          React.createElement("path", { d: "M9 12h6" })
        );
      });
      Icon.displayName = String(prop);
      return Icon;
    },
  });
}

function makeFallbackModule(name) {
  const FallbackComponent = React.forwardRef(function ArchiveFallback(props, ref) {
    const tag = props.asChild ? React.Fragment : "div";
    const pass = props.asChild
      ? {}
      : { ref, className: props.className, style: props.style, "data-mock": name };
    return React.createElement(tag, pass, props.children);
  });
  return new Proxy(FallbackComponent, {
    get(target, prop) {
      if (prop === "__esModule") return true;
      if (prop === "default") return FallbackComponent;
      if (prop === "cn" || prop === "clsx" || prop === "twMerge") return cn;
      if (prop === "cva") return (base) => () => base || "";
      if (prop === "Slot") return FallbackComponent;
      if (prop === "AnimatePresence" || prop === "MotionConfig") {
        return ({ children }) => React.createElement(React.Fragment, null, children);
      }
      if (prop === "motion") {
        return new Proxy({}, {
          get(__, tag) {
            return React.forwardRef((props, ref) => {
              const clean = {};
              for (const [k, v] of Object.entries(props || {})) {
                if (!["initial","animate","exit","transition","variants","whileHover","whileTap","layout","layoutId"].includes(k)) {
                  clean[k] = v;
                }
              }
              return React.createElement(typeof tag === "string" ? tag : "div", { ...clean, ref });
            });
          },
        });
      }
      if (typeof prop === "string" && /^[A-Z]/.test(prop)) {
        const Sub = React.forwardRef((props, ref) => {
          const isButton = /Trigger|Button|Close/i.test(prop);
          const tag = isButton ? "button" : "div";
          const extra = isButton ? { type: props.type || "button", onClick: props.onClick } : {};
          return React.createElement(tag, { ref, className: props.className, style: props.style, ...extra }, props.children);
        });
        Sub.displayName = prop;
        return Sub;
      }
      if (typeof prop === "string" && prop.startsWith("use")) {
        return () => ({
          push: () => {}, replace: () => {}, back: () => {}, prefetch: () => {},
          pathname: "/", query: {}, params: {},
          get: () => null, toString: () => "",
          theme: "light", setTheme: () => {},
          open: true, setOpen: () => {}, toggleSidebar: () => {}, state: "expanded", isMobile: false,
        });
      }
      return target[prop];
    },
  });
}

function normalizePath(basePath, rel) {
  const parts = basePath.split("/").slice(0, -1);
  for (const seg of rel.split("/")) {
    if (!seg || seg === ".") continue;
    if (seg === "..") parts.pop();
    else parts.push(seg);
  }
  return parts.join("/");
}

function resolveFromMap(fileMap, fromPath, spec) {
  const candidates = [];
  if (spec.startsWith("@/")) {
    const tail = spec.slice(2);
    candidates.push("src/" + tail, tail);
  } else if (spec.startsWith("./") || spec.startsWith("../")) {
    candidates.push(normalizePath(fromPath, spec));
  }
  const exts = ["", ".tsx", ".ts", ".jsx", ".js", "/index.tsx", "/index.ts", "/index.jsx", "/index.js"];
  for (const base of candidates) {
    for (const ext of exts) {
      const full = base + ext;
      if (Object.prototype.hasOwnProperty.call(fileMap, full)) return full;
    }
  }
  return null;
}

class PreviewErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return React.createElement("div", { className: "pv-error" },
        React.createElement("strong", null, "Erro ao renderizar componente"),
        React.createElement("pre", null, String(this.state.error.message || this.state.error))
      );
    }
    return this.props.children;
  }
}

window.renderArchiveComponent = function renderArchiveComponent(container, entryPath, entryCode, fileMap) {
  const files = { ...(fileMap || {}), [entryPath]: entryCode };
  const cache = new Map();
  const iconProxy = makeIconProxy();

  function loadModule(modPath) {
    if (cache.has(modPath)) return cache.get(modPath).exports;
    const mod = { exports: {} };
    cache.set(modPath, mod);
    const source = files[modPath];
    const compiled = transform(source, {
      transforms: ["typescript", "jsx", "imports"],
      jsxRuntime: "classic",
      filePath: modPath,
    }).code;

    function localRequire(spec) {
      if (spec === "react") return React;
      if (spec === "react-dom") return ReactDOM;
      if (spec === "react-dom/client") return { createRoot };
      if (spec === "react/jsx-runtime" || spec === "react/jsx-dev-runtime") return jsxRuntime;
      if (spec === "lucide-react") return iconProxy;
      if (spec === "clsx" || spec === "tailwind-merge") return { __esModule: true, default: cn, clsx: cn, twMerge: cn };
      if (spec === "class-variance-authority") return { __esModule: true, cva: (base) => () => base || "" };
      if (spec === "next/link") {
        const Link = React.forwardRef(({ href, children, ...rest }, ref) =>
          React.createElement("a", { ref, href: typeof href === "string" ? href : "#", onClick: (e) => e.preventDefault(), ...rest }, children)
        );
        return { __esModule: true, default: Link };
      }
      if (spec === "next/image") {
        const Img = ({ src, alt, ...rest }) => React.createElement("img", { src: typeof src === "string" ? src : "", alt: alt || "", ...rest });
        return { __esModule: true, default: Img };
      }
      if (spec.endsWith(".css") || spec.endsWith(".scss")) return {};
      const resolved = resolveFromMap(files, modPath, spec);
      if (resolved) return loadModule(resolved);
      return makeFallbackModule(spec);
    }

    const fn = new Function("require", "module", "exports", "React", compiled);
    fn(localRequire, mod, mod.exports, React);
    return mod.exports;
  }

  const root = createRoot(container);
  try {
    const exportsObj = loadModule(entryPath);
    const exportedNames = Object.keys(exportsObj).filter((k) => k !== "__esModule");
    let Comp = null;
    if (typeof exportsObj.default === "function" || (exportsObj.default && exportsObj.default.$$typeof)) {
      Comp = exportsObj.default;
    } else {
      for (const name of exportedNames) {
        if (/^[A-Z]/.test(name) && !/Provider|Context$/i.test(name)) {
          const val = exportsObj[name];
          if (typeof val === "function" || (val && val.$$typeof)) {
            Comp = val;
            break;
          }
        }
      }
    }

    if (!Comp) {
      root.render(React.createElement("div", { className: "pv-info" },
        React.createElement("strong", null, "Modulo carregado sem componente padrao renderizavel"),
        React.createElement("p", null, "Exportacoes encontradas: " + (exportedNames.join(", ") || "nenhuma"))
      ));
      return;
    }

    const Provider = exportsObj.SidebarProvider || exportsObj.TooltipProvider || null;
    const sampleProps = {
      title: "Preview",
      label: "Exemplo",
      children: "Conteudo de demonstracao",
      items: [
        { id: "1", title: "Inicio", label: "Inicio", href: "#" },
        { id: "2", title: "Questoes", label: "Questoes", href: "#" },
        { id: "3", title: "Caderno de erros", label: "Caderno de erros", href: "#" },
      ],
      error: new Error("Erro simulado de preview"),
      reset: () => {},
    };
    let element = React.createElement(Comp, sampleProps);
    if (Provider && Provider !== Comp) {
      element = React.createElement(Provider, { defaultOpen: true }, element);
    }

    root.render(
      React.createElement(PreviewErrorBoundary, null,
        React.createElement("div", { className: "pv-stage" },
          React.createElement("div", { className: "pv-banner" },
            "Preview experimental TSX · " + entryPath + " · Exports: " + exportedNames.slice(0, 8).join(", ")
          ),
          React.createElement("div", { className: "pv-canvas" }, element)
        )
      )
    );
  } catch (err) {
    root.render(React.createElement("div", { className: "pv-error" },
      React.createElement("strong", null, "Nao foi possivel transpilar/montar este arquivo isoladamente"),
      React.createElement("pre", null, String(err && err.message ? err.message : err))
    ));
  }
};
`;

const tmpEntry = path.resolve(depsPrefix, "_tsx_runtime_entry.mjs");
fs.writeFileSync(tmpEntry, entrySource, "utf8");

await esbuild.build({
  entryPoints: [tmpEntry],
  bundle: true,
  minify: true,
  format: "iife",
  target: ["es2020"],
  nodePaths: [path.resolve(depsPrefix, "node_modules")],
  outfile: outFile,
  define: { "process.env.NODE_ENV": '"production"' },
});

fs.unlinkSync(tmpEntry);
const stat = fs.statSync(outFile);
console.log(JSON.stringify({ runtime: outFile, bytes: stat.size }));
