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
import { cva } from "class-variance-authority";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs) {
  return twMerge(clsx(inputs));
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
      if (spec === "clsx") return { __esModule: true, default: clsx, clsx };
      if (spec === "tailwind-merge") return { __esModule: true, twMerge };
      if (spec === "cn" || spec === "@/lib/utils" || spec.endsWith("/lib/utils")) return { __esModule: true, default: cn, cn };
      if (spec === "class-variance-authority") return { __esModule: true, cva };
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
      if (spec === "@base-ui/react/button") {
        const BaseBtn = React.forwardRef(({ render, nativeButton, ...props }, ref) =>
          React.createElement("button", { ref, type: props.type || "button", ...props })
        );
        return { __esModule: true, Button: BaseBtn, default: BaseBtn };
      }
      if (spec === "@base-ui/react/merge-props") {
        return {
          __esModule: true,
          mergeProps: (...objs) => Object.assign({}, ...objs.filter((o) => o && typeof o === "object")),
        };
      }
      if (spec === "@base-ui/react/use-render") {
        return {
          __esModule: true,
          useRender: ({ defaultTagName = "div", props = {}, render } = {}) => {
            const clean = { ...props };
            delete clean.render;
            if (typeof render === "function") return render(clean);
            if (React.isValidElement(render)) return React.cloneElement(render, clean);
            return React.createElement(defaultTagName || "div", clean);
          },
        };
      }
      if (spec.endsWith(".css") || spec.endsWith(".scss")) return {};
      const resolved = resolveFromMap(files, modPath, spec);
      if (resolved) return loadModule(resolved);
      return makeFallbackModule(spec);
    }

    const key = "__archiveMod_" + Math.random().toString(36).slice(2);
    const scriptEl = document.createElement("script");
    scriptEl.textContent = "window[" + JSON.stringify(key) + "] = function(require, module, exports, React) {\\n" + compiled + "\\n};";
    document.head.appendChild(scriptEl);
    scriptEl.remove();
    const fn = window[key];
    delete window[key];
    if (typeof fn !== "function") throw new Error("Falha ao carregar modulo transpilado.");
    fn(localRequire, mod, mod.exports, React);
    return mod.exports;
  }

  function StageShell({ title, children }) {
    const [dark, setDark] = React.useState(false);
    React.useEffect(() => {
      document.documentElement.classList.toggle("dark", dark);
    }, [dark]);
    return React.createElement(
      "div",
      { className: "min-h-screen flex flex-col bg-background text-foreground" },
      React.createElement(
        "div",
        { className: "flex items-center justify-between gap-2 px-3.5 py-2 border-b border-border bg-muted/40 text-xs text-muted-foreground" },
        React.createElement("span", { className: "truncate" }, title),
        React.createElement(
          "button",
          {
            type: "button",
            onClick: () => setDark((d) => !d),
            className: "px-2.5 py-1 rounded-md border border-border bg-background text-foreground font-medium hover:bg-accent",
          },
          dark ? "Tema claro" : "Tema escuro"
        )
      ),
      React.createElement("div", { className: "p-6 flex-1 flex flex-col items-center gap-6" }, children)
    );
  }

  const root = createRoot(container);
  try {
    const exportsObj = loadModule(entryPath);
    const exportedNames = Object.keys(exportsObj).filter((k) => k !== "__esModule");

    let element = null;
    const isStoryFile = /\.stories\.(tsx|jsx)$/i.test(entryPath);
    if (isStoryFile) {
      const stories = exportedNames.filter((n) => n !== "default" && typeof exportsObj[n] === "function");
      if (stories.length) {
        element = React.createElement(
          "div",
          { className: "w-full max-w-2xl flex flex-col gap-5" },
          stories.map((name) => {
            const StoryComp = exportsObj[name];
            const storyArgs = StoryComp.args || {};
            return React.createElement(
              "section",
              { key: name, className: "rounded-xl border border-border bg-card p-5 shadow-xs" },
              React.createElement("div", { className: "text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3" }, name),
              React.createElement("div", { className: "flex flex-wrap items-center gap-3" }, React.createElement(StoryComp, storyArgs))
            );
          })
        );
      }
    }

    if (!element && exportsObj.SidebarProvider && exportsObj.Sidebar && exportsObj.SidebarMenu && exportsObj.SidebarMenuButton) {
      const {
        SidebarProvider,
        Sidebar,
        SidebarHeader,
        SidebarContent,
        SidebarGroup,
        SidebarGroupLabel,
        SidebarGroupContent,
        SidebarMenu,
        SidebarMenuItem,
        SidebarMenuButton,
      } = exportsObj;
      const navItems = [
        { label: "Inicio", active: true },
        { label: "Questoes", active: false },
        { label: "Simulados", active: false },
        { label: "Caderno de Erros", active: false },
        { label: "Revisao", active: false },
      ];
      const menuItems = navItems.map((item) =>
        React.createElement(
          SidebarMenuItem,
          { key: item.label },
          React.createElement(SidebarMenuButton, { isActive: item.active }, item.label)
        )
      );
      const menu = React.createElement(SidebarMenu, null, menuItems);
      const groupInner = SidebarGroupContent ? React.createElement(SidebarGroupContent, null, menu) : menu;
      const group = SidebarGroup
        ? React.createElement(
            SidebarGroup,
            null,
            SidebarGroupLabel ? React.createElement(SidebarGroupLabel, null, "Navegacao") : null,
            groupInner
          )
        : groupInner;
      const content = SidebarContent ? React.createElement(SidebarContent, null, group) : group;
      const header = SidebarHeader ? React.createElement(SidebarHeader, null, React.createElement("strong", { className: "px-2 py-1 text-sm font-semibold" }, "Exams App")) : null;
      element = React.createElement(
        "div",
        { className: "rounded-xl border border-border overflow-hidden shadow-sm bg-sidebar text-sidebar-foreground w-64" },
        React.createElement(
          SidebarProvider,
          { defaultOpen: true, className: "min-h-0" },
          React.createElement(Sidebar, { collapsible: "none", className: "w-full" }, header, content)
        )
      );
    }

    if (!element) {
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
      element = React.createElement(Comp, sampleProps);
      if (Provider && Provider !== Comp) {
        element = React.createElement(Provider, { defaultOpen: true }, element);
      }
    }

    root.render(
      React.createElement(
        PreviewErrorBoundary,
        null,
        React.createElement(
          StageShell,
          { title: (isStoryFile ? "Ladle Stories · " : "Preview TSX · ") + entryPath + " · " + exportedNames.length + " exports" },
          element
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
