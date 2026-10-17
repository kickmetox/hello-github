const S = {
  workspace: "",
  python: "",
  tabs: [],
  active: -1,
  breaks: {},
  debugLine: 0,
  debugFile: "",
  runId: "",
  runFrom: 0,
  debugFrom: 0,
  bottom: "output",
  side: "tree",
  complete: [],
  completeIndex: 0,
  ai: [],
  baseUrl: "",
  model: "",
  terminalId: "",
  terminalFrom: 0,
  coverage: {},
  watches: [],
  clip: "",
};

const BOTTOM = [
  ["output", "Ausgabe"],
  ["problems", "Probleme"],
  ["debug", "Debug"],
  ["tests", "Tests"],
  ["terminal", "Terminal"],
  ["repl", "REPL"],
  ["git", "Git"],
  ["packages", "Pakete"],
  ["search", "Suche"],
  ["todo", "TODO"],
  ["history", "Historie"],
  ["notebook", "Notebook"],
  ["http", "HTTP"],
  ["db", "Datenbank"],
  ["vars", "Variablen"],
  ["remote", "Remote"],
];

const $ = (id) => document.getElementById(id);
const codeEl = () => $("code");
const highlightEl = () => $("highlight");

function toast(message) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

async function api(path, body) {
  const opt = { credentials: "same-origin", headers: {} };
  if (body !== undefined) {
    opt.method = "POST";
    opt.headers["Content-Type"] = "application/json";
    opt.body = JSON.stringify(body);
  }
  const response = await fetch(path, opt);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || response.statusText || "Fehler");
  }
  return data;
}

function apiGet(path) {
  return api(path);
}

function tab() {
  return S.tabs[S.active] || null;
}

function esc(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function highlightPython(src, errorLines) {
  const kw = new Set("False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield match case".split(" "));
  let html = "";
  let lineBuf = "";
  let line = 1;
  let i = 0;
  let lastWord = "";
  function pushToken(text, cls) {
    const parts = text.split("\n");
    parts.forEach((part, index) => {
      const chunk = cls ? `<span class="${cls}">${esc(part)}</span>` : esc(part);
      lineBuf += chunk;
      if (index < parts.length - 1) {
        html += errorLines.has(line) ? `<span class="errline">${lineBuf}</span>\n` : lineBuf + "\n";
        lineBuf = "";
        line += 1;
      }
    });
  }
  function stringClass(raw) {
    const quote = raw.startsWith('"""') || raw.startsWith("'''") ? 3 : 1;
    const inner = raw.slice(quote, raw.length - quote);
    if (/^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|WITH|ALTER|DROP)\b/i.test(inner)) return "str inj-sql";
    if (/<\/?[a-z][^>]*>/i.test(inner)) return "str inj-html";
    const trimmed = inner.trim();
    if ((trimmed.startsWith("{") && trimmed.endsWith("}")) || (trimmed.startsWith("[") && trimmed.endsWith("]"))) {
      try { JSON.parse(trimmed); return "str inj-json"; } catch (_err) { /* weiter als String */ }
    }
    return "str";
  }
  while (i < src.length) {
    const ch = src[i];
    if (ch === "#") {
      const end = src.indexOf("\n", i);
      const stop = end === -1 ? src.length : end;
      pushToken(src.slice(i, stop), "comment");
      i = stop;
      lastWord = "";
      continue;
    }
    const prefix = src.slice(i, i + 3);
    const quoteAt = (offset) => src[i + offset] === '"' || src[i + offset] === "'";
    let q = 0;
    let start = i;
    const head = src.slice(i, i + 6);
    const pre = head.match(/^(?:[rRuUfFbB]{0,2})/);
    if (pre && quoteAt(pre[0].length)) {
      start = i;
      q = pre[0].length;
    }
    if (q || ch === '"' || ch === "'") {
      const qpos = q ? i + q : i;
      const triple = src.slice(qpos, qpos + 3);
      const quote = triple[0] === triple[1] && triple[1] === triple[2] ? triple : src[qpos];
      let j = qpos + quote.length;
      while (j < src.length && src.slice(j, j + quote.length) !== quote) {
        j += src[j] === "\\" ? 2 : 1;
      }
      j = Math.min(src.length, j + quote.length);
      const raw = src.slice(start, j);
      pushToken(raw, stringClass(raw));
      i = j;
      lastWord = "";
      continue;
    }
    if (/[0-9]/.test(ch) || (ch === "." && /[0-9]/.test(src[i + 1] || ""))) {
      const match = src.slice(i).match(/^(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d[\d_]*)?j?)/);
      if (match) {
        pushToken(match[0], "num");
        i += match[0].length;
        lastWord = "";
        continue;
      }
    }
    if (/[A-Za-z_]/.test(ch)) {
      const match = src.slice(i).match(/^[A-Za-z_][A-Za-z0-9_]*/);
      const word = match[0];
      let cls = "";
      if (kw.has(word)) cls = "kw";
      else if (lastWord === "def") cls = "fn";
      else if (lastWord === "class") cls = "cls";
      else if (src[i + word.length] === "(") cls = "fn";
      pushToken(word, cls);
      lastWord = word;
      i += word.length;
      continue;
    }
    if ("=+-*/%<>!&|^~:.,;()[]{}".includes(ch)) {
      pushToken(ch, "op");
      i += 1;
      if (!/\s/.test(ch)) lastWord = "";
      continue;
    }
    pushToken(ch, "");
    i += 1;
  }
  html += errorLines.has(line) ? `<span class="errline">${lineBuf}</span>` : lineBuf;
  return html;
}

function errorLineSet() {
  const current = tab();
  const lines = new Set();
  if (!current) return lines;
  (current.problems || []).forEach((item) => {
    if (item.severity === "error") lines.add(item.line);
  });
  return lines;
}

function renderEditor() {
  const current = tab();
  const text = current ? current.content : "";
  const area = codeEl();
  if (area.value !== text) {
    const pos = area.selectionStart;
    area.value = text;
    area.selectionStart = area.selectionEnd = Math.min(pos, text.length);
  }
  highlightEl().innerHTML = highlightPython(text, errorLineSet()) + "\n";
  renderGutter();
  renderTabs();
  syncScroll();
}

function renderGutter() {
  const current = tab();
  const text = current ? current.content : "";
  const count = text ? text.split("\n").length : 1;
  const breaks = (current && S.breaks[current.path]) || {};
  const covered = current && S.coverage[current.path];
  let html = "";
  for (let line = 1; line <= count; line += 1) {
    const classes = ["gutter-line"];
    if (breaks[line] !== undefined) classes.push("bp");
    if (S.debugFile && current && S.debugFile === current.path && S.debugLine === line) classes.push("current");
    if ((current.problems || []).some((item) => item.line === line && item.severity !== "info")) classes.push("err");
    const mark = covered && covered.missing && covered.missing.includes(line) ? "·" : "";
    html += `<div class="${classes.join(" ")}" data-line="${line}">${mark}${line}</div>`;
  }
  $("gutter").innerHTML = html;
}

function renderTabs() {
  $("tabs").innerHTML = "";
  S.tabs.forEach((item, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tab" + (index === S.active ? " on" : "");
    const name = item.path.split(/[\\/]/).pop();
    button.textContent = (item.dirty ? "● " : "") + name;
    button.onclick = () => activate(index);
    $("tabs").appendChild(button);
  });
}

function syncScroll() {
  highlightEl().scrollTop = codeEl().scrollTop;
  highlightEl().scrollLeft = codeEl().scrollLeft;
  $("gutter").scrollTop = codeEl().scrollTop;
}

function cursorPos() {
  const area = codeEl();
  const text = area.value.slice(0, area.selectionStart);
  const lines = text.split("\n");
  return { line: lines.length, col: lines[lines.length - 1].length };
}

function updateStatus(extra) {
  const pos = cursorPos();
  $("st-pos").textContent = `Zeile ${pos.line}, Spalte ${pos.col + 1}`;
  if (extra) $("st-mode").textContent = extra + (tab() && tab().writable === false ? " · nur lesen" : "");
  $("st-py").textContent = S.python || "";
}

function activate(index) {
  S.active = index;
  const current = tab();
  codeEl().value = current ? current.content : "";
  renderEditor();
  if (current) scheduleAnalyze();
  updateStatus(current ? current.path : "Bereit");
}

async function openPath(path, line) {
  const existing = S.tabs.findIndex((item) => item.path === path);
  if (existing >= 0) {
    activate(existing);
  } else {
    const data = await apiGet("/api/file?path=" + encodeURIComponent(path));
    if (data.binary) {
      toast("Binärdatei");
      return;
    }
    S.tabs.push({
      path: data.path,
      content: data.content,
      saved: data.content,
      dirty: false,
      writable: data.writable !== false,
      problems: [],
      outline: [],
    });
    activate(S.tabs.length - 1);
  }
  if (line) revealLine(line);
}

function revealLine(line) {
  const area = codeEl();
  const lines = area.value.split("\n");
  let offset = 0;
  for (let index = 0; index < line - 1 && index < lines.length; index += 1) offset += lines[index].length + 1;
  area.focus();
  area.selectionStart = area.selectionEnd = offset;
  const lineHeight = 18;
  area.scrollTop = Math.max(0, (line - 3) * lineHeight);
  syncScroll();
}

async function saveTab() {
  const current = tab();
  if (!current) return;
  if (current.writable === false) {
    toast("Außerhalb des Workspace nur lesbar");
    return;
  }
  unfoldAll();
  await api("/api/file", { path: current.path, content: current.content });
  current.saved = current.content;
  current.dirty = false;
  renderTabs();
  toast("Gespeichert");
}

function unfoldAll() {
  const current = tab();
  if (!current || !current.folds) return;
  current.folds.slice().reverse().forEach((fold) => {
    const lines = current.content.split("\n");
    const index = lines.findIndex((line) => line.includes(fold.marker));
    if (index >= 0) {
      lines.splice(index, 1, ...fold.text.split("\n"));
      current.content = lines.join("\n");
    }
  });
  current.folds = [];
  codeEl().value = current.content;
}

function foldAt(line) {
  const current = tab();
  if (!current) return;
  const block = (current.outline || []).find((item) => item.line === line && item.end_line > item.line);
  if (!block) {
    toast("Kein faltbarer Block in dieser Zeile");
    return;
  }
  current.folds = current.folds || [];
  const lines = current.content.split("\n");
  const hidden = lines.slice(block.line, block.end_line).join("\n");
  const marker = `    # … ${block.name} (${block.end_line - block.line} Zeilen)`;
  lines.splice(block.line, block.end_line - block.line, marker);
  current.folds.push({ marker, text: hidden });
  current.content = lines.join("\n");
  current.dirty = true;
  renderEditor();
}

async function refreshTree(path, container) {
  const data = await apiGet("/api/tree" + (path ? "?path=" + encodeURIComponent(path) : ""));
  const host = container || $("tree");
  host.innerHTML = "";
  data.entries.forEach((entry) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tree-item" + (entry.dir ? " dir" : "");
    button.textContent = (entry.dir ? "▸ " : "") + entry.name;
    const wrap = document.createElement("div");
    wrap.appendChild(button);
    if (entry.dir) {
      const children = document.createElement("div");
      children.className = "tree-children hidden";
      button.onclick = async () => {
        if (children.dataset.loaded !== "1") {
          await refreshTree(entry.path, children);
          children.dataset.loaded = "1";
        }
        children.classList.toggle("hidden");
      };
      wrap.appendChild(children);
    } else {
      button.onclick = () => openPath(entry.path).catch((err) => toast(err.message));
    }
    host.appendChild(wrap);
  });
}

let analyzeTimer = 0;
function scheduleAnalyze() {
  clearTimeout(analyzeTimer);
  analyzeTimer = setTimeout(() => runAnalyze().catch(() => {}), 450);
}

async function runAnalyze() {
  const current = tab();
  if (!current) return;
  const data = await api("/api/analyze", { path: current.path, content: current.content });
  current.problems = data.problems;
  current.outline = data.outline;
  renderOutline();
  renderEditor();
  if (S.bottom === "problems") renderPanel();
}

function renderOutline() {
  const current = tab();
  const host = $("outline");
  host.innerHTML = "";
  if (!current) return;
  (current.outline || []).forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "outline-item";
    button.textContent = (item.parent ? item.parent + "." : "") + item.name;
    button.onclick = () => revealLine(item.line);
    button.ondblclick = () => foldAt(item.line);
    host.appendChild(button);
  });
}

function setBottom(name) {
  S.bottom = name;
  document.querySelectorAll("#bottom-tabs button").forEach((button) => {
    button.classList.toggle("on", button.dataset.panel === name);
  });
  renderPanel();
}

function renderPanel() {
  const host = $("panel");
  host.innerHTML = "";
  const builders = {
    output: renderOutput,
    problems: renderProblems,
    debug: renderDebug,
    tests: renderTests,
    terminal: renderTerminal,
    repl: renderRepl,
    git: renderGit,
    packages: renderPackages,
    search: renderSearch,
    todo: renderTodos,
    history: renderHistory,
    notebook: renderNotebook,
    http: renderHttp,
    db: renderDb,
    vars: renderVars,
    remote: renderRemote,
  };
  (builders[S.bottom] || renderOutput)(host);
}

function renderOutput() {
  const pre = document.createElement("div");
  pre.id = "output-text";
  pre.textContent = S.output || "";
  $("panel").appendChild(pre);
  if ((S.output || "").includes("Traceback")) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Mit KI reparieren";
    button.onclick = fixWithAi;
    $("panel").appendChild(button);
  }
}

function renderProblems(host) {
  const current = tab();
  const items = current ? current.problems || [] : [];
  if (!items.length) {
    host.textContent = "Keine Probleme in der aktuellen Datei.";
    return;
  }
  items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "problem sev-" + item.severity;
    button.textContent = `${item.line}:${item.col}  ${item.code}  ${item.message}`;
    button.onclick = () => revealLine(item.line);
    host.appendChild(button);
  });
}

function field(label, id, value) {
  const wrap = document.createElement("label");
  wrap.textContent = label;
  const input = document.createElement("input");
  input.id = id;
  input.value = value || "";
  wrap.appendChild(input);
  return wrap;
}

function renderDebug(host) {
  host.textContent = S.debugText || "Kein Debugger. Haltepunkt im Rand setzen und F5 drücken.";
  const watch = document.createElement("input");
  watch.placeholder = "Ausdruck beobachten";
  watch.id = "watch-input";
  const add = document.createElement("button");
  add.type = "button";
  add.textContent = "Watch";
  add.onclick = async () => {
    const expr = watch.value.trim();
    if (!expr) return;
    S.watches.push(expr);
    const data = await api("/api/debug", { cmd: "eval", expr });
    const event = (data.events || []).reverse().find((item) => item.event === "eval" && item.expr === expr);
    host.append("\n" + expr + " = " + (event ? event.value || event.error : "?"));
  };
  host.appendChild(document.createElement("br"));
  host.appendChild(watch);
  host.appendChild(add);
}

function renderTests(host) {
  const row = document.createElement("div");
  ["auto", "pytest", "unittest", "doctest"].forEach((name) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = name;
    button.onclick = () => runTests(name, false);
    row.appendChild(button);
  });
  const cov = document.createElement("button");
  cov.type = "button";
  cov.textContent = "Mit Coverage";
  cov.onclick = () => runTests("pytest", true);
  row.appendChild(cov);
  host.appendChild(row);
  const pre = document.createElement("div");
  pre.textContent = S.testOutput || "";
  host.appendChild(pre);
}

function renderTerminal(host) {
  const pre = document.createElement("div");
  pre.id = "term-text";
  pre.textContent = S.terminalText || "";
  const input = document.createElement("input");
  input.placeholder = "Befehl, Enter sendet";
  input.onkeydown = async (event) => {
    if (event.key !== "Enter") return;
    if (!S.terminalId) await startTerminal();
    await api("/api/terminal", { action: "write", id: S.terminalId, data: input.value + "\n" });
    input.value = "";
  };
  host.appendChild(pre);
  host.appendChild(input);
  if (!S.terminalId) startTerminal();
}

async function startTerminal() {
  const data = await api("/api/terminal", { action: "start" });
  S.terminalId = data.id;
  S.terminalFrom = 0;
  pollTerminal();
}

async function pollTerminal() {
  if (!S.terminalId) return;
  try {
    const data = await api("/api/terminal", { action: "read", id: S.terminalId, from: S.terminalFrom });
    S.terminalFrom = data.next;
    S.terminalText = (S.terminalText || "") + (data.text || "");
    const node = $("term-text");
    if (node) node.textContent = S.terminalText;
  } catch (_err) { /* Terminal kann geschlossen sein */ }
  if (S.bottom === "terminal") setTimeout(pollTerminal, 500);
}

function renderRepl(host) {
  const log = document.createElement("div");
  log.id = "repl-log";
  log.textContent = S.replLog || "";
  const input = document.createElement("textarea");
  input.placeholder = "Python, Strg+Enter führt aus";
  input.style.width = "100%";
  input.style.height = "70px";
  input.onkeydown = async (event) => {
    if (event.key === "Enter" && event.ctrlKey) {
      event.preventDefault();
      const data = await api("/api/repl", { code: input.value });
      S.replLog = (S.replLog || "") + ">>> " + input.value + "\n" + (data.stdout || "") + (data.result ? data.result + "\n" : "") + (data.error || "");
      S.variables = data.variables || [];
      S.plots = data.images || [];
      log.textContent = S.replLog;
      input.value = "";
      if (S.bottom === "vars") renderPanel();
    }
  };
  const restart = document.createElement("button");
  restart.type = "button";
  restart.textContent = "Kernel neu";
  restart.onclick = async () => { await api("/api/repl", { restart: true, code: "" }); toast("Kernel neu"); };
  host.appendChild(log);
  host.appendChild(input);
  host.appendChild(restart);
  (S.plots || []).forEach((name) => {
    const img = document.createElement("img");
    img.className = "plot";
    img.src = "/api/plot?name=" + encodeURIComponent(name);
    host.appendChild(img);
  });
}

function renderVars(host) {
  const vars = S.variables || [];
  if (!vars.length) {
    host.textContent = "Keine Variablen. REPL oder Notebook ausführen. Im Debugger stehen Werte im Debug-Panel.";
    return;
  }
  const table = document.createElement("table");
  vars.forEach((item) => {
    const row = document.createElement("tr");
    const name = document.createElement("td");
    name.textContent = item.name + " : " + item.kind;
    const value = document.createElement("td");
    value.textContent = item.repr || JSON.stringify(item.rows || item.shape || "");
    row.appendChild(name);
    row.appendChild(value);
    table.appendChild(row);
  });
  host.appendChild(table);
}

async function renderGit(host) {
  host.textContent = "Lade Git …";
  try {
    const data = await api("/api/git", { action: "status" });
    host.innerHTML = "";
    const info = document.createElement("div");
    info.textContent = data.repo === false ? "Kein Git-Repository im Workspace." : (data.branch || "") + "\n" + (data.stdout || "");
    host.appendChild(info);
    const msg = document.createElement("input");
    msg.placeholder = "Commit-Nachricht";
    const commit = document.createElement("button");
    commit.type = "button";
    commit.textContent = "Alles stagen und committen";
    commit.onclick = async () => {
      await api("/api/git", { action: "add", paths: ["."] });
      const result = await api("/api/git", { action: "commit", message: msg.value });
      toast(result.ok ? "Commit erstellt" : result.error);
      renderGit(host);
    };
    const push = document.createElement("button");
    push.type = "button";
    push.textContent = "Push";
    push.onclick = async () => toast(JSON.stringify(await api("/api/git", { action: "push" })).slice(0, 240));
    const pull = document.createElement("button");
    pull.type = "button";
    pull.textContent = "Pull";
    pull.onclick = async () => toast(JSON.stringify(await api("/api/git", { action: "pull" })).slice(0, 240));
    const log = document.createElement("button");
    log.type = "button";
    log.textContent = "Log";
    log.onclick = async () => {
      const result = await api("/api/git", { action: "log" });
      info.textContent += "\n" + (result.stdout || result.error || "");
    };
    host.appendChild(msg);
    host.appendChild(commit);
    host.appendChild(push);
    host.appendChild(pull);
    host.appendChild(log);
  } catch (err) {
    host.textContent = err.message;
  }
}

async function renderPackages(host) {
  host.innerHTML = "";
  const search = document.createElement("input");
  search.placeholder = "PyPI-Paket";
  const find = document.createElement("button");
  find.type = "button";
  find.textContent = "Suchen";
  const install = document.createElement("button");
  install.type = "button";
  install.textContent = "Installieren";
  const info = document.createElement("div");
  find.onclick = async () => {
    info.textContent = JSON.stringify(await api("/api/pip", { action: "search", query: search.value }), null, 2);
  };
  install.onclick = async () => {
    info.textContent = "Installiere …";
    const result = await api("/api/pip", { action: "install", package: search.value });
    info.textContent = (result.stdout || "") + (result.error || "");
  };
  const groups = document.createElement("div");
  ["qualitaet", "tests", "editor", "build", "data", "web", "db", "notebook"].forEach((group) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = group;
    button.onclick = async () => {
      info.textContent = "Installiere " + group + " …";
      const result = await api("/api/pip", { action: "group", group });
      info.textContent = (result.stdout || "") + (result.error || "");
    };
    groups.appendChild(button);
  });
  const py = document.createElement("button");
  py.type = "button";
  py.textContent = "Python herunterladen";
  py.onclick = downloadPython;
  const venv = document.createElement("button");
  venv.type = "button";
  venv.textContent = "venv anlegen";
  venv.onclick = async () => {
    const name = prompt("Ordner relativ zum Workspace", ".venv");
    if (!name) return;
    const result = await api("/api/venv", { path: name });
    toast(result.python || result.error || "venv erzeugt");
    loadPythons();
  };
  host.appendChild(search);
  host.appendChild(find);
  host.appendChild(install);
  host.appendChild(py);
  host.appendChild(venv);
  host.appendChild(groups);
  host.appendChild(info);
  try {
    const listed = await api("/api/pip", { action: "list" });
    info.textContent = (listed.packages || []).map((item) => item.name + " " + item.version).join("\n");
  } catch (err) {
    info.textContent = err.message;
  }
}

function renderSearch(host) {
  const input = document.createElement("input");
  input.placeholder = "Suche in Dateien, Symbolen, Einstellungen";
  input.onkeydown = async (event) => {
    if (event.key !== "Enter") return;
    const data = await api("/api/search", { query: input.value });
    const list = document.createElement("div");
    data.hits.forEach((hit) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "hit";
      button.textContent = `${hit.kind} ${hit.path}:${hit.line} ${hit.text}`;
      button.onclick = () => { if (hit.kind !== "setting") openPath(hit.path, hit.line); };
      list.appendChild(button);
    });
    host.appendChild(list);
  };
  host.appendChild(input);
}

async function renderTodos(host) {
  host.textContent = "Sammle TODO …";
  const data = await api("/api/todos", {});
  host.innerHTML = "";
  data.items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "hit";
    button.textContent = `${item.tag} ${item.path}:${item.line} ${item.text}`;
    button.onclick = () => openPath(item.path, item.line);
    host.appendChild(button);
  });
  if (!data.items.length) host.textContent = "Keine TODO/FIXME-Kommentare.";
}

async function renderHistory(host) {
  const current = tab();
  if (!current) {
    host.textContent = "Keine Datei offen.";
    return;
  }
  const relative = current.path.startsWith(S.workspace) ? current.path.slice(S.workspace.length).replace(/^[/\\]/, "") : current.path;
  const data = await apiGet("/api/history?path=" + encodeURIComponent(relative));
  if (!data.items.length) {
    host.textContent = "Noch keine lokale Historie. Sie entsteht beim Speichern.";
    return;
  }
  data.items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "hit";
    button.textContent = item.time + "  " + item.bytes + " Bytes";
    button.onclick = async () => {
      const restored = await api("/api/history", { path: relative, id: item.id, restore: true });
      current.content = restored.content;
      current.dirty = true;
      renderEditor();
      toast("Snapshot geladen, noch nicht gespeichert");
    };
    host.appendChild(button);
  });
}

function renderNotebook(host) {
  host.innerHTML = "";
  const path = document.createElement("input");
  path.placeholder = "notebook.ipynb";
  path.value = (tab() && tab().path.endsWith(".ipynb")) ? tab().path : "notebook.ipynb";
  const load = document.createElement("button");
  load.type = "button";
  load.textContent = "Öffnen";
  const box = document.createElement("div");
  load.onclick = async () => {
    const data = await apiGet("/api/notebook?path=" + encodeURIComponent(path.value));
    box.innerHTML = "";
    data.cells.forEach((cell) => {
      const area = document.createElement("textarea");
      area.value = cell.source;
      area.style.width = "100%";
      area.style.height = "80px";
      const run = document.createElement("button");
      run.type = "button";
      run.textContent = "Zelle " + cell.index;
      const out = document.createElement("div");
      run.onclick = async () => {
        const result = await api("/api/notebook", { action: "run", path: path.value, index: cell.index, source: area.value });
        out.textContent = (result.stdout || "") + (result.result || "") + (result.error || "");
        S.variables = result.variables || S.variables;
        (result.images || []).forEach((name) => {
          const img = document.createElement("img");
          img.className = "plot";
          img.src = "/api/plot?name=" + encodeURIComponent(name);
          out.appendChild(img);
        });
      };
      box.appendChild(area);
      box.appendChild(run);
      box.appendChild(out);
    });
  };
  host.appendChild(path);
  host.appendChild(load);
  host.appendChild(box);
}

function renderHttp(host) {
  const area = document.createElement("textarea");
  area.style.width = "100%";
  area.style.height = "90px";
  area.value = "GET https://pypi.org/pypi/pip/json\n";
  const send = document.createElement("button");
  send.type = "button";
  send.textContent = "Anfrage senden";
  const out = document.createElement("div");
  send.onclick = async () => {
    const result = await api("/api/http", { text: area.value });
    out.textContent = (result.status || "") + " " + (result.reason || result.error || "") + "\n" + (result.body || "").slice(0, 4000);
  };
  host.appendChild(area);
  host.appendChild(send);
  host.appendChild(out);
}

function renderDb(host) {
  const path = document.createElement("input");
  path.placeholder = "datei.sqlite oder absolut";
  path.value = "beispiele/demo.sqlite";
  const sql = document.createElement("textarea");
  sql.style.width = "100%";
  sql.value = "CREATE TABLE IF NOT EXISTS person (id INTEGER PRIMARY KEY, name TEXT);\nSELECT name FROM sqlite_master;";
  const run = document.createElement("button");
  run.type = "button";
  run.textContent = "SQL ausführen";
  const out = document.createElement("div");
  run.onclick = async () => {
    const result = await api("/api/db", { engine: "sqlite", path: path.value, sql: sql.value });
    out.textContent = JSON.stringify(result.rows || result, null, 2).slice(0, 5000);
  };
  host.appendChild(path);
  host.appendChild(sql);
  host.appendChild(run);
  host.appendChild(out);
}

function renderRemote(host) {
  const target = document.createElement("input");
  target.placeholder = "user@host";
  const command = document.createElement("input");
  command.placeholder = "remote Befehl, docker oder wsl";
  const ssh = document.createElement("button");
  ssh.type = "button";
  ssh.textContent = "SSH";
  const ps = document.createElement("button");
  ps.type = "button";
  ps.textContent = "docker ps";
  const wsl = document.createElement("button");
  wsl.type = "button";
  wsl.textContent = "WSL";
  const out = document.createElement("div");
  const show = (result) => { out.textContent = (result.stdout || "") + (result.stderr || "") + (result.error || ""); };
  ssh.onclick = async () => show(await api("/api/remote", { action: "ssh", target: target.value, command: command.value }));
  ps.onclick = async () => show(await api("/api/remote", { action: "docker-ps" }));
  wsl.onclick = async () => show(await api("/api/remote", { action: "wsl", command: command.value || "python3 --version" }));
  host.appendChild(target);
  host.appendChild(command);
  host.appendChild(ssh);
  host.appendChild(ps);
  host.appendChild(wsl);
  host.appendChild(out);
}

function appendOutput(text) {
  S.output = (S.output || "") + text;
  const node = $("output-text");
  if (node) node.textContent = S.output;
}

async function runFile(debug) {
  const current = tab();
  if (!current) return toast("Keine Datei");
  unfoldAll();
  await saveTab();
  S.output = "";
  setBottom("output");
  if (!debug) {
    const data = await api("/api/run", { mode: "file", path: current.path });
    S.runId = data.id;
    S.runFrom = 0;
    pollRun();
    updateStatus("Läuft");
    return;
  }
  const points = Object.entries(S.breaks[current.path] || {}).map(([line, condition]) => ({
    file: current.path, line: Number(line), condition: condition || null,
  }));
  await api("/api/debug/start", { path: current.path, breakpoints: points });
  S.debugFrom = 0;
  setBottom("debug");
  pollDebug();
  updateStatus("Debugger");
}

async function pollRun() {
  if (!S.runId) return;
  const data = await apiGet(`/api/session?id=${S.runId}&from=${S.runFrom}`);
  S.runFrom = data.next;
  appendOutput((data.lines || []).join(""));
  if (data.running) {
    setTimeout(pollRun, 300);
  } else {
    appendOutput(`\n[beendet ${data.code}]\n`);
    updateStatus("Bereit");
    if (S.bottom === "output") renderPanel();
  }
}

async function pollDebug() {
  const data = await apiGet("/api/debug?from=0");
  const out = (data.output || []).join("");
  S.debugText = out;
  if (data.paused) {
    S.debugLine = data.paused.line;
    S.debugFile = data.paused.file;
    const locals = Object.entries(data.paused.locals || {}).map(([key, value]) => key + " = " + value).join("\n");
    S.debugText += `\nPause ${data.paused.reason} ${data.paused.file}:${data.paused.line}\n${locals}\n`;
    if (data.paused.file && data.paused.file.endsWith(".py")) {
      openPath(data.paused.file, data.paused.line).catch(() => {});
    }
    updateStatus("Pause Zeile " + data.paused.line);
    if (S.bottom === "debug") renderPanel();
    renderGutter();
    return;
  }
  if (data.running) setTimeout(pollDebug, 400);
  else {
    updateStatus("Debugger beendet");
    S.debugLine = 0;
    if (S.bottom === "debug") renderPanel();
  }
}

async function debugCmd(cmd) {
  const current = tab();
  const points = current ? Object.entries(S.breaks[current.path] || {}).map(([line, condition]) => ({
    file: current.path, line: Number(line), condition: condition || null,
  })) : [];
  await api("/api/debug", { cmd, breakpoints: points });
  setTimeout(pollDebug, 200);
}

async function runTests(framework, coverage) {
  const current = tab();
  const data = await api("/api/tests", { framework, path: current ? current.path : "", coverage });
  S.runId = data.id;
  S.runFrom = 0;
  S.testOutput = "";
  setBottom("tests");
  const tick = async () => {
    const state = await apiGet(`/api/session?id=${S.runId}&from=${S.runFrom}`);
    S.runFrom = state.next;
    S.testOutput += (state.lines || []).join("");
    if (S.bottom === "tests") renderPanel();
    if (state.running) setTimeout(tick, 400);
    else if (coverage) {
      const report = await api("/api/coverage", {});
      S.coverage = report.files || {};
      renderGutter();
      toast("Coverage " + (report.percent ?? "") + "%");
    }
  };
  tick();
}

async function formatCurrent() {
  const current = tab();
  if (!current) return;
  const data = await api("/api/format", { content: current.content });
  current.content = data.content;
  current.dirty = true;
  renderEditor();
  toast("Formatiert mit " + data.tool);
}

async function downloadPython() {
  const data = await api("/api/tools/python", {});
  toast("Download gestartet");
  const tick = async () => {
    const job = await apiGet("/api/jobs?id=" + data.job);
    $("st-mode").textContent = (job.log || []).slice(-1)[0] || "Download";
    if (!job.done) setTimeout(tick, 800);
    else {
      toast(job.result && job.result.python ? job.result.python : (job.result && job.result.error) || "fertig");
      loadPythons();
    }
  };
  tick();
}

function hidePopup() {
  $("popup").classList.add("hidden");
  S.complete = [];
}

async function completeAt() {
  const current = tab();
  if (!current) return;
  const pos = cursorPos();
  const data = await api("/api/complete", { content: current.content, line: pos.line, col: pos.col, path: current.path });
  S.complete = data.items || [];
  S.completeIndex = 0;
  if (!S.complete.length) return hidePopup();
  const popup = $("popup");
  popup.innerHTML = "";
  popup.classList.remove("hidden");
  const rect = caretRect();
  popup.style.left = rect.left + "px";
  popup.style.top = rect.top + "px";
  S.complete.forEach((item, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = index === 0 ? "on" : "";
    button.textContent = item.label + (item.detail ? "  " + item.detail : "");
    button.onclick = () => acceptComplete(index);
    popup.appendChild(button);
  });
}

function caretRect() {
  const area = codeEl();
  const style = getComputedStyle(area);
  const div = document.createElement("div");
  div.style.position = "absolute";
  div.style.visibility = "hidden";
  div.style.whiteSpace = "pre";
  div.style.font = style.font;
  div.style.padding = style.padding;
  div.style.width = area.clientWidth + "px";
  div.textContent = area.value.slice(0, area.selectionStart);
  const span = document.createElement("span");
  span.textContent = ".";
  div.appendChild(span);
  document.body.appendChild(div);
  const spanRect = span.getBoundingClientRect();
  const divRect = div.getBoundingClientRect();
  const host = area.getBoundingClientRect();
  document.body.removeChild(div);
  return {
    left: host.left + (spanRect.left - divRect.left) - area.scrollLeft,
    top: host.top + (spanRect.top - divRect.top) - area.scrollTop + 18,
  };
}

function acceptComplete(index) {
  const item = S.complete[index];
  if (!item) return;
  const area = codeEl();
  const pos = area.selectionStart;
  const upto = area.value.slice(0, pos);
  const prefix = (upto.match(/[A-Za-z0-9_]*$/) || [""])[0];
  const insert = item.kind === "snippet" ? item.insert : item.insert;
  const start = pos - prefix.length;
  const next = area.value.slice(0, start) + insert + area.value.slice(pos);
  const current = tab();
  current.content = next;
  current.dirty = true;
  area.value = next;
  area.selectionStart = area.selectionEnd = start + insert.length;
  hidePopup();
  renderEditor();
}

function selectedText() {
  const area = codeEl();
  return area.value.slice(area.selectionStart, area.selectionEnd);
}

function replaceSelection(text) {
  const area = codeEl();
  const current = tab();
  const start = area.selectionStart;
  current.content = area.value.slice(0, start) + text + area.value.slice(area.selectionEnd);
  current.dirty = true;
  renderEditor();
  area.selectionStart = start;
  area.selectionEnd = start + text.length;
}

function modal(title, body, buttons) {
  const root = $("modal");
  root.classList.remove("hidden");
  root.innerHTML = "";
  const box = document.createElement("div");
  box.className = "box";
  const heading = document.createElement("h2");
  heading.textContent = title;
  box.appendChild(heading);
  box.appendChild(body);
  const row = document.createElement("div");
  row.className = "row";
  buttons.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = item.label;
    button.onclick = () => {
      const close = item.run();
      if (close !== false) root.classList.add("hidden");
    };
    row.appendChild(button);
  });
  box.appendChild(row);
  root.appendChild(box);
}

function promptModal(title, label, value, ok) {
  const body = document.createElement("div");
  const input = document.createElement("input");
  input.value = value || "";
  body.appendChild(document.createTextNode(label));
  body.appendChild(input);
  modal(title, body, [
    { label: "Abbrechen", run: () => {} },
    { label: "OK", run: () => ok(input.value) },
  ]);
  setTimeout(() => input.focus(), 0);
}

function lineDiff(before, after) {
  const a = before.split("\n");
  const b = after.split("\n");
  const host = document.createElement("div");
  const max = Math.max(a.length, b.length);
  for (let i = 0; i < max; i += 1) {
    if (a[i] === b[i]) continue;
    if (a[i] !== undefined) {
      const del = document.createElement("div");
      del.className = "diff-del";
      del.textContent = "- " + a[i];
      host.appendChild(del);
    }
    if (b[i] !== undefined) {
      const add = document.createElement("div");
      add.className = "diff-add";
      add.textContent = "+ " + b[i];
      host.appendChild(add);
    }
  }
  return host;
}

async function inlineEdit() {
  const selection = selectedText() || (tab() && tab().content) || "";
  const body = document.createElement("div");
  const input = document.createElement("input");
  input.placeholder = "Zum Beispiel: in eine async-Funktion umschreiben";
  body.appendChild(input);
  modal("Inline-Änderung", body, [
    { label: "Abbrechen", run: () => {} },
    { label: "An Modell senden", run: async () => {
      const result = await api("/api/ai/inline", { instruction: input.value, selection, content: tab() ? tab().content : "", path: tab() ? tab().path : "" });
      const diff = lineDiff(selection, result.content);
      const box = document.createElement("div");
      box.appendChild(diff);
      modal("Diff annehmen?", box, [
        { label: "Verwerfen", run: () => {} },
        { label: "Annehmen", run: () => replaceSelection(result.content) },
      ]);
      return false;
    } },
  ]);
}

async function fixWithAi() {
  const current = tab();
  if (!current) return;
  const result = await api("/api/ai/fix", { traceback: S.output || "", content: current.content, path: current.path });
  const diff = lineDiff(current.content, result.content);
  modal("KI-Reparatur", diff, [
    { label: "Verwerfen", run: () => {} },
    { label: "Datei ersetzen", run: () => { current.content = result.content; current.dirty = true; renderEditor(); } },
  ]);
}

async function sendAi(agent) {
  const text = $("ai-input").value.trim();
  if (!text) return;
  if (!S.baseUrl) {
    aiSettings(text);
    return;
  }
  const current = tab();
  if (agent) {
    const started = await api("/api/ai/agent", { prompt: text });
    const tick = async () => {
      const job = await apiGet("/api/jobs?id=" + started.job);
      $("ai-log").textContent = (job.log || []).join("\n") + (job.result ? "\n" + JSON.stringify(job.result.steps || job.result, null, 2).slice(0, 8000) : "");
      if (!job.done) setTimeout(tick, 700);
      else { refreshTree(); toast("Agent fertig"); }
    };
    tick();
    return;
  }
  S.ai.push({ role: "user", content: text });
  $("ai-input").value = "";
  $("ai-log").textContent = S.ai.map((item) => item.role + ": " + item.content).join("\n\n");
  const result = await api("/api/ai/chat", {
    messages: S.ai,
    text,
    path: current ? current.path : "",
    content: current ? current.content : "",
  });
  S.ai.push({ role: "assistant", content: result.content || result.error || "" });
  $("ai-log").textContent = S.ai.map((item) => item.role + ": " + item.content).join("\n\n");
}

function toggleBreak(line) {
  const current = tab();
  if (!current) return;
  S.breaks[current.path] = S.breaks[current.path] || {};
  if (S.breaks[current.path][line] !== undefined) delete S.breaks[current.path][line];
  else S.breaks[current.path][line] = "";
  renderGutter();
}

async function gotoDef() {
  const current = tab();
  if (!current) return;
  const pos = cursorPos();
  const data = await api("/api/goto", { content: current.content, line: pos.line, col: pos.col, path: current.path });
  if (!data.hits.length) return toast("Keine Definition");
  openPath(data.hits[0].path, data.hits[0].line);
}

async function renameSymbol() {
  const current = tab();
  if (!current) return;
  const pos = cursorPos();
  const upto = current.content.split("\n")[pos.line - 1] || "";
  const name = (upto.slice(0, pos.col).match(/[A-Za-z_][A-Za-z0-9_]*$/) || [""])[0];
  promptModal("Umbenennen", "Neuer Name für " + name, name, async (value) => {
    const preview = await api("/api/rename", { old: name, new: value, project: true, preview: true });
    if (!confirm(`${preview.count} Stellen in ${(preview.changed || []).length} Dateien ändern?`)) return;
    await api("/api/rename", { old: name, new: value, project: true });
    toast("Umbenannt");
    if (current.path) {
      const fresh = await apiGet("/api/file?path=" + encodeURIComponent(current.path));
      current.content = fresh.content;
      current.dirty = false;
      renderEditor();
    }
  });
}

async function extractMethod() {
  const current = tab();
  if (!current) return;
  const area = codeEl();
  const start = area.value.slice(0, area.selectionStart).split("\n").length;
  const end = area.value.slice(0, Math.max(area.selectionEnd - 1, area.selectionStart)).split("\n").length;
  promptModal("Methode extrahieren", "Name", "extracted", async (name) => {
    const result = await api("/api/extract", { content: current.content, start, end, name });
    current.content = result.content;
    current.dirty = true;
    renderEditor();
  });
}

function insertSnippet(code) {
  const current = tab();
  if (!current) return;
  const area = codeEl();
  const pos = area.selectionStart;
  current.content = area.value.slice(0, pos) + code + area.value.slice(pos);
  current.dirty = true;
  renderEditor();
}

async function loadPythons() {
  const data = await apiGet("/api/pythons");
  const select = $("py-select");
  select.innerHTML = "";
  data.interpreters.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.path;
    option.textContent = `${item.version || "?"}  ${item.source}`;
    if (item.path === data.current) option.selected = true;
    select.appendChild(option);
  });
  S.python = data.current;
  updateStatus();
}

function buildMenus() {
  const menus = [
    ["Datei", [
      ["Öffnen…", () => openFileDialog()],
      ["Datei laden…", loadPickedFiles],
      ["Neue Datei", newFile],
      ["Ordner öffnen…", openFolder],
      ["Speichern", saveTab, "Strg+S"],
      ["Alles speichern", saveTab],
    ]],
    ["Bearbeiten", [
      ["Ausschneiden", cutSelection, "Strg+X"],
      ["Kopieren", () => copySelection(false), "Strg+C"],
      ["Bereich kopieren…", copyRange],
      ["Einfügen", pasteClip, "Strg+V"],
      ["Formatieren", formatCurrent, "Umschalt+Alt+F"],
      ["Snippet einfügen", pickSnippet],
      ["Falten", () => foldAt(cursorPos().line)],
      ["Alles aufklappen", () => { unfoldAll(); renderEditor(); }],
    ]],
    ["Navigieren", [
      ["Gehe zu Definition", gotoDef, "F12"],
      ["Suche überall", () => setBottom("search"), "Strg+Umschalt+F"],
      ["Gliederung", () => showSide("outline")],
      ["TODO", () => setBottom("todo")],
      ["Lesezeichen", addBookmark],
    ]],
    ["Ausführen", [
      ["Datei ausführen", () => runFile(false), "Strg+F5"],
      ["Auswahl ausführen", runSelection],
      ["Syntax prüfen", checkSyntax],
      ["Bytecode kompilieren", () => compileCurrent("file")],
      ["Projekt kompilieren", () => compileCurrent("project")],
      ["PyInstaller", pyInstaller],
      ["Framework starten", runFramework],
    ]],
    ["Debuggen", [
      ["Start / Weiter", () => S.debugLine ? debugCmd("continue") : runFile(true), "F5"],
      ["Schritt über", () => debugCmd("step"), "F10"],
      ["Schritt hinein", () => debugCmd("step_into"), "F11"],
      ["Schritt hinaus", () => debugCmd("step_out")],
      ["Haltepunkt", () => toggleBreak(cursorPos().line), "F9"],
      ["Bedingung…", conditionBreak],
      ["Stopp", stopAll],
    ]],
    ["Refactor", [
      ["Umbenennen", renameSymbol, "Umschalt+F6"],
      ["Methode extrahieren", extractMethod],
      ["Dubletten suchen", findDuplicates],
    ]],
    ["Werkzeuge", [
      ["Paket-Manager", () => setBottom("packages")],
      ["Python herunterladen", downloadPython],
      ["venv", () => setBottom("packages")],
      ["conda", condaCreate],
      ["Poetry install", () => api("/api/poetry", {}).then((r) => toast(r.ok ? "poetry fertig" : r.error))],
      ["Werkzeugstatus", toolStatus],
      ["Tests", () => setBottom("tests")],
    ]],
    ["Git", [
      ["Status", () => setBottom("git")],
      ["Branch…", gitBranch],
      ["Klonen…", gitClone],
      ["Konflikte", gitConflicts],
      ["GitHub und Visual Studio…", () => aiSettings()],
    ]],
    ["KI", [
      ["Sprachmodell verbinden…", () => aiSettings()],
      ["Inline-Edit", inlineEdit, "Strg+K"],
      ["Chat", () => $("ai-input").focus()],
      ["Agent", () => sendAi(true)],
      ["Mit KI reparieren", fixWithAi],
      ["Live-Sitzung", startCollab],
    ]],
    ["Fenster", [
      ["Zweites Fenster", secondWindow],
    ]],
    ["Hilfe", [
      ["Tastatur", showKeys],
      ["Über ShatuIDE", about],
    ]],
  ];
  const bar = $("menubar");
  menus.forEach(([name, items]) => {
    const wrap = document.createElement("div");
    wrap.className = "menu";
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = name;
    button.onclick = (event) => {
      event.stopPropagation();
      document.querySelectorAll(".menu").forEach((menu) => menu.classList.remove("open"));
      wrap.classList.add("open");
    };
    const pop = document.createElement("div");
    pop.className = "menu-pop";
    items.forEach(([label, fn, hint]) => {
      const item = document.createElement("button");
      item.type = "button";
      item.innerHTML = `<span>${label}</span>` + (hint ? `<span>${hint}</span>` : "");
      item.onclick = () => { wrap.classList.remove("open"); Promise.resolve(fn()).catch((err) => toast(err.message)); };
      pop.appendChild(item);
    });
    wrap.appendChild(button);
    wrap.appendChild(pop);
    bar.appendChild(wrap);
  });
  document.addEventListener("click", () => document.querySelectorAll(".menu").forEach((menu) => menu.classList.remove("open")));
}

function copyText(text) {
  S.clip = text;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).catch(() => {});
  }
  toast("Kopiert (" + text.length + " Zeichen)");
}

function copySelection(lineIfEmpty) {
  const current = tab();
  if (!current) return;
  const area = codeEl();
  let text = area.value.slice(area.selectionStart, area.selectionEnd);
  if (!text && lineIfEmpty !== false) {
    const lines = area.value.split("\n");
    text = lines[cursorPos().line - 1] || "";
  }
  if (!text) return toast("Nichts markiert");
  copyText(text);
}

function cutSelection() {
  const current = tab();
  if (!current) return;
  if (current.writable === false) return toast("Nur lesen");
  const area = codeEl();
  let start = area.selectionStart;
  let end = area.selectionEnd;
  if (start === end) {
    const lines = area.value.split("\n");
    const line = cursorPos().line;
    let offset = 0;
    for (let index = 0; index < line - 1; index += 1) offset += lines[index].length + 1;
    start = offset;
    end = offset + lines[line - 1].length;
    if (line < lines.length) end += 1;
  }
  const text = area.value.slice(start, end);
  if (!text) return toast("Nichts markiert");
  copyText(text);
  area.selectionStart = start;
  area.selectionEnd = end;
  replaceSelection("");
}

function readClipboard() {
  if (!navigator.clipboard || !navigator.clipboard.readText) return Promise.resolve("");
  return Promise.race([
    navigator.clipboard.readText().catch(() => ""),
    new Promise((resolve) => setTimeout(() => resolve(""), 400)),
  ]);
}

async function pasteClip() {
  const current = tab();
  if (!current) return;
  if (current.writable === false) return toast("Nur lesen");
  const remote = await readClipboard();
  const text = remote || S.clip || "";
  if (!text) return toast("Zwischenablage leer");
  replaceSelection(text);
}

function copyRange() {
  const current = tab();
  if (!current) return;
  const body = document.createElement("div");
  const from = document.createElement("input");
  from.type = "number";
  from.min = "1";
  from.value = String(cursorPos().line);
  const to = document.createElement("input");
  to.type = "number";
  to.min = "1";
  to.value = from.value;
  aiField(body, "Von Zeile", from);
  aiField(body, "Bis Zeile", to);
  modal("Bereich kopieren", body, [
    { label: "Abbrechen", run: () => {} },
    { label: "Kopieren", run: () => {
      const lines = current.content.split("\n");
      const start = Math.max(1, Number(from.value) || 1);
      const end = Math.min(lines.length, Math.max(start, Number(to.value) || start));
      copyText(lines.slice(start - 1, end).join("\n"));
    } },
  ]);
}

function secondWindow() {
  const opened = window.open(location.href, "shatu-" + Date.now(), "popup=yes,width=1280,height=860,left=80,top=40");
  if (!opened) toast("Zweites Fenster wurde blockiert");
}

function loadPickedFiles() {
  const input = document.createElement("input");
  input.type = "file";
  input.multiple = true;
  input.onchange = async () => {
    for (const file of input.files || []) {
      if (file.size > 2000000) {
        toast(file.name + " ist zu groß");
        continue;
      }
      const text = await file.text();
      if (text.includes("\0")) {
        toast(file.name + " ist binär");
        continue;
      }
      S.tabs.push({ path: file.name, content: text, saved: "", dirty: true, writable: true, problems: [], outline: [] });
      activate(S.tabs.length - 1);
    }
    toast("Geladen, Speichern schreibt in den Workspace");
  };
  input.click();
}

async function openFileDialog(start) {
  const body = document.createElement("div");
  const pathInput = document.createElement("input");
  pathInput.id = "browse-path";
  const list = document.createElement("div");
  list.className = "browse-list";
  list.id = "browse-list";
  const filter = document.createElement("input");
  filter.placeholder = "Name filtern, zum Beispiel .py oder .sh";
  body.appendChild(pathInput);
  body.appendChild(filter);
  body.appendChild(list);
  let current = "";
  let ticket = 0;
  async function load(path) {
    const id = ++ticket;
    const data = await apiGet("/api/browse?path=" + encodeURIComponent(path || ""));
    if (id !== ticket) return;
    current = data.path;
    pathInput.value = data.path;
    list.replaceChildren();
    function row(label, action, className) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = className || "";
      button.textContent = label;
      button.onclick = action;
      list.appendChild(button);
    }
    row("Workspace", () => load(data.workspace).catch((err) => toast(err.message)));
    row("Home", () => load(data.home).catch((err) => toast(err.message)));
    if (data.parent) row("..", () => load(data.parent).catch((err) => toast(err.message)), "dir");
    const needle = filter.value.trim().toLowerCase();
    data.entries.forEach((entry) => {
      if (needle && !entry.name.toLowerCase().includes(needle)) return;
      row((entry.dir ? "▸ " : "") + entry.name, () => {
        if (entry.dir) load(entry.path).catch((err) => toast(err.message));
        else {
          $("modal").classList.add("hidden");
          openPath(entry.path).catch((err) => toast(err.message));
        }
      }, entry.dir ? "dir" : "");
    });
  }
  pathInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") load(pathInput.value).catch((err) => toast(err.message));
  });
  filter.addEventListener("input", () => load(current || pathInput.value).catch(() => {}));
  modal("Datei öffnen", body, [{ label: "Schließen", run: () => {} }]);
  await load(start || S.workspace || "");
}

function newFile() {
  promptModal("Neue Datei", "Pfad im Workspace", "neu.py", async (path) => {
    const written = await api("/api/file", { path, content: "" });
    await refreshTree();
    openPath(written.path);
  });
}

function openFolder() {
  promptModal("Workspace", "Voller Zugriff auf diesen Ordner", S.workspace || "D:\\AI_Temp\\ShatuIDE", async (path) => {
    const data = await api("/api/workspace", { path });
    S.workspace = data.workspace;
    S.tabs = [];
    S.active = -1;
    $("ws-label").textContent = S.workspace;
    codeEl().value = "";
    renderEditor();
    refreshTree();
  });
}

async function pickSnippet() {
  const data = await apiGet("/api/snippets");
  const body = document.createElement("div");
  data.snippets.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = item.label + " (" + item.trigger + ")";
    button.onclick = () => { insertSnippet(item.code); $("modal").classList.add("hidden"); };
    body.appendChild(button);
  });
  modal("Snippets", body, [{ label: "Schließen", run: () => {} }]);
}

function addBookmark() {
  const current = tab();
  if (!current) return;
  api("/api/bookmarks", { action: "add", path: current.path, line: cursorPos().line, note: "Lesezeichen" })
    .then(() => toast("Lesezeichen gespeichert"));
}

async function runSelection() {
  const text = selectedText();
  if (!text) return toast("Nichts markiert");
  const data = await api("/api/run", { mode: "selection", content: text });
  S.runId = data.id;
  S.runFrom = 0;
  S.output = "";
  setBottom("output");
  pollRun();
}

async function checkSyntax() {
  const current = tab();
  if (!current) return;
  const result = await api("/api/compile", { mode: "check", content: current.content, path: current.path });
  toast(result.message || result.error);
}

async function compileCurrent(mode) {
  const current = tab();
  if (mode === "file" && current) await saveTab();
  const result = await api("/api/compile", { mode, path: current ? current.path : "" });
  toast(result.message || result.error || "fertig");
}

async function pyInstaller() {
  const current = tab();
  if (!current) return;
  await saveTab();
  const data = await api("/api/run", { mode: "pyinstaller", path: current.path });
  S.runId = data.id;
  S.runFrom = 0;
  S.output = "";
  setBottom("output");
  pollRun();
}

async function runFramework() {
  const data = await apiGet("/api/frameworks");
  if (!data.items.length) return toast("Kein Django, Flask oder FastAPI erkannt");
  const item = data.items[0];
  const started = await api("/api/run", { mode: "framework", argv: item.argv, cwd: item.cwd });
  S.runId = started.id;
  S.runFrom = 0;
  S.output = item.label + "\n";
  setBottom("output");
  pollRun();
}

function conditionBreak() {
  const line = cursorPos().line;
  promptModal("Bedingter Haltepunkt", "Ausdruck, leer = immer", "", (value) => {
    const current = tab();
    S.breaks[current.path] = S.breaks[current.path] || {};
    S.breaks[current.path][line] = value;
    renderGutter();
  });
}

async function stopAll() {
  if (S.runId) await api("/api/session/stop", { id: S.runId });
  await api("/api/debug", { cmd: "stop" }).catch(() => {});
  updateStatus("Gestoppt");
}

async function findDuplicates() {
  const data = await api("/api/duplicates", {});
  const body = document.createElement("div");
  if (!data.groups.length) body.textContent = "Keine längeren Dubletten.";
  data.groups.forEach((group) => {
    const block = document.createElement("div");
    block.textContent = group.preview + "\n" + group.places.map((place) => place.path + ":" + place.line).join("\n");
    body.appendChild(block);
    body.appendChild(document.createElement("hr"));
  });
  modal("Dubletten", body, [{ label: "Schließen", run: () => {} }]);
}

async function condaCreate() {
  promptModal("conda", "Name der Umgebung", "shatu", async (name) => {
    const result = await api("/api/conda", { name, version: "3.12" });
    toast(result.ok ? "conda-Umgebung angelegt" : result.error);
  });
}

async function toolStatus() {
  const data = await apiGet("/api/tools");
  const body = document.createElement("pre");
  body.textContent = JSON.stringify(data, null, 2);
  modal("Werkzeuge", body, [{ label: "Schließen", run: () => {} }]);
}

function gitBranch() {
  promptModal("Branch", "Name", "feature", async (name) => {
    const result = await api("/api/git", { action: "branch", name });
    toast(result.ok ? "Branch angelegt" : result.error);
  });
}

function gitClone() {
  promptModal("Klonen", "https://…", "", async (url) => {
    const result = await api("/api/git", { action: "clone", url, dest: "repo" });
    toast(result.ok ? "Geklont" : result.error);
    refreshTree();
  });
}

async function gitConflicts() {
  const data = await api("/api/git", { action: "conflicts" });
  const body = document.createElement("div");
  (data.files || []).forEach((path) => {
    const ours = document.createElement("button");
    ours.type = "button";
    ours.textContent = "Ours " + path;
    ours.onclick = () => api("/api/git", { action: "resolve", path, side: "ours" });
    const theirs = document.createElement("button");
    theirs.type = "button";
    theirs.textContent = "Theirs " + path;
    theirs.onclick = () => api("/api/git", { action: "resolve", path, side: "theirs" });
    body.appendChild(ours);
    body.appendChild(theirs);
  });
  if (!(data.files || []).length) body.textContent = "Keine Konflikte.";
  modal("Merge-Konflikte", body, [{ label: "Schließen", run: () => {} }]);
}

function aiField(body, label, node) {
  const caption = document.createElement("label");
  caption.textContent = label;
  body.appendChild(caption);
  body.appendChild(node);
}

async function aiSettings(prefill) {
  const cfg = await apiGet("/api/ai/config");
  const providers = cfg.providers || [];
  const body = document.createElement("div");
  const provider = document.createElement("select");
  providers.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.id;
    option.textContent = item.name;
    provider.appendChild(option);
  });
  if ([...provider.options].some((option) => option.value === cfg.provider)) provider.value = cfg.provider;
  else {
    const match = providers.find((item) => item.base_url && item.base_url === (cfg.base_url || ""));
    if (match) provider.value = match.id;
    else if (cfg.base_url) provider.value = "custom";
  }
  const note = document.createElement("p");
  note.className = "hint";
  const url = document.createElement("input");
  url.id = "ai-base-url";
  url.value = cfg.base_url || "http://127.0.0.1:11434/v1";
  const model = document.createElement("input");
  model.id = "ai-model";
  model.setAttribute("list", "ai-models");
  model.value = cfg.model || "llama3.1";
  const list = document.createElement("datalist");
  list.id = "ai-models";
  const key = document.createElement("input");
  key.type = "password";
  key.placeholder = cfg.has_api_key ? "gesetzt, leer lassen zum Behalten" : "API-Schlüssel, bei Ollama leer";
  const system = document.createElement("textarea");
  system.spellcheck = false;
  system.rows = 3;
  system.value = cfg.system_prompt || "";
  system.placeholder = "Leer lassen für den Standardassistenten";
  const prompt = document.createElement("textarea");
  prompt.spellcheck = false;
  prompt.id = "ai-connect-prompt";
  prompt.rows = 3;
  prompt.placeholder = "Prompt, der beim Verbinden an das Modell geht";
  prompt.value = prefill || "";
  const github = document.createElement("input");
  github.type = "password";
  github.id = "ai-github-token";
  github.placeholder = cfg.has_github_token ? "gesetzt, leer lassen zum Behalten" : "Personal Access Token für github.com";
  const checks = document.createElement("div");
  checks.className = "checks";
  checks.id = "ai-extensions";
  const selected = new Set(Array.isArray(cfg.extensions) ? cfg.extensions : []);
  (cfg.extension_catalog || []).forEach((item) => {
    const label = document.createElement("label");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.value = item.id;
    box.checked = selected.has(item.id);
    box.title = item.note || "";
    label.append(box, document.createTextNode(item.name));
    checks.appendChild(label);
  });
  const vscodePath = document.createElement("input");
  vscodePath.placeholder = (cfg.editors && cfg.editors.vscode && cfg.editors.vscode.path) || "Pfad zu code, leer = automatisch";
  vscodePath.value = (cfg.editors && cfg.editors.vscode && cfg.editors.vscode.configured) || "";
  const visualPath = document.createElement("input");
  visualPath.placeholder = "Pfad zu devenv.exe, leer = automatisch";
  visualPath.value = (cfg.editors && cfg.editors.visualstudio && cfg.editors.visualstudio.configured) || "";
  const windPath = document.createElement("input");
  windPath.placeholder = "Pfad zu windsurf, leer = automatisch";
  windPath.value = (cfg.editors && cfg.editors.windsurf && cfg.editors.windsurf.configured) || "";
  const result = document.createElement("pre");
  result.id = "ai-connect-result";
  function applyProvider(force) {
    const item = providers.find((entry) => entry.id === provider.value);
    note.textContent = item ? item.note : "";
    if (!item || item.id === "custom" || !force) return;
    url.value = item.base_url;
    model.value = item.model;
    key.placeholder = item.key_hint || key.placeholder;
  }
  provider.addEventListener("change", () => applyProvider(true));
  applyProvider(false);
  aiField(body, "Anbieter", provider);
  body.appendChild(note);
  aiField(body, "Basis-URL", url);
  aiField(body, "Modell", model);
  body.appendChild(list);
  aiField(body, "API-Schlüssel", key);
  aiField(body, "System-Prompt", system);
  aiField(body, "Prompt", prompt);
  aiField(body, "GitHub-Token", github);
  const ghHint = document.createElement("p");
  ghHint.className = "hint";
  ghHint.textContent = "Das Token gilt nur für HTTPS gegen github.com (Klonen, Push, Pull). Copilot selbst meldet man in VS Code oder Visual Studio an.";
  body.appendChild(ghHint);
  aiField(body, "VS-Code-Erweiterungen", checks);
  aiField(body, "Visual Studio Code", vscodePath);
  aiField(body, "Visual Studio", visualPath);
  aiField(body, "Windsurf", windPath);
  const actions = document.createElement("div");
  actions.className = "editor-actions";
  function editorButton(label, run) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.onclick = () => run().catch((err) => { result.textContent = err.message; });
    actions.appendChild(button);
  }
  function chosenExtensions() {
    return [...checks.querySelectorAll("input:checked")].map((box) => box.value);
  }
  editorButton("GitHub prüfen", async () => {
    result.textContent = "Prüfe GitHub…";
    const saved = await api("/api/ai/config", payload(false));
    remember(saved);
    const who = await api("/api/editors", { action: "github", github_token: github.value });
    result.textContent = "GitHub: " + (who.login || "") + (who.name ? " (" + who.name + ")" : "");
  });
  editorButton("Editor-Konfiguration schreiben", async () => {
    const saved = await api("/api/ai/config", payload(false));
    remember(saved);
    const written = await api("/api/editors", { action: "write", extensions: chosenExtensions() });
    result.textContent = written.message || "Geschrieben.";
  });
  editorButton("VS Code öffnen", async () => {
    await api("/api/ai/config", payload(false));
    const opened = await api("/api/editors", { action: "open", kind: "vscode" });
    result.textContent = "VS Code: " + opened.path;
  });
  editorButton("Visual Studio öffnen", async () => {
    await api("/api/ai/config", payload(false));
    const opened = await api("/api/editors", { action: "open", kind: "visualstudio" });
    result.textContent = "Visual Studio: " + opened.path;
  });
  editorButton("Erweiterungen installieren", async () => {
    await api("/api/ai/config", payload(false));
    result.textContent = "Installiere…";
    const installed = await api("/api/editors", { action: "install", extensions: chosenExtensions() });
    result.textContent = installed.log || installed.error || "Fertig.";
  });
  body.appendChild(actions);
  body.appendChild(result);

  function payload(send) {
    const data = {
      provider: provider.value,
      base_url: url.value,
      model: model.value,
      api_key: key.value,
      system_prompt: system.value,
      github_token: github.value,
      extensions: chosenExtensions(),
      editor_vscode: vscodePath.value,
      editor_visualstudio: visualPath.value,
      editor_windsurf: windPath.value,
    };
    const current = tab();
    if (current) {
      data.path = current.path;
      data.content = current.content;
    }
    if (send) data.prompt = prompt.value;
    return data;
  }

  function remember(saved) {
    S.baseUrl = saved.base_url || "";
    S.model = saved.model || "";
  }

  modal("Sprachmodell verbinden", body, [
    { label: "Abbrechen", run: () => {} },
    { label: "Modelle laden", run: () => {
      result.textContent = "Lade Modelle…";
      api("/api/ai/models", { base_url: url.value, api_key: key.value }).then((data) => {
        list.replaceChildren();
        (data.models || []).forEach((name) => {
          const option = document.createElement("option");
          option.value = name;
          list.appendChild(option);
        });
        if ((data.models || []).length) {
          if (!model.value.trim()) model.value = data.models[0];
          result.textContent = data.models.length + " Modelle geladen.";
        } else result.textContent = "Keine Modelle gemeldet.";
      }).catch((err) => { result.textContent = err.message; });
      return false;
    } },
    { label: "Speichern", run: () => {
      api("/api/ai/config", payload(false)).then((saved) => {
        remember(saved);
        result.textContent = "Verbindung gespeichert.";
        toast("Gespeichert");
      }).catch((err) => { result.textContent = err.message; });
      return false;
    } },
    { label: "Verbinden und senden", run: () => {
      const text = prompt.value.trim();
      if (!text) {
        result.textContent = "Prompt eingeben.";
        return false;
      }
      result.textContent = "Sende Prompt…";
      api("/api/ai/config", payload(true)).then((saved) => {
        remember(saved);
        const reply = saved.reply || {};
        result.textContent = reply.content || reply.error || "Keine Antwort.";
        if (reply.ok && reply.content) {
          S.ai.push({ role: "user", content: text });
          S.ai.push({ role: "assistant", content: reply.content });
          $("ai-log").textContent = S.ai.map((item) => item.role + ": " + item.content).join("\n\n");
        }
      }).catch((err) => { result.textContent = err.message; });
      return false;
    } },
  ]);
}

async function startCollab() {
  const current = tab();
  const data = await api("/api/collab", { action: "start", path: current ? current.path : "", content: current ? current.content : "" });
  toast("Live-Sitzung Port " + data.port + " Token " + data.token);
  prompt("Adresse für den Partner", location.protocol + "//" + location.hostname + ":" + data.port + "/?token=" + data.token);
}

function showKeys() {
  const body = document.createElement("pre");
  body.textContent = "Strg+S Speichern\nStrg+X Ausschneiden\nStrg+C Kopieren\nStrg+V Einfügen\nStrg+F5 Ausführen\nF5 Debug/Weiter\nF9 Haltepunkt\nF10 Schritt über\nF11 Schritt hinein\nF12 Definition\nStrg+K Inline-KI\nStrg+Eingabe Prompt senden\nStrg+Leertaste Vervollständigen\nStrg+Umschalt+F Suche";
  modal("Tastatur", body, [{ label: "Schließen", run: () => {} }]);
}

function about() {
  const body = document.createElement("div");
  body.innerHTML = "<p><b>ShatuIDE</b> 1.0</p><p>Andreas Meyer<br>ame@sellerbach.de</p><p>Lokale Python-IDE. Workspace mit vollem Dateizugriff, Standard unter Windows: D:\\AI_Temp\\ShatuIDE. Ein vorhandenes Icon oder die Mitte einer Grafik (grafik.png / icon.png) wird automatisch verwendet.</p>";
  modal("Über", body, [{ label: "Schließen", run: () => {} }]);
}

function showSide(name) {
  S.side = name;
  $("tree").classList.toggle("hidden", name !== "tree");
  $("outline").classList.toggle("hidden", name !== "outline");
  document.querySelectorAll("[data-side]").forEach((button) => button.classList.toggle("on", button.dataset.side === name));
}

function onKey(event) {
  const key = event.key.toLowerCase();
  if (event.ctrlKey && key === "s") { event.preventDefault(); saveTab().catch((err) => toast(err.message)); }
  else if (event.ctrlKey && key === "f5") { event.preventDefault(); runFile(false); }
  else if (event.key === "F5") { event.preventDefault(); S.debugLine ? debugCmd("continue") : runFile(true); }
  else if (event.key === "F9") { event.preventDefault(); toggleBreak(cursorPos().line); }
  else if (event.key === "F10") { event.preventDefault(); debugCmd("step"); }
  else if (event.key === "F11") { event.preventDefault(); debugCmd("step_into"); }
  else if (event.key === "F12") { event.preventDefault(); gotoDef(); }
  else if (event.ctrlKey && key === "k") { event.preventDefault(); inlineEdit(); }
  else if (event.ctrlKey && event.code === "Space") { event.preventDefault(); completeAt(); }
  else if (S.complete.length && event.key === "ArrowDown") { event.preventDefault(); moveComplete(1); }
  else if (S.complete.length && event.key === "ArrowUp") { event.preventDefault(); moveComplete(-1); }
  else if (S.complete.length && (event.key === "Enter" || event.key === "Tab")) { event.preventDefault(); acceptComplete(S.completeIndex); }
  else if (event.key === "Escape") hidePopup();
}

function moveComplete(delta) {
  S.completeIndex = (S.completeIndex + delta + S.complete.length) % S.complete.length;
  [...$("popup").children].forEach((node, index) => node.classList.toggle("on", index === S.completeIndex));
}

function bindResize(id, apply) {
  const node = $(id);
  node.addEventListener("mousedown", (event) => {
    event.preventDefault();
    const move = (ev) => apply(ev);
    const up = () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  });
}

async function boot() {
  buildMenus();
  BOTTOM.forEach(([id, label]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.panel = id;
    button.textContent = label;
    button.onclick = () => setBottom(id);
    $("bottom-tabs").appendChild(button);
  });
  document.querySelectorAll("[data-side]").forEach((button) => {
    button.onclick = () => showSide(button.dataset.side);
  });
  $("btn-run").onclick = () => runFile(false);
  $("btn-debug").onclick = () => runFile(true);
  $("btn-stop").onclick = () => stopAll();
  $("btn-format").onclick = () => formatCurrent();
  $("ai-connect").onclick = () => aiSettings($("ai-input").value).catch((err) => toast(err.message));
  $("ai-send").onclick = () => sendAi(false).catch((err) => toast(err.message));
  $("ai-input").addEventListener("keydown", (event) => {
    if (event.ctrlKey && event.key === "Enter") {
      event.preventDefault();
      sendAi(false).catch((err) => toast(err.message));
    }
  });
  $("ai-agent").onclick = () => sendAi(true).catch((err) => toast(err.message));
  $("ai-inline").onclick = () => inlineEdit();
  $("py-select").onchange = async (event) => {
    await api("/api/interpreter", { path: event.target.value });
    S.python = event.target.value;
    updateStatus();
  };
  const area = codeEl();
  area.addEventListener("input", () => {
    const current = tab();
    if (!current) return;
    current.content = area.value;
    current.dirty = current.content !== current.saved;
    highlightEl().innerHTML = highlightPython(current.content, errorLineSet()) + "\n";
    renderGutter();
    renderTabs();
    scheduleAnalyze();
    if (/[A-Za-z0-9_.]$/.test(area.value.slice(0, area.selectionStart))) completeAt().catch(() => {});
    else hidePopup();
  });
  area.addEventListener("scroll", syncScroll);
  area.addEventListener("keyup", () => updateStatus());
  area.addEventListener("click", () => { updateStatus(); hidePopup(); });
  area.addEventListener("keydown", onKey);
  $("gutter").addEventListener("click", (event) => {
    const line = event.target.dataset && event.target.dataset.line;
    if (line) toggleBreak(Number(line));
  });
  document.addEventListener("keydown", (event) => {
    if (event.target === area) return;
    if (event.ctrlKey && event.key.toLowerCase() === "s") { event.preventDefault(); saveTab(); }
  });
  bindResize("left-resizer", (event) => { document.documentElement.style.setProperty("--left", Math.max(160, event.clientX) + "px"); });
  bindResize("right-resizer", (event) => { document.documentElement.style.setProperty("--right", Math.max(200, window.innerWidth - event.clientX) + "px"); });
  bindResize("bottom-resizer", (event) => { document.documentElement.style.setProperty("--bottom", Math.max(90, window.innerHeight - event.clientY) + "px"); });
  const state = await apiGet("/api/state");
  S.workspace = state.workspace;
  S.python = state.python;
  S.baseUrl = state.base_url || "";
  S.model = state.model || "";
  $("ws-label").textContent = state.workspace;
  document.title = "ShatuIDE – " + state.author;
  await refreshTree();
  await loadPythons();
  setBottom("output");
  const welcome = state.workspace.replace(/[/\\]$/, "") + "/beispiele/hallo.py";
  openPath(welcome).catch(() => {});
  updateStatus("Bereit");
}

boot().catch((err) => toast(err.message));
