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
  wrap: false,
  dock: "functions",
  symbol: null,
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
  ["studio", "Studio"],
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

function languageOf(path) {
  const name = String(path || "").split(/[\\/]/).pop().toLowerCase();
  const ext = name.includes(".") ? name.slice(name.lastIndexOf(".")) : "";
  if ([".py", ".pyw", ".pyi"].includes(ext)) return "python";
  if ([".sh", ".bash", ".zsh", ".ksh"].includes(ext) || [".bashrc", ".bash_profile", ".profile", ".zshrc"].includes(name)) return "shell";
  if (ext === ".json" || ext === ".jsonc") return "json";
  if ([".html", ".htm", ".xhtml"].includes(ext)) return "html";
  if ([".ps1", ".psm1", ".psd1"].includes(ext)) return "powershell";
  if ([".bat", ".cmd"].includes(ext)) return "batch";
  if ([".js", ".ts", ".jsx", ".tsx"].includes(ext)) return "js";
  if ([".sql"].includes(ext)) return "sql";
  return "text";
}

function highlightSource(src, errorLines, lang) {
  if (lang === "python") return highlightPython(src, errorLines);
  if (lang === "json") return highlightJson(src, errorLines);
  if (lang === "html") return highlightHtml(src, errorLines);
  return highlightSimple(src, errorLines, lang);
}

function highlightJson(src, errorLines) {
  let html = "";
  let lineBuf = "";
  let line = 1;
  let i = 0;
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
  while (i < src.length) {
    const ch = src[i];
    if (ch === '"') {
      let j = i + 1;
      while (j < src.length && src[j] !== '"') j += src[j] === "\\" ? 2 : 1;
      j = Math.min(src.length, j + 1);
      let k = j;
      while (k < src.length && /[ \t\r\n]/.test(src[k])) k += 1;
      pushToken(src.slice(i, j), src[k] === ":" ? "fn" : "str");
      i = j;
      continue;
    }
    if (ch === "-" || /[0-9]/.test(ch)) {
      const match = src.slice(i).match(/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/);
      if (match && match[0] !== "-") {
        pushToken(match[0], "num");
        i += match[0].length;
        continue;
      }
    }
    const word = src.slice(i).match(/^(?:true|false|null)(?![A-Za-z0-9_])/);
    if (word) {
      pushToken(word[0], "kw");
      i += word[0].length;
      continue;
    }
    if ("{}[]:,".includes(ch)) {
      pushToken(ch, "op");
      i += 1;
      continue;
    }
    pushToken(ch, "");
    i += 1;
  }
  html += errorLines.has(line) ? `<span class="errline">${lineBuf}</span>` : lineBuf;
  return html;
}

function highlightHtml(src, errorLines) {
  let html = "";
  let lineBuf = "";
  let line = 1;
  let i = 0;
  let raw = "";
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
  function paintTag(rawTag) {
    const open = rawTag.match(/^<\/?/);
    pushToken(open[0], "op");
    let cursor = open[0].length;
    const name = rawTag.slice(cursor).match(/^[A-Za-z][\w:-]*/);
    if (name) {
      pushToken(name[0], "fn");
      cursor += name[0].length;
    }
    while (cursor < rawTag.length) {
      const ch = rawTag[cursor];
      if (ch === '"' || ch === "'") {
        let end = cursor + 1;
        while (end < rawTag.length && rawTag[end] !== ch) end += rawTag[end] === "\\" ? 2 : 1;
        end = Math.min(rawTag.length, end + 1);
        pushToken(rawTag.slice(cursor, end), "str");
        cursor = end;
        continue;
      }
      if (/[A-Za-z_:]/.test(ch)) {
        const word = rawTag.slice(cursor).match(/^[A-Za-z_:][\w:.-]*/);
        pushToken(word[0], "cls");
        cursor += word[0].length;
        continue;
      }
      pushToken(ch, "op");
      cursor += 1;
    }
  }
  while (i < src.length) {
    if (raw) {
      const close = new RegExp("</" + raw + "\\s*>", "i").exec(src.slice(i));
      if (!close) {
        pushToken(src.slice(i), "");
        i = src.length;
        break;
      }
      pushToken(src.slice(i, i + close.index), "");
      i += close.index;
      raw = "";
      continue;
    }
    if (src.startsWith("<!--", i)) {
      const end = src.indexOf("-->", i + 4);
      const stop = end < 0 ? src.length : end + 3;
      pushToken(src.slice(i, stop), "comment");
      i = stop;
      continue;
    }
    if (src[i] === "<" && /[A-Za-z!/?]/.test(src[i + 1] || "")) {
      let end = i + 1;
      let quote = "";
      while (end < src.length) {
        const ch = src[end];
        if (quote) {
          if (ch === quote) quote = "";
          end += ch === "\\" ? 2 : 1;
          continue;
        }
        if (ch === '"' || ch === "'") {
          quote = ch;
          end += 1;
          continue;
        }
        if (ch === ">") {
          end += 1;
          break;
        }
        end += 1;
      }
      const rawTag = src.slice(i, end);
      paintTag(rawTag);
      const opened = rawTag.match(/^<([A-Za-z][\w:-]*)/);
      if (opened && ["script", "style", "pre", "textarea"].includes(opened[1].toLowerCase()) && !/\/>\s*$/.test(rawTag)) {
        raw = opened[1].toLowerCase();
      }
      i = end;
      continue;
    }
    const next = src.indexOf("<", i + 1);
    const stop = next < 0 ? src.length : next;
    pushToken(src.slice(i, stop), "");
    i = stop === i ? i + 1 : stop;
  }
  html += errorLines.has(line) ? `<span class="errline">${lineBuf}</span>` : lineBuf;
  return html;
}

function highlightSimple(src, errorLines, lang) {
  const table = {
    shell: ["#", "if then else elif fi for while do done case esac function return select until in time local export unset readonly declare typeset trap source alias echo printf read cd pwd exit set shift eval exec let test"],
    powershell: ["#", "function if else elseif foreach while do until switch return param filter try catch finally for break continue class enum throw begin process end in trap"],
    js: ["//", "function return if else for while const let var class extends new this import export from async await try catch finally throw break continue switch case default typeof"],
    sql: ["--", "select from where insert into update delete create table join left right inner on as and or not null group by order limit"],
    batch: ["rem", "echo set if else goto call for in do exist not"],
  };
  const spec = table[lang] || ["#", ""];
  const comment = spec[0];
  const keywords = new Set(spec[1].split(" ").filter(Boolean));
  return src.split("\n").map((line, index) => {
    const html = highlightLine(line, comment, keywords);
    return errorLines.has(index + 1) ? `<span class="errline">${html}</span>` : html;
  }).join("\n");
}

function highlightLine(line, comment, keywords) {
  let html = "";
  let i = 0;
  const commentAt = (pos) => {
    if (comment === "rem") {
      const head = line.slice(pos).match(/^\s*(?:rem\b|::)/i);
      return head && pos === 0 ? head[0].length : 0;
    }
    return line.slice(pos, pos + comment.length) === comment ? comment.length : 0;
  };
  while (i < line.length) {
    const mark = commentAt(i);
    if (mark && (comment !== "rem" || /^\s*(?:rem\b|::)/i.test(line.slice(i)))) {
      html += `<span class="comment">${esc(line.slice(i))}</span>`;
      break;
    }
    const ch = line[i];
    if (ch === '"' || ch === "'") {
      let j = i + 1;
      while (j < line.length && line[j] !== ch) j += line[j] === "\\" ? 2 : 1;
      j = Math.min(line.length, j + 1);
      html += `<span class="str">${esc(line.slice(i, j))}</span>`;
      i = j;
      continue;
    }
    if (ch === "$") {
      const match = line.slice(i).match(/^\$\{[^}]+\}|^\$[A-Za-z_][A-Za-z0-9_]*/);
      if (match) {
        html += `<span class="fn">${esc(match[0])}</span>`;
        i += match[0].length;
        continue;
      }
    }
    if (/[A-Za-z_]/.test(ch)) {
      const match = line.slice(i).match(/^[A-Za-z_][A-Za-z0-9_]*/);
      const word = match[0];
      const cls = keywords.has(word.toLowerCase()) ? "kw" : "";
      html += cls ? `<span class="${cls}">${esc(word)}</span>` : esc(word);
      i += word.length;
      continue;
    }
    if (/[0-9]/.test(ch)) {
      const match = line.slice(i).match(/^\d+/);
      html += `<span class="num">${esc(match[0])}</span>`;
      i += match[0].length;
      continue;
    }
    html += esc(ch);
    i += 1;
  }
  return html;
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
  const lang = languageOf(current && current.path);
  highlightEl().innerHTML = highlightSource(text, errorLineSet(), lang) + "\n";
  renderGutter();
  renderTabs();
  renderFunctions();
  syncScroll();
  updateStatus();
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
    if (current && (current.problems || []).some((item) => item.line === line && item.severity !== "info")) classes.push("err");
    const mark = covered && covered.missing && covered.missing.includes(line) ? "·" : "";
    html += `<div class="${classes.join(" ")}" data-line="${line}">${mark}${line}</div>`;
  }
  $("gutter").innerHTML = html;
}

function renderTabs() {
  $("tabs").innerHTML = "";
  S.tabs.forEach((item, index) => {
    const tabNode = document.createElement("div");
    tabNode.className = "tab" + (index === S.active ? " on" : "");
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tab-name";
    const name = item.path.split(/[\\/]/).pop();
    button.textContent = (item.dirty ? "● " : "") + name;
    button.onclick = () => activate(index);
    const close = document.createElement("button");
    close.type = "button";
    close.className = "tab-close";
    close.title = "Datei schließen";
    close.textContent = "×";
    close.onclick = (event) => {
      event.stopPropagation();
      closeTab(index);
    };
    tabNode.appendChild(button);
    tabNode.appendChild(close);
    $("tabs").appendChild(tabNode);
  });
}

function closeTab(index) {
  const item = S.tabs[index];
  if (!item) return;
  const finish = () => {
    S.tabs.splice(index, 1);
    if (!S.tabs.length) S.active = -1;
    else if (S.active > index) S.active -= 1;
    else if (S.active === index) S.active = Math.min(index, S.tabs.length - 1);
    const current = tab();
    codeEl().value = current ? current.content : "";
    renderEditor();
    updateStatus(current ? current.path : "Bereit");
  };
  if (!item.dirty) {
    finish();
    return;
  }
  const body = document.createElement("p");
  body.textContent = item.path.split(/[\\/]/).pop() + " ist nicht gespeichert.";
  modal("Datei schließen", body, [
    { label: "Abbrechen", run: () => {} },
    { label: "Schließen", run: finish },
  ]);
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
  const current = tab();
  $("st-pos").textContent = `Zeile ${pos.line}, Spalte ${pos.col + 1}`;
  const names = { python: "Python", powershell: "PowerShell", shell: "Shell", batch: "Batch", json: "JSON", html: "HTML", js: "JavaScript", sql: "SQL", text: "Text" };
  const lang = languageOf(current && current.path);
  if ($("st-lang")) $("st-lang").textContent = names[lang] || "Text";
  if ($("st-eol")) $("st-eol").textContent = current && current.content.includes("\r\n") ? "CRLF" : "LF";
  if (extra) $("st-mode").textContent = extra + (current && current.writable === false ? " · nur lesen" : "");
  const py = S.python || "";
  $("st-py").textContent = py ? py.split(/[\\/]/).pop() : "";
}

function activate(index) {
  S.active = index;
  S.symbol = null;
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
  updateStatus();
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

function kindLabel(kind) {
  return {
    function: "Funktion",
    method: "Methode",
    class: "Klasse",
    filter: "Filter",
    label: "Sprungmarke",
    key: "Schlüssel",
    element: "Element",
    heading: "Überschrift",
  }[kind] || "Symbol";
}

function localSymbols(text, lang) {
  const items = [];
  const lines = String(text || "").split("\n");
  if (lang === "python") {
    let parent = "";
    let parentIndent = -1;
    lines.forEach((line, index) => {
      const match = line.match(/^(\s*)(async\s+def|def|class)\s+([A-Za-z_][\w]*)/);
      if (!match) return;
      const indent = match[1].length;
      if (match[2] === "class") {
        parent = match[3];
        parentIndent = indent;
        items.push({ name: match[3], kind: "class", line: index + 1, end_line: index + 1, parent: "" });
        return;
      }
      if (parent && indent > parentIndent) {
        items.push({ name: match[3], kind: "method", line: index + 1, end_line: index + 1, parent });
        return;
      }
      parent = "";
      parentIndent = -1;
      items.push({ name: match[3], kind: "function", line: index + 1, end_line: index + 1, parent: "" });
    });
    return items;
  }
  if (lang === "powershell") {
    lines.forEach((line, index) => {
      const match = line.match(/^\s*(function|filter|class)\s+([A-Za-z_][\w-]*)/i);
      if (!match) return;
      const word = match[1].toLowerCase();
      const kind = word === "class" ? "class" : (word === "filter" ? "filter" : "function");
      items.push({ name: match[2], kind, line: index + 1, end_line: index + 1, parent: "" });
    });
    return items;
  }
  if (lang === "shell") {
    const skip = new Set(["if", "elif", "else", "while", "for", "until", "case", "select", "time", "coproc"]);
    lines.forEach((line, index) => {
      const named = line.match(/^\s*function\s+([A-Za-z_][\w]*)\b/);
      const classic = line.match(/^\s*([A-Za-z_][\w]*)\s*\(\s*\)/);
      const name = named ? named[1] : (classic ? classic[1] : "");
      if (!name || skip.has(name)) return;
      items.push({ name, kind: "function", line: index + 1, end_line: index + 1, parent: "" });
    });
    return items;
  }
  if (lang === "batch") {
    lines.forEach((line, index) => {
      const match = line.match(/^\s*:([A-Za-z_][\w-]*)/);
      if (match) items.push({ name: match[1], kind: "label", line: index + 1, end_line: index + 1, parent: "" });
    });
    return items;
  }
  if (lang === "json") {
    lines.forEach((line, index) => {
      const match = line.match(/^\s*"((?:\\.|[^"\\])*)"\s*:/);
      if (match) items.push({ name: match[1], kind: "key", line: index + 1, end_line: index + 1, parent: "" });
    });
    return items;
  }
  if (lang === "html") {
    lines.forEach((line, index) => {
      const fn = line.match(/\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)/);
      if (fn) items.push({ name: fn[1], kind: "function", line: index + 1, end_line: index + 1, parent: "" });
      const tag = line.match(/<([A-Za-z][\w:-]*)\b([^>]*)>/);
      if (!tag) return;
      const tagName = tag[1].toLowerCase();
      const idMatch = tag[2].match(/\bid\s*=\s*["']([^"']+)["']/i);
      const textMatch = line.slice(line.indexOf(">") + 1).match(/^([^<]+)/);
      const text = textMatch ? textMatch[1].replace(/\s+/g, " ").trim() : "";
      const heading = /^h[1-6]$/.test(tagName);
      if (!idMatch && !heading) return;
      let label = tagName;
      if (idMatch) label += "#" + idMatch[1];
      if (heading && text) label += " " + text;
      items.push({ name: label, kind: heading ? "heading" : "element", line: index + 1, end_line: index + 1, parent: "" });
    });
  }
  return items;
}

function symbolList(current) {
  const local = localSymbols(current.content, languageOf(current.path));
  if (local.length) return local;
  return current.outline || [];
}

function propRow(host, label, value) {
  const row = document.createElement("div");
  row.className = "prop-row";
  const name = document.createElement("span");
  name.textContent = label;
  const text = document.createElement("div");
  text.textContent = value;
  row.appendChild(name);
  row.appendChild(text);
  host.appendChild(row);
}

function renderProperties(current, item) {
  const host = $("fn-props-body");
  if (!host) return;
  host.innerHTML = "";
  if (!current) {
    propRow(host, "Datei", "keine");
    return;
  }
  const lines = current.content ? current.content.split("\n").length : 1;
  propRow(host, "Datei", current.path.split(/[\\/]/).pop());
  propRow(host, "Sprache", $("st-lang") ? $("st-lang").textContent : languageOf(current.path));
  propRow(host, "Zeilen", String(lines));
  propRow(host, "Geändert", current.dirty ? "ja" : "nein");
  if (!item) return;
  propRow(host, "Name", item.name);
  propRow(host, "Art", kindLabel(item.kind));
  propRow(host, "Zeile", String(item.line));
  if (item.params) propRow(host, "Parameter", item.params);
  if (item.kind === "key" || item.kind === "label") return;
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "Im Fenster prüfen";
  button.onclick = () => {
    revealLine(item.line);
    probeWindow("function").catch((err) => toast(err.message));
  };
  host.appendChild(button);
}

function renderFunctions() {
  const host = $("fn-list");
  if (!host) return;
  const current = tab();
  host.innerHTML = "";
  if (!current) {
    renderProperties(null, null);
    return;
  }
  const query = (($("fn-filter") && $("fn-filter").value) || "").toLowerCase();
  const items = symbolList(current).filter((item) => !query || String(item.name).toLowerCase().includes(query));
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "fn-empty";
    empty.textContent = languageOf(current.path) === "html" ? "Kein Element in dieser Datei" : "Keine Funktion in dieser Datei";
    host.appendChild(empty);
  }
  const selected = items.find((item) => S.symbol && S.symbol.name === item.name && S.symbol.line === item.line) || null;
  items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "outline-item fn-item" + (selected === item ? " on" : "");
    button.textContent = (item.parent ? item.parent + "." : "") + item.name;
    button.title = kindLabel(item.kind) + ", Zeile " + item.line;
    button.onclick = () => {
      S.symbol = item;
      revealLine(item.line);
      renderFunctions();
    };
    host.appendChild(button);
  });
  renderProperties(current, selected);
}

function showRibbon(name) {
  document.querySelectorAll("[data-ribbon-page]").forEach((page) => {
    page.classList.toggle("hidden", page.dataset.ribbonPage !== name);
  });
  document.querySelectorAll("#ribbon-tabs [data-ribbon]").forEach((button) => {
    button.classList.toggle("on", button.dataset.ribbon === name);
  });
}

function paneOpen(id) {
  const node = $(id);
  return !!node && !node.classList.contains("collapsed");
}

function setPane(id, open) {
  const node = $(id);
  if (node) node.classList.toggle("collapsed", !open);
  const resizer = $(id + "-resizer");
  if (resizer) resizer.classList.toggle("collapsed", !open);
}

function showDock(name) {
  setPane("right", true);
  S.dock = name;
  const functions = $("dock-functions");
  const ai = $("dock-ai");
  if (functions) functions.classList.toggle("hidden", name !== "functions");
  if (ai) ai.classList.toggle("hidden", name !== "ai");
  document.querySelectorAll("[data-dock]").forEach((button) => button.classList.toggle("on", button.dataset.dock === name));
}

function toggleDock(name) {
  if (paneOpen("right") && S.dock === name) setPane("right", false);
  else showDock(name);
}

function setBottom(name) {
  setPane("bottom", true);
  S.bottom = name;
  document.querySelectorAll("#bottom-tabs button").forEach((button) => {
    button.classList.toggle("on", button.dataset.panel === name);
  });
  renderPanel();
}

function toggleBottom(name) {
  if (paneOpen("bottom") && S.bottom === name) setPane("bottom", false);
  else setBottom(name);
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
    studio: renderStudio,
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

function allBreakpoints() {
  const points = [];
  Object.entries(S.breaks).forEach(([file, lines]) => {
    Object.entries(lines || {}).forEach(([line, condition]) => {
      points.push({ file, line: Number(line), condition: condition || null });
    });
  });
  return points;
}

function scheduleRecovery() {
  clearTimeout(S.recoveryTimer);
  S.recoveryTimer = setTimeout(() => {
    const current = tab();
    if (!current || !current.path || current.content === current.saved) return;
    api("/api/studio", { action: "recovery", path: current.path, content: current.content }).catch(() => {});
  }, 1200);
}

function renderTerminal(host) {
  const select = document.createElement("select");
  const automatic = document.createElement("option");
  automatic.value = "";
  automatic.textContent = "Standard-Shell";
  select.appendChild(automatic);
  apiGet("/api/studio?action=shells").then((data) => {
    (data.shells || []).forEach((item) => {
      const option = document.createElement("option");
      option.value = item.path;
      option.textContent = item.label;
      if (S.terminalShell === item.path) option.selected = true;
      select.appendChild(option);
    });
  }).catch(() => {});
  select.onchange = async () => {
    S.terminalShell = select.value;
    if (S.terminalId) {
      await api("/api/terminal", { action: "close", id: S.terminalId }).catch(() => {});
      S.terminalId = "";
      S.terminalText = "";
    }
    await startTerminal();
  };
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
  host.appendChild(select);
  host.appendChild(pre);
  host.appendChild(input);
  if (!S.terminalId) startTerminal();
}

async function startTerminal() {
  const data = await api("/api/terminal", { action: "start", shell: S.terminalShell || "" });
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
  input.id = "project-query";
  input.placeholder = "Suche in Dateien, Symbolen, Einstellungen";
  const repl = document.createElement("input");
  repl.id = "project-replace";
  repl.placeholder = "Ersetzen durch, nur im Workspace";
  const row = document.createElement("div");
  const find = document.createElement("button");
  find.type = "button";
  find.textContent = "Suchen";
  const preview = document.createElement("button");
  preview.type = "button";
  preview.textContent = "Vorschau";
  const apply = document.createElement("button");
  apply.type = "button";
  apply.textContent = "Alle ersetzen";
  const caseBox = document.createElement("label");
  const caseInput = document.createElement("input");
  caseInput.type = "checkbox";
  caseInput.id = "project-case";
  caseBox.appendChild(caseInput);
  caseBox.append(" Groß/Klein");
  const wordBox = document.createElement("label");
  const wordInput = document.createElement("input");
  wordInput.type = "checkbox";
  wordInput.id = "project-word";
  wordBox.appendChild(wordInput);
  wordBox.append(" Ganzes Wort");
  const regexBox = document.createElement("label");
  const regexInput = document.createElement("input");
  regexInput.type = "checkbox";
  regexInput.id = "project-regex";
  regexBox.appendChild(regexInput);
  regexBox.append(" Regex");
  const list = document.createElement("div");
  list.id = "project-hits";
  const runSearch = async () => {
    const data = await api("/api/search", { query: input.value });
    list.textContent = "";
    data.hits.forEach((hit) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "hit";
      button.textContent = `${hit.kind} ${hit.path}:${hit.line} ${hit.text}`;
      button.onclick = () => { if (hit.kind !== "setting") openPath(hit.path, hit.line); };
      list.appendChild(button);
    });
  };
  input.onkeydown = (event) => { if (event.key === "Enter") runSearch().catch((err) => toast(err.message)); };
  find.onclick = () => runSearch().catch((err) => toast(err.message));
  preview.onclick = () => projectReplace(true).catch((err) => toast(err.message));
  apply.onclick = () => projectReplace(false).catch((err) => toast(err.message));
  row.appendChild(find);
  row.appendChild(preview);
  row.appendChild(apply);
  row.appendChild(caseBox);
  row.appendChild(wordBox);
  row.appendChild(regexBox);
  host.appendChild(input);
  host.appendChild(repl);
  host.appendChild(row);
  host.appendChild(list);
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
  path.value = S.dbPath || "beispiele/demo.sqlite";
  const sql = document.createElement("textarea");
  sql.style.width = "100%";
  sql.value = S.dbSql || "CREATE TABLE IF NOT EXISTS person (id INTEGER PRIMARY KEY, name TEXT);\nSELECT name FROM sqlite_master;";
  const run = document.createElement("button");
  run.type = "button";
  run.textContent = "SQL ausführen";
  const create = document.createElement("button");
  create.type = "button";
  create.textContent = "Datenbank anlegen";
  const out = document.createElement("div");
  run.onclick = async () => {
    const result = await api("/api/db", { engine: "sqlite", path: path.value, sql: sql.value });
    out.textContent = JSON.stringify(result.rows || result, null, 2).slice(0, 5000);
  };
  create.onclick = () => openDatabaseCreator();
  host.appendChild(path);
  host.appendChild(sql);
  const row = document.createElement("div");
  row.className = "row";
  row.append(run, create);
  host.appendChild(row);
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
  const hostName = document.createElement("input");
  hostName.placeholder = "PowerShell-Host, leer = dieser Rechner";
  const user = document.createElement("input");
  user.placeholder = "Benutzer für SSH";
  const psCommand = document.createElement("textarea");
  psCommand.placeholder = "Get-Date oder Skript. Leer = aktuelle Datei.";
  psCommand.style.width = "100%";
  psCommand.style.height = "70px";
  const local = document.createElement("button");
  local.type = "button";
  local.textContent = "PS lokal";
  const winrm = document.createElement("button");
  winrm.type = "button";
  winrm.textContent = "WinRM";
  const remoteSsh = document.createElement("button");
  remoteSsh.type = "button";
  remoteSsh.textContent = "PS per SSH";
  const trace = document.createElement("button");
  trace.type = "button";
  trace.textContent = "Ablauf verfolgen";
  async function powershellBody() {
    if (psCommand.value.trim()) return psCommand.value;
    const current = tab();
    if (!current) throw new Error("Kein Befehl und keine Datei");
    return current.content;
  }
  async function runRemote(transport) {
    const data = await api("/api/studio", {
      action: "remote",
      transport,
      host: hostName.value,
      user: user.value,
      command: await powershellBody(),
    });
    S.output = "";
    S.runId = data.id;
    S.runFrom = 0;
    setBottom("output");
    pollRun();
    toast(data.message || "Remote-Befehl");
  }
  local.onclick = () => runRemote("local").catch((err) => toast(err.message));
  winrm.onclick = () => runRemote("winrm").catch((err) => toast(err.message));
  remoteSsh.onclick = () => runRemote("ssh").catch((err) => toast(err.message));
  trace.onclick = async () => {
    const current = tab();
    if (!current) return toast("Keine Datei");
    await saveTab();
    const data = await api("/api/studio", {
      action: "trace",
      path: current.path,
      content: current.content,
      transport: hostName.value.trim() ? "ssh" : "local",
      host: hostName.value,
      user: user.value,
    });
    S.output = "";
    S.runId = data.id;
    S.runFrom = 0;
    setBottom("output");
    pollRun();
  };
  host.appendChild(target);
  host.appendChild(command);
  host.appendChild(ssh);
  host.appendChild(ps);
  host.appendChild(wsl);
  host.appendChild(hostName);
  host.appendChild(user);
  host.appendChild(psCommand);
  host.appendChild(local);
  host.appendChild(winrm);
  host.appendChild(remoteSsh);
  host.appendChild(trace);
  host.appendChild(out);
}

function appendOutput(text) {
  S.output = (S.output || "") + text;
  const node = $("output-text");
  if (node) node.textContent = S.output;
}

async function runFile(debug) {
  try {
    const current = tab();
    if (!current) return toast("Keine Datei");
    unfoldAll();
    await saveTab();
    S.output = "";
    if (!debug) {
      setBottom("output");
      const data = await api("/api/run", { mode: "file", path: current.path });
      S.runId = data.id;
      S.runFrom = 0;
      pollRun();
      updateStatus("Läuft");
      return;
    }
    const points = allBreakpoints();
    await api("/api/debug/start", { path: current.path, breakpoints: points });
    S.debugFrom = 0;
    setBottom("debug");
    pollDebug();
    updateStatus("Debugger");
  } catch (err) {
    toast(err.message);
  }
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
    if (data.paused.file) {
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
  const points = allBreakpoints();
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
  const data = await api("/api/format", { content: current.content, path: current.path });
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

function closeModal() {
  $("modal").classList.add("hidden");
}

function modal(title, body, buttons) {
  const root = $("modal");
  root.classList.remove("hidden");
  root.innerHTML = "";
  const box = document.createElement("div");
  box.className = "box";
  const head = document.createElement("div");
  head.className = "modal-head";
  const heading = document.createElement("h2");
  heading.textContent = title;
  const close = document.createElement("button");
  close.type = "button";
  close.className = "modal-x";
  close.title = "Schließen";
  close.textContent = "×";
  close.onclick = () => closeModal();
  head.appendChild(heading);
  head.appendChild(close);
  box.appendChild(head);
  box.appendChild(body);
  root.onclick = (event) => {
    if (event.target === root) closeModal();
  };
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

function setBuffer(content, selStart, selEnd) {
  const current = tab();
  if (!current) return;
  current.content = content;
  current.dirty = content !== current.saved;
  renderEditor();
  const area = codeEl();
  area.selectionStart = selStart;
  area.selectionEnd = selEnd == null ? selStart : selEnd;
  updateStatus();
}

function lineBounds(text, start, end) {
  const from = text.lastIndexOf("\n", Math.max(0, start - 1)) + 1;
  let to = text.indexOf("\n", Math.max(start, end));
  if (to === -1) to = text.length;
  if (end > start && text[end - 1] === "\n") to = end - 1;
  return { start: from, end: to };
}

function lineIndexes(text, start, end) {
  const bounds = lineBounds(text, start, end);
  const startLine = text.slice(0, bounds.start).split("\n").length - 1;
  const endLine = text.slice(0, bounds.end).split("\n").length - 1;
  return { bounds, startLine, endLine };
}

function commentMark(path) {
  const lang = languageOf(path);
  if (lang === "json") return null;
  if (lang === "html") return { line: "<!--", end: "-->" };
  if (lang === "js") return { line: "//" };
  if (lang === "sql") return { line: "--" };
  if (lang === "batch") return { line: "REM" };
  return { line: "#" };
}

function toggleComment() {
  const current = tab();
  if (!current) return;
  const area = codeEl();
  const text = area.value;
  const { bounds, startLine, endLine } = lineIndexes(text, area.selectionStart, area.selectionEnd);
  const lines = text.split("\n");
  const spec = commentMark(current.path);
  if (!spec) return toast("JSON-Kommentare sind kein gültiges JSON.");
  const body = lines.slice(startLine, endLine + 1);
  if (spec.end) {
    const startRe = new RegExp("^(\\s*)" + spec.line.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s?");
    const endRe = new RegExp("\\s?" + spec.end.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s*$");
    const commented = body.every((line) => !line.trim() || (startRe.test(line) && endRe.test(line)));
    const next = body.map((line) => {
      if (!line.trim()) return line;
      if (commented) return line.replace(startRe, "$1").replace(endRe, "");
      return line.replace(/^(\s*)/, "$1" + spec.line + " ").replace(/\s*$/, " " + spec.end);
    });
    lines.splice(startLine, body.length, ...next);
    const updated = lines.join("\n");
    setBuffer(updated, bounds.start, bounds.start + next.join("\n").length);
    return;
  }
  const mark = spec.line;
  const commented = body.every((line) => !line.trim() || new RegExp("^\\s*" + mark.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s?").test(line));
  const next = body.map((line) => {
    if (!line.trim()) return line;
    if (commented) return line.replace(new RegExp("^(\\s*)" + mark.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s?"), "$1");
    return line.replace(/^(\s*)/, "$1" + mark + " ");
  });
  lines.splice(startLine, body.length, ...next);
  const updated = lines.join("\n");
  setBuffer(updated, bounds.start, bounds.start + next.join("\n").length);
}

function duplicateLines(dir) {
  const current = tab();
  if (!current) return;
  const area = codeEl();
  const text = area.value;
  const info = lineIndexes(text, area.selectionStart, area.selectionEnd);
  const lines = text.split("\n");
  const block = lines.slice(info.startLine, info.endLine + 1);
  const at = dir < 0 ? info.startLine : info.endLine + 1;
  lines.splice(at, 0, ...block);
  const updated = lines.join("\n");
  const cursor = dir < 0 ? info.bounds.start : info.bounds.start + block.join("\n").length + 1;
  setBuffer(updated, cursor, cursor);
}

function moveLines(dir) {
  const current = tab();
  if (!current) return;
  const area = codeEl();
  const text = area.value;
  const info = lineIndexes(text, area.selectionStart, area.selectionEnd);
  const lines = text.split("\n");
  if (dir < 0 && info.startLine === 0) return;
  if (dir > 0 && info.endLine >= lines.length - 1) return;
  const block = lines.slice(info.startLine, info.endLine + 1);
  if (dir > 0) {
    const next = lines[info.endLine + 1];
    lines.splice(info.startLine, block.length + 1, next, ...block);
  } else {
    const prev = lines[info.startLine - 1];
    lines.splice(info.startLine - 1, block.length + 1, ...block, prev);
  }
  const updated = lines.join("\n");
  const lineStart = updated.split("\n").slice(0, info.startLine + dir).join("\n");
  const pos = lineStart.length ? lineStart.length + 1 : 0;
  setBuffer(updated, pos, pos + block.join("\n").length);
}

function deleteLines() {
  const current = tab();
  if (!current) return;
  const area = codeEl();
  const text = area.value;
  const info = lineIndexes(text, area.selectionStart, area.selectionEnd);
  const lines = text.split("\n");
  lines.splice(info.startLine, info.endLine - info.startLine + 1);
  const updated = lines.join("\n");
  const prefix = updated.split("\n").slice(0, info.startLine).join("\n");
  const pos = prefix.length ? prefix.length + (info.startLine ? 1 : 0) : 0;
  setBuffer(updated, pos, pos);
}

function joinLines() {
  const current = tab();
  if (!current) return;
  const area = codeEl();
  const text = area.value;
  const info = lineIndexes(text, area.selectionStart, area.selectionEnd);
  const lines = text.split("\n");
  const target = info.startLine;
  if (target >= lines.length - 1) return;
  lines[target] = lines[target].replace(/\s*$/, "") + " " + lines[target + 1].replace(/^\s*/, "");
  lines.splice(target + 1, 1);
  const updated = lines.join("\n");
  const pos = updated.split("\n").slice(0, target).join("\n").length + (target ? 1 : 0) + lines[target].length;
  setBuffer(updated, pos, pos);
}

function shiftLines(out) {
  const current = tab();
  if (!current) return;
  const area = codeEl();
  const text = area.value;
  const info = lineIndexes(text, area.selectionStart, area.selectionEnd);
  const lines = text.split("\n");
  for (let index = info.startLine; index <= info.endLine; index += 1) {
    lines[index] = out ? lines[index].replace(/^(?:\t| {1,4})/, "") : "\t" + lines[index];
  }
  const updated = lines.join("\n");
  setBuffer(updated, info.bounds.start, info.bounds.start);
}

function indentOrTab() {
  const area = codeEl();
  if (area.selectionStart !== area.selectionEnd && area.value.slice(area.selectionStart, area.selectionEnd).includes("\n")) {
    shiftLines(false);
    return;
  }
  const current = tab();
  if (!current) return;
  const start = area.selectionStart;
  setBuffer(area.value.slice(0, start) + "\t" + area.value.slice(area.selectionEnd), start + 1, start + 1);
}

function toggleCase() {
  const current = tab();
  if (!current) return;
  const area = codeEl();
  let start = area.selectionStart;
  let end = area.selectionEnd;
  const text = area.value;
  if (start === end) {
    const left = text.slice(0, start).match(/[A-Za-z0-9_]*$/) || [""];
    const right = text.slice(start).match(/^[A-Za-z0-9_]*/) || [""];
    start -= left[0].length;
    end += right[0].length;
  }
  if (start === end) return;
  const raw = text.slice(start, end);
  const next = raw === raw.toLowerCase() ? raw.toUpperCase() : raw.toLowerCase();
  setBuffer(text.slice(0, start) + next + text.slice(end), start, start + next.length);
}

function toggleWrap() {
  S.wrap = !S.wrap;
  $("editor").classList.toggle("wrap", S.wrap);
  toast(S.wrap ? "Zeilenumbruch an" : "Zeilenumbruch aus");
}

function editorHistory(redo) {
  const area = codeEl();
  area.focus();
  document.execCommand(redo ? "redo" : "undo");
  const current = tab();
  if (!current) return;
  current.content = area.value;
  current.dirty = current.content !== current.saved;
  renderEditor();
}

function goToLine() {
  promptModal("Gehe zu Zeile", "Zeilennummer", String(cursorPos().line), (value) => {
    const line = Number(value);
    if (!line || line < 1) return;
    revealLine(line);
  });
}

function selectNextOccurrence() {
  const current = tab();
  if (!current) return;
  const area = codeEl();
  const text = area.value;
  let needle = text.slice(area.selectionStart, area.selectionEnd);
  let from = area.selectionEnd;
  if (!needle) {
    const left = text.slice(0, area.selectionStart).match(/[A-Za-z0-9_]*$/) || [""];
    const right = text.slice(area.selectionStart).match(/^[A-Za-z0-9_]*/) || [""];
    needle = left[0] + right[0];
    from = area.selectionStart - left[0].length;
    if (!needle) return;
    area.selectionStart = from;
    area.selectionEnd = from + needle.length;
    return;
  }
  let at = text.indexOf(needle, from);
  if (at < 0) at = text.indexOf(needle, 0);
  if (at < 0) return;
  area.selectionStart = at;
  area.selectionEnd = at + needle.length;
  area.focus();
}

function findOptions() {
  return {
    query: $("find-query").value,
    replacement: $("find-replace").value,
    case: $("find-case").classList.contains("on"),
    word: $("find-word").classList.contains("on"),
    regex: $("find-regex").classList.contains("on"),
  };
}

function findPattern(options) {
  if (!options.query) return null;
  let source = options.regex ? options.query : options.query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  if (options.word) source = "\\b(?:" + source + ")\\b";
  return new RegExp(source, options.case ? "g" : "gi");
}

function findMatches(text, options) {
  const pattern = findPattern(options);
  if (!pattern) return [];
  const found = [];
  let match;
  while ((match = pattern.exec(text)) && found.length < 5000) {
    if (!match[0]) pattern.lastIndex += 1;
    found.push({ start: match.index, end: match.index + match[0].length, text: match[0] });
  }
  return found;
}

function refreshFindCount() {
  const current = tab();
  const node = $("find-count");
  if (!current || !node) return;
  try {
    const count = findMatches(current.content, findOptions()).length;
    node.textContent = count ? count + " Treffer" : "kein Treffer";
  } catch (err) {
    node.textContent = "Muster ungültig";
  }
}

function openFind(replace) {
  $("findbar").classList.remove("hidden");
  const area = codeEl();
  const selected = area.value.slice(area.selectionStart, area.selectionEnd);
  if (selected && !selected.includes("\n")) $("find-query").value = selected;
  (replace ? $("find-replace") : $("find-query")).focus();
  if (!replace) $("find-query").select();
  refreshFindCount();
}

function closeFind() {
  $("findbar").classList.add("hidden");
  codeEl().focus();
}

function findNext(dir) {
  const current = tab();
  if (!current) return;
  if ($("findbar").classList.contains("hidden")) openFind(false);
  let matches;
  try {
    matches = findMatches(current.content, findOptions());
  } catch (err) {
    $("find-count").textContent = "Muster ungültig";
    return;
  }
  refreshFindCount();
  if (!matches.length) return;
  const area = codeEl();
  const pos = dir < 0 ? area.selectionStart : area.selectionEnd;
  let pick = dir < 0 ? matches[matches.length - 1] : matches[0];
  if (dir < 0) {
    for (let index = matches.length - 1; index >= 0; index -= 1) {
      if (matches[index].end <= pos) { pick = matches[index]; break; }
    }
  } else {
    for (const item of matches) {
      if (item.start >= pos) { pick = item; break; }
    }
  }
  area.focus();
  area.selectionStart = pick.start;
  area.selectionEnd = pick.end;
}

function replaceCurrent(all) {
  const current = tab();
  if (!current) return;
  const options = findOptions();
  let pattern;
  try {
    pattern = findPattern(options);
  } catch (err) {
    toast("Muster ungültig");
    return;
  }
  if (!pattern) return;
  const area = codeEl();
  if (all) {
    const before = findMatches(current.content, options).length;
    const next = options.regex
      ? current.content.replace(pattern, options.replacement)
      : current.content.replace(pattern, () => options.replacement);
    setBuffer(next, 0, 0);
    toast(before + " ersetzt");
    refreshFindCount();
    return;
  }
  const matches = findMatches(current.content, options);
  const selected = matches.find((item) => item.start === area.selectionStart && item.end === area.selectionEnd);
  if (!selected) {
    findNext(1);
    return;
  }
  const next = current.content.slice(0, selected.start) + options.replacement + current.content.slice(selected.end);
  const cursor = selected.start + options.replacement.length;
  setBuffer(next, cursor, cursor);
  refreshFindCount();
  findNext(1);
}

function openProjectReplace() {
  setBottom("search");
  setTimeout(() => {
    const node = $("project-replace");
    if (node) node.focus();
  }, 0);
}

async function projectReplace(preview) {
  const query = ($("project-query") && $("project-query").value || "").trim();
  if (query.length < 1) return toast("Suchtext fehlt");
  if (!preview && !confirm("Treffer im Workspace ersetzen?")) return;
  const data = await api("/api/replace", {
    query,
    replacement: ($("project-replace") && $("project-replace").value) || "",
    case: $("project-case") && $("project-case").checked,
    word: $("project-word") && $("project-word").checked,
    regex: $("project-regex") && $("project-regex").checked,
    preview,
  });
  const host = $("project-hits");
  if (host) {
    host.textContent = "";
    const head = document.createElement("div");
    head.textContent = data.replacements + " Treffer in " + data.files.length + " Dateien" + (data.truncated ? " (Liste gekürzt)" : "");
    host.appendChild(head);
    data.files.forEach((file) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "hit";
      const sample = (file.lines[0] && file.lines[0].text) || "";
      button.textContent = file.count + "  " + file.path + "  " + sample;
      button.onclick = () => openPath(file.path, file.lines[0] ? file.lines[0].line : 1);
      host.appendChild(button);
    });
  }
  if (!preview) {
    toast(data.replacements + " Stellen ersetzt");
    const current = tab();
    if (current && current.path) {
      const fresh = await apiGet("/api/file?path=" + encodeURIComponent(current.path));
      current.content = fresh.content;
      current.saved = fresh.content;
      current.dirty = false;
      renderEditor();
    }
  }
}

function bindFindbar() {
  const toggle = (id) => {
    $(id).classList.toggle("on");
    refreshFindCount();
  };
  $("find-case").onclick = () => toggle("find-case");
  $("find-word").onclick = () => toggle("find-word");
  $("find-regex").onclick = () => toggle("find-regex");
  $("find-prev").onclick = () => findNext(-1);
  $("find-next").onclick = () => findNext(1);
  $("find-one").onclick = () => replaceCurrent(false);
  $("find-all").onclick = () => replaceCurrent(true);
  $("find-close").onclick = () => closeFind();
  $("find-query").addEventListener("input", refreshFindCount);
  $("find-query").addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); findNext(event.shiftKey ? -1 : 1); }
    if (event.key === "Escape") { event.preventDefault(); closeFind(); }
  });
  $("find-replace").addEventListener("keydown", (event) => {
    if (event.key === "Enter") { event.preventDefault(); replaceCurrent(event.ctrlKey || event.metaKey); }
    if (event.key === "Escape") { event.preventDefault(); closeFind(); }
  });
}

async function openGenerated(path, content) {
  const written = await api("/api/file", { path, content });
  await refreshTree();
  await openPath(written.path);
}

function runSession(data) {
  S.output = "";
  S.runId = data.id;
  S.runFrom = 0;
  setBottom("output");
  pollRun();
  if (data.message) toast(data.message);
}

async function buildExe() {
  const current = tab();
  if (!current) return toast("Keine Datei");
  await saveTab();
  const stem = (current.path.split(/[/\\]/).pop() || "ShatuApp").replace(/\.[^.]+$/, "") || "ShatuApp";
  const lang = languageOf(current.path);
  const data = await api("/api/studio", {
    action: "exe",
    path: current.path,
    content: current.content,
    name: stem,
    target: (lang === "powershell" || lang === "batch") ? "windows" : "native",
  });
  if (data.id) runSession(data);
  else toast(data.message || data.path || "EXE erzeugt");
}

function buildMsi() {
  const current = tab();
  const body = document.createElement("div");
  const name = document.createElement("input");
  name.value = "ShatuApp";
  const version = document.createElement("input");
  version.value = "1.0.0";
  const maker = document.createElement("input");
  maker.value = "ShatuIDE";
  body.append("Produkt", name, "Version", version, "Hersteller", maker);
  modal("MSI-Installer", body, [
    { label: "Abbrechen", run: () => {} },
    { label: "Erzeugen", run: () => {
      api("/api/studio", {
        action: "msi",
        name: name.value,
        version: version.value,
        manufacturer: maker.value,
        path: current ? current.path : "",
      }).then((data) => {
        toast(data.message || data.path);
        $("modal").classList.add("hidden");
      }).catch((err) => toast(err.message));
      return false;
    } },
  ]);
}

function buildModule() {
  const current = tab();
  if (!current) return toast("Keine Datei");
  promptModal("PowerShell-Modul", "Modulname", "Werkzeug", async (name) => {
    const data = await api("/api/studio", {
      action: "module",
      name,
      content: current.content,
      path: current.path,
      version: "1.0.0",
    });
    toast(data.message);
    await refreshTree();
    await openPath(data.psm1);
  });
}

function buildFunction() {
  const body = document.createElement("div");
  const name = document.createElement("input");
  name.value = "Get-Wert";
  const synopsis = document.createElement("input");
  synopsis.placeholder = "Kurzbeschreibung";
  const description = document.createElement("textarea");
  description.placeholder = "Beschreibung";
  const params = document.createElement("textarea");
  params.placeholder = "Name Typ Pflicht Hilfe, eine Zeile je Parameter\nWert int ja Die Zahl";
  body.append("Name", name, "Synopsis", synopsis, "Beschreibung", description, "Parameter", params);
  modal("Erweiterte Funktion", body, [
    { label: "Abbrechen", run: () => {} },
    { label: "Erzeugen", run: () => {
      const parameters = params.value.split("\n").map((line) => line.trim()).filter(Boolean).map((line) => {
        const parts = line.split(/\s+/);
        return { name: parts[0], type: parts[1] || "string", mandatory: parts[2] || "", help: parts.slice(3).join(" ") };
      });
      api("/api/studio", {
        action: "function",
        name: name.value,
        synopsis: synopsis.value,
        description: description.value,
        parameters,
      }).then(async (data) => {
        const current = tab();
        if (current && languageOf(current.path) === "powershell" && current.writable !== false) {
          const area = codeEl();
          area.focus();
          area.selectionStart = area.selectionEnd = area.value.length;
          replaceSelection((area.value.endsWith("\n") || !area.value ? "" : "\n") + data.content);
          toast("Funktion eingefügt");
        } else {
          await openGenerated("ausgabe/" + name.value + ".ps1", data.content);
        }
        $("modal").classList.add("hidden");
      }).catch((err) => toast(err.message));
      return false;
    } },
  ]);
}

function openGuiDesigner() {
  const controls = [];
  let selected = -1;
  let drag = null;
  const body = document.createElement("div");
  const title = document.createElement("input");
  title.value = "Werkzeug";
  const lang = document.createElement("select");
  [["powershell", "PowerShell WinForms"], ["python", "Python tkinter"]].forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    lang.appendChild(option);
  });
  const tools = document.createElement("div");
  tools.className = "row";
  const canvas = document.createElement("div");
  canvas.id = "gui-canvas";
  const nameInput = document.createElement("input");
  const textInput = document.createElement("input");
  function draw() {
    canvas.innerHTML = "";
    controls.forEach((item, index) => {
      const node = document.createElement("div");
      node.className = "widget" + (index === selected ? " on" : "");
      node.textContent = item.text || item.kind;
      node.style.left = item.x + "px";
      node.style.top = item.y + "px";
      node.style.width = item.w + "px";
      node.style.height = item.h + "px";
      node.onmousedown = (event) => {
        event.preventDefault();
        selected = index;
        drag = { index, ox: event.clientX, oy: event.clientY, x: item.x, y: item.y };
        nameInput.value = item.name;
        textInput.value = item.text;
        draw();
      };
      canvas.appendChild(node);
    });
  }
  canvas.onmousemove = (event) => {
    if (!drag) return;
    const item = controls[drag.index];
    item.x = Math.max(0, Math.min(500, drag.x + event.clientX - drag.ox));
    item.y = Math.max(0, Math.min(330, drag.y + event.clientY - drag.oy));
    drag.ox = event.clientX;
    drag.oy = event.clientY;
    drag.x = item.x;
    drag.y = item.y;
    draw();
  };
  canvas.onmouseup = () => { drag = null; };
  nameInput.onchange = () => { if (controls[selected]) { controls[selected].name = nameInput.value; } };
  textInput.onchange = () => { if (controls[selected]) { controls[selected].text = textInput.value; draw(); } };
  [["label", "Beschriftung"], ["button", "Schaltfläche"], ["textbox", "Eingabe"], ["checkbox", "Auswahl"], ["combo", "Liste"]].forEach(([kind, label]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.onclick = () => {
      const count = controls.length + 1;
      controls.push({ kind, name: kind + count, text: label, x: 16, y: 16 + controls.length * 36, w: 140, h: 28, items: kind === "combo" ? ["Eins", "Zwei"] : [] });
      selected = controls.length - 1;
      nameInput.value = controls[selected].name;
      textInput.value = controls[selected].text;
      draw();
    };
    tools.appendChild(button);
  });
  body.append("Titel", title, "Ziel", lang, tools, canvas, "Name", nameInput, "Text", textInput);
  modal("GUI entwerfen", body, [
    { label: "Abbrechen", run: () => {} },
    { label: "Skript erzeugen", run: () => {
      api("/api/studio", { action: "gui", title: title.value, language: lang.value, controls: controls.map((item) => ({ ...item })) })
        .then(async (data) => {
          await refreshTree();
          await openPath(data.path);
          $("modal").classList.add("hidden");
          toast(data.message);
        })
        .catch((err) => toast(err.message));
      return false;
    } },
  ]);
}

function buildService() {
  const body = document.createElement("div");
  const name = document.createElement("input");
  name.value = "ShatuDienst";
  const description = document.createElement("input");
  description.placeholder = "Beschreibung";
  body.append("Dienstname", name, "Beschreibung", description);
  modal("Windows-Dienst", body, [
    { label: "Abbrechen", run: () => {} },
    { label: "Skripte schreiben", run: () => {
      const current = tab();
      api("/api/studio", { action: "service", name: name.value, description: description.value, path: current ? current.path : "" })
        .then(async (data) => {
          toast(data.message);
          await refreshTree();
          if (data.path) await openPath(data.path);
          $("modal").classList.add("hidden");
        })
        .catch((err) => toast(err.message));
      return false;
    } },
  ]);
}

async function measureFile() {
  const current = tab();
  if (!current) return toast("Keine Datei");
  await saveTab();
  const data = await api("/api/studio", { action: "measure", path: current.path });
  runSession(data);
}

function restoreRecovery() {
  apiGet("/api/studio?action=recovery").then((data) => {
    const body = document.createElement("div");
    if (!data.items || !data.items.length) {
      body.textContent = "Keine Wiederherstellung.";
    }
    (data.items || []).forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "hit";
      button.textContent = item.time + "  " + item.path;
      button.onclick = async () => {
        const restored = await api("/api/studio", { action: "recovery-read", id: item.id });
        const existing = S.tabs.findIndex((tabItem) => tabItem.path === restored.path);
        if (existing >= 0) activate(existing);
        else {
          S.tabs.push({
            path: restored.path,
            content: restored.content,
            saved: "",
            dirty: true,
            writable: true,
            problems: [],
            outline: [],
          });
          activate(S.tabs.length - 1);
        }
        const current = tab();
        current.content = restored.content;
        current.dirty = true;
        renderEditor();
        $("modal").classList.add("hidden");
        toast("Wiederhergestellt, noch nicht gespeichert");
      };
      body.appendChild(button);
    });
    modal("Wiederherstellen", body, [{ label: "Schließen", run: () => {} }]);
  }).catch((err) => toast(err.message));
}

function labeled(host, caption, node) {
  const label = document.createElement("label");
  label.textContent = caption;
  host.appendChild(label);
  host.appendChild(node);
}

function openScriptCreator() {
  const body = document.createElement("div");
  const lang = document.createElement("select");
  lang.id = "script-lang";
  [["python", "Python"], ["powershell", "PowerShell"], ["shell", "Bash"], ["batch", "Batch"]].forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    lang.appendChild(option);
  });
  const name = document.createElement("input");
  name.id = "script-name";
  name.value = "Skript";
  const action = document.createElement("select");
  action.id = "script-action";
  [
    ["auto", "Aus der Aufgabe erkennen"],
    ["print", "Antworten ausgeben"],
    ["sum", "Zahlen addieren"],
    ["list", "Ordner auflisten"],
    ["fetch", "Webseite holen"],
    ["csv", "CSV-Zeile anhängen"],
    ["json", "JSON anzeigen"],
    ["write", "Text speichern"],
  ].forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    action.appendChild(option);
  });
  const purpose = document.createElement("textarea");
  purpose.id = "script-purpose";
  purpose.placeholder = "Was das Skript tun soll";
  const questions = document.createElement("textarea");
  questions.id = "script-questions";
  questions.placeholder = "Eine Zeile je Abfrage: Name: Frage an den Benutzer\nName: Wie heißt du";
  const prompt = document.createElement("textarea");
  prompt.id = "script-prompt";
  prompt.placeholder = "Freier Prompt. Leer lassen, wenn die Felder oben gelten.\nSprache: python\nName: Gruss\nFrage: Name: Wie heißt du\nBegrüße die Person";
  const modelLabel = document.createElement("label");
  modelLabel.className = "inline";
  const model = document.createElement("input");
  model.id = "script-model";
  model.type = "checkbox";
  modelLabel.append(model, document.createTextNode(" Prompt an das verbundene Sprachmodell senden"));
  const hint = document.createElement("div");
  hint.className = "hint";
  hint.textContent = "Ohne Modell entsteht das Skript aus diesen Feldern. Mit Modell braucht es eine Verbindung unter KI. Bei CSV und Text speichern ist die erste Abfrage die Datei.";
  labeled(body, "Sprache", lang);
  labeled(body, "Name", name);
  labeled(body, "Aktion", action);
  labeled(body, "Aufgabe", purpose);
  labeled(body, "Abfragen", questions);
  labeled(body, "Prompt", prompt);
  body.appendChild(modelLabel);
  body.appendChild(hint);
  modal("Skript erzeugen", body, [
    { label: "Abbrechen", run: () => {} },
    { label: "Erzeugen", run: () => {
      api("/api/studio", {
        action: "script",
        language: lang.value,
        name: name.value,
        action_name: action.value,
        purpose: purpose.value,
        questions: questions.value,
        prompt: prompt.value,
        use_model: model.checked,
      }).then(async (data) => {
        await openGenerated(data.path, data.content);
        $("modal").classList.add("hidden");
        toast(data.message);
      }).catch((err) => toast(err.message));
      return false;
    } },
  ]);
}

function openDatabaseCreator() {
  const body = document.createElement("div");
  const engine = document.createElement("select");
  engine.id = "db-engine";
  [["sqlite", "SQLite"], ["postgresql", "PostgreSQL"], ["mysql", "MySQL"], ["mongodb", "MongoDB"]].forEach(([value, label]) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    engine.appendChild(option);
  });
  const name = document.createElement("input");
  name.id = "db-name";
  name.value = "Lager";
  const path = document.createElement("input");
  path.id = "db-path";
  path.placeholder = "leer = datenbanken/Name.sqlite";
  const schema = document.createElement("textarea");
  schema.id = "db-schema";
  schema.style.height = "140px";
  schema.value = "person\n  id int pk\n  name text pflicht\n  email text unique\n";
  const dsn = document.createElement("input");
  dsn.id = "db-dsn";
  dsn.placeholder = "DSN oder mongodb://host, nur zum Anlegen auf dem Server";
  const applyLabel = document.createElement("label");
  applyLabel.className = "inline";
  const apply = document.createElement("input");
  apply.id = "db-apply";
  apply.type = "checkbox";
  applyLabel.append(apply, document.createTextNode(" Auf dem Server anlegen (PostgreSQL, MySQL, MongoDB)"));
  const hint = document.createElement("div");
  hint.className = "hint";
  hint.textContent = "SQLite wird als Datei angelegt. Andere Engines bekommen SQL oder ein Schema. Spalte: Name Typ pk pflicht unique.";
  labeled(body, "Engine", engine);
  labeled(body, "Name", name);
  labeled(body, "Datei", path);
  labeled(body, "Tabellen", schema);
  labeled(body, "Verbindung", dsn);
  body.appendChild(applyLabel);
  body.appendChild(hint);
  modal("Datenbank erzeugen", body, [
    { label: "Abbrechen", run: () => {} },
    { label: "Anlegen", run: () => {
      api("/api/studio", {
        action: "database",
        engine: engine.value,
        name: name.value,
        path: path.value,
        schema: schema.value,
        dsn: dsn.value,
        apply: apply.checked,
      }).then(async (data) => {
        if (data.database) S.dbPath = data.database;
        if (data.sample) S.dbSql = data.sample;
        await refreshTree();
        if (data.path) await openPath(data.path);
        $("modal").classList.add("hidden");
        toast(data.message);
      }).catch((err) => toast(err.message));
      return false;
    } },
  ]);
}

function openKit() {
  apiGet("/api/studio?action=kit").then((data) => {
    const modules = data.modules || [];
    const byId = Object.fromEntries(modules.map((item) => [item.id, item]));
    const blocks = [];
    const body = document.createElement("div");
    const name = document.createElement("input");
    name.id = "kit-name";
    name.value = "Baukasten";
    const lang = document.createElement("select");
    lang.id = "kit-lang";
    [["python", "Python"], ["powershell", "PowerShell"], ["shell", "Bash"], ["batch", "Batch"]].forEach(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      lang.appendChild(option);
    });
    const saved = document.createElement("select");
    saved.id = "kit-saved";
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "Gespeicherter Kasten";
    saved.appendChild(empty);
    (data.kits || []).forEach((item) => {
      const option = document.createElement("option");
      option.value = item.name;
      option.textContent = item.name;
      saved.appendChild(option);
    });
    const kit = document.createElement("div");
    kit.className = "kit";
    const palette = document.createElement("div");
    palette.id = "kit-modules";
    palette.className = "kit-modules";
    const stack = document.createElement("div");
    stack.id = "kit-stack";
    stack.className = "kit-stack";
    function blank(module) {
      const block = { id: module.id };
      module.fields.forEach((field) => { block[field.name] = field.default || ""; });
      return block;
    }
    function draw() {
      stack.textContent = "";
      if (!blocks.length) {
        const hint = document.createElement("div");
        hint.className = "hint";
        hint.textContent = "Module links anklicken. Sie laufen von oben nach unten. {Variable} setzt einen früheren Wert ein.";
        stack.appendChild(hint);
      }
      blocks.forEach((block, index) => {
        const module = byId[block.id];
        const card = document.createElement("div");
        card.className = "kit-card";
        const heading = document.createElement("h3");
        heading.textContent = (index + 1) + ". " + (module ? module.title : block.id);
        card.appendChild(heading);
        (module ? module.fields : []).forEach((field) => {
          let input;
          if (field.kind === "choice") {
            input = document.createElement("select");
            (field.choices || []).forEach((choice) => {
              const option = document.createElement("option");
              option.value = choice;
              option.textContent = choice;
              input.appendChild(option);
            });
          } else {
            input = document.createElement("input");
          }
          input.value = block[field.name] || "";
          input.oninput = () => { block[field.name] = input.value; };
          labeled(card, field.label, input);
        });
        const row = document.createElement("div");
        row.className = "row";
        [["Hoch", -1], ["Runter", 1]].forEach(([label, step]) => {
          const button = document.createElement("button");
          button.type = "button";
          button.textContent = label;
          button.onclick = () => {
            const next = index + step;
            if (next < 0 || next >= blocks.length) return;
            const moved = blocks[index];
            blocks[index] = blocks[next];
            blocks[next] = moved;
            draw();
          };
          row.appendChild(button);
        });
        const remove = document.createElement("button");
        remove.type = "button";
        remove.textContent = "Entfernen";
        remove.onclick = () => { blocks.splice(index, 1); draw(); };
        row.appendChild(remove);
        card.appendChild(row);
        stack.appendChild(card);
      });
    }
    modules.forEach((module) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = module.title;
      button.title = module.text;
      button.onclick = () => { blocks.push(blank(module)); draw(); };
      palette.appendChild(button);
    });
    saved.onchange = () => {
      if (!saved.value) return;
      api("/api/studio", { action: "kit", op: "load", name: saved.value }).then((loaded) => {
        name.value = loaded.name;
        if ([...lang.options].some((option) => option.value === loaded.language)) lang.value = loaded.language;
        blocks.splice(0, blocks.length, ...(loaded.blocks || []));
        draw();
      }).catch((err) => toast(err.message));
    };
    labeled(body, "Name", name);
    labeled(body, "Sprache", lang);
    labeled(body, "Gespeichert", saved);
    kit.append(palette, stack);
    body.appendChild(kit);
    const hint = document.createElement("div");
    hint.className = "hint";
    hint.textContent = "Der Kasten wird unter baukasten/ gespeichert. Das Skript landet in ausgabe/. Batch kennt nur Eingabe, Ausgabe, Rechnen, Text, Datei schreiben, Ordner, Bedingung und Pause.";
    body.appendChild(hint);
    modal("Baukasten", body, [
      { label: "Abbrechen", run: () => {} },
      { label: "Merken", run: () => {
        api("/api/studio", { action: "kit", op: "save", name: name.value, language: lang.value, blocks })
          .then((savedKit) => { toast("Baukasten " + savedKit.name + " gemerkt"); })
          .catch((err) => toast(err.message));
        return false;
      } },
      { label: "Erzeugen", run: () => {
        api("/api/studio", { action: "kit", op: "build", name: name.value, language: lang.value, blocks })
          .then(async (built) => {
            await openGenerated(built.path, built.content);
            $("modal").classList.add("hidden");
            toast(built.message);
          })
          .catch((err) => toast(err.message));
        return false;
      } },
    ]);
    const box = $("modal").querySelector(".box");
    if (box) box.classList.add("wide");
    draw();
  }).catch((err) => toast(err.message));
}

function renderStudio(host) {
  const row = document.createElement("div");
  row.className = "row";
  const actions = [
    ["Skript", openScriptCreator],
    ["Baukasten", openKit],
    ["Datenbank", openDatabaseCreator],
    ["EXE", buildExe],
    ["MSI", buildMsi],
    ["Modul", buildModule],
    ["Funktion", buildFunction],
    ["GUI", openGuiDesigner],
    ["Dienst", buildService],
    ["Messen", measureFile],
    ["Wiederherstellen", restoreRecovery],
  ];
  actions.forEach(([label, fn]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.onclick = () => Promise.resolve(fn()).catch((err) => toast(err.message));
    row.appendChild(button);
  });
  const topic = document.createElement("input");
  topic.placeholder = "Get-Help Thema, z. B. Get-Date";
  topic.value = "Get-Command";
  const help = document.createElement("button");
  help.type = "button";
  help.textContent = "PS-Hilfe";
  const out = document.createElement("div");
  help.onclick = async () => {
    const data = await apiGet("/api/studio?action=help&topic=" + encodeURIComponent(topic.value));
    out.textContent = data.text || "";
  };
  host.appendChild(row);
  host.appendChild(topic);
  host.appendChild(help);
  host.appendChild(out);
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
      ["Wiederherstellen…", restoreRecovery],
    ]],
    ["Bearbeiten", [
      ["Rückgängig", () => editorHistory(false), "Strg+Z"],
      ["Wiederholen", () => editorHistory(true), "Strg+Y"],
      ["Ausschneiden", cutSelection, "Strg+X"],
      ["Kopieren", () => copySelection(false), "Strg+C"],
      ["Bereich kopieren…", copyRange],
      ["Einfügen", pasteClip, "Strg+V"],
      ["Suchen…", () => openFind(false), "Strg+F"],
      ["Ersetzen…", () => openFind(true), "Strg+H"],
      ["Zeile kommentieren", toggleComment, "Strg+/"],
      ["Zeile duplizieren", () => duplicateLines(1), "Umschalt+Alt+↓"],
      ["Zeile nach oben", () => moveLines(-1), "Alt+↑"],
      ["Zeile nach unten", () => moveLines(1), "Alt+↓"],
      ["Zeile löschen", deleteLines, "Strg+Umschalt+K"],
      ["Zeilen verbinden", joinLines, "Strg+Umschalt+J"],
      ["Groß-/Kleinschreibung", toggleCase, "Strg+Umschalt+U"],
      ["Nächstes Vorkommen", selectNextOccurrence, "Strg+D"],
      ["Zeilenumbruch", toggleWrap, "Alt+Z"],
      ["Formatieren", formatCurrent, "Umschalt+Alt+F"],
      ["Snippet einfügen", pickSnippet],
      ["Falten", () => foldAt(cursorPos().line)],
      ["Alles aufklappen", () => { unfoldAll(); renderEditor(); }],
    ]],
    ["Navigieren", [
      ["Gehe zu Definition", gotoDef, "F12"],
      ["Gehe zu Zeile…", goToLine, "Strg+G"],
      ["Suche überall", () => setBottom("search"), "Strg+Umschalt+F"],
      ["In Dateien ersetzen…", openProjectReplace, "Strg+Umschalt+H"],
      ["Gliederung", () => showSide("outline")],
      ["TODO", () => setBottom("todo")],
      ["Lesezeichen", addBookmark],
    ]],
    ["Ausführen", [
      ["Datei ausführen", () => runFile(false), "Strg+F5"],
      ["Auswahl ausführen", runSelection],
      ["Markierung im Fenster", () => probeWindow("mark"), "Alt+F5"],
      ["Funktion im Fenster", () => probeWindow("function"), "Umschalt+Alt+F5"],
      ["Syntax prüfen", checkSyntax],
      ["Bytecode kompilieren", () => compileCurrent("file")],
      ["Projekt kompilieren", () => compileCurrent("project")],
      ["PyInstaller", pyInstaller],
      ["EXE erzeugen", buildExe],
      ["MSI-Installer…", buildMsi],
      ["Leistung messen", measureFile],
      ["Framework starten", runFramework],
    ]],
    ["Erzeugen", [
      ["Skript aus Abfrage…", openScriptCreator],
      ["Baukasten…", openKit],
      ["Datenbank erzeugen…", openDatabaseCreator],
      ["EXE erzeugen", buildExe],
      ["MSI-Installer…", buildMsi],
      ["Modul aus Funktionen…", buildModule],
      ["Funktion erzeugen…", buildFunction],
      ["GUI entwerfen…", openGuiDesigner],
      ["Windows-Dienst…", buildService],
      ["Leistung messen", measureFile],
    ]],
    ["Debuggen", [
      ["Start / Weiter", () => S.debugLine ? debugCmd("continue") : runFile(true), "F5"],
      ["Schritt über", () => debugCmd("step"), "F10"],
      ["Schritt hinein", () => debugCmd("step_into"), "F11"],
      ["Schritt hinaus", () => debugCmd("step_out")],
      ["Haltepunkt", () => toggleBreak(cursorPos().line), "F9"],
      ["Bedingung…", conditionBreak],
      ["Stopp", stopAll],
      ["Remote-Ablauf", () => setBottom("remote")],
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
      ["Testfenster", () => probeWindow("mark")],
      ["Fenster schließen", closeWindow],
    ]],
    ["Hilfe", [
      ["PS-Hilfe", () => setBottom("studio")],
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

function closeWindow() {
  const child = !!window.opener;
  if (child) {
    window.open("", "_self");
    window.close();
    return;
  }
  toast("Das Hauptfenster schließt der Browser über seinen eigenen Rahmen");
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
  filter.placeholder = "Name filtern, zum Beispiel .py, .html, .json oder .sh";
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

function selectionLines() {
  const area = codeEl();
  const text = area.value;
  const start = area.selectionStart;
  const end = area.selectionEnd;
  const startLine = text.slice(0, start).split("\n").length;
  let endLine = text.slice(0, Math.max(start, end)).split("\n").length;
  if (end > start && text[end - 1] === "\n") endLine -= 1;
  return { startLine, endLine, selected: text.slice(start, end) };
}

async function probeWindow(scope) {
  const current = tab();
  if (!current) return toast("Keine Datei");
  const lines = selectionLines();
  const data = await api("/api/probe", {
    content: current.content,
    path: current.path,
    start: scope === "function" ? cursorPos().line : lines.startLine,
    end: lines.endLine,
    selected: scope === "function" ? "" : lines.selected,
    scope,
  });
  const opened = window.open("/probe", "shatu-probe-" + Date.now(), "popup=yes,width=920,height=720,left=100,top=40");
  if (!opened) return toast("Testfenster wurde blockiert");
  const message = { type: "shatu-probe", ...data };
  const send = (event) => {
    if (event.source !== opened || !event.data || event.data.type !== "shatu-probe-ready") return;
    opened.postMessage(message, location.origin);
  };
  window.addEventListener("message", send);
  const timer = setInterval(() => {
    if (opened.closed) {
      clearInterval(timer);
      window.removeEventListener("message", send);
      return;
    }
    opened.postMessage(message, location.origin);
  }, 250);
  setTimeout(() => {
    clearInterval(timer);
    window.removeEventListener("message", send);
  }, 4000);
}

async function runSelection() {
  const text = selectedText();
  const current = tab();
  if (!text) return toast("Nichts markiert");
  const data = await api("/api/run", { mode: "selection", content: text, path: current ? current.path : "" });
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
  body.textContent = "Strg+S Speichern\nStrg+W Datei schließen\nEscape Dialog schließen\nStrg+Z Rückgängig\nStrg+Y Wiederholen\nStrg+X Ausschneiden\nStrg+C Kopieren\nStrg+V Einfügen\nStrg+F Suchen\nStrg+H Ersetzen\nStrg+/ Zeile kommentieren\nStrg+D Nächstes Vorkommen\nAlt+↑/↓ Zeile verschieben\nUmschalt+Alt+↓ Zeile duplizieren\nStrg+Umschalt+K Zeile löschen\nStrg+G Gehe zu Zeile\nStrg+F5 Ausführen\nAlt+F5 Markierung im Fenster\nUmschalt+Alt+F5 Funktion im Fenster\nF5 Debug/Weiter\nF9 Haltepunkt\nF10 Schritt über\nF11 Schritt hinein\nF12 Definition\nStrg+K Inline-KI\nStrg+Eingabe Prompt senden\nStrg+Leertaste Vervollständigen\nStrg+Umschalt+F Suche\nStrg+Umschalt+H In Dateien ersetzen\nStudio Baukasten, Skript, Datenbank, EXE, MSI, Modul, GUI, Dienst, Messen, PS-Hilfe";
  modal("Tastatur", body, [{ label: "Schließen", run: () => {} }]);
}

function about() {
  const body = document.createElement("div");
  body.innerHTML = "<p><b>ShatuIDE</b> 1.0</p><p>Andreas Meyer<br>ame@sellerbach.de</p><p>Lokale Python-IDE. Workspace mit vollem Dateizugriff, Standard unter Windows: D:\\AI_Temp\\ShatuIDE. shatuide.jpg, icon.png oder die Mitte einer Grafik wird automatisch verwendet.</p>";
  modal("Über", body, [{ label: "Schließen", run: () => {} }]);
}

function showSide(name) {
  setPane("left", true);
  S.side = name;
  $("tree").classList.toggle("hidden", name !== "tree");
  $("outline").classList.toggle("hidden", name !== "outline");
  document.querySelectorAll("[data-side]").forEach((button) => button.classList.toggle("on", button.dataset.side === name));
}

function toggleSide(name) {
  if (paneOpen("left") && S.side === name) setPane("left", false);
  else showSide(name);
}

function onKey(event) {
  const key = event.key.toLowerCase();
  if (event.ctrlKey && key === "s") { event.preventDefault(); saveTab().catch((err) => toast(err.message)); }
  else if (event.ctrlKey && key === "f5") { event.preventDefault(); runFile(false); }
  else if (event.altKey && event.key === "F5") { event.preventDefault(); probeWindow(event.shiftKey ? "function" : "mark").catch((err) => toast(err.message)); }
  else if (event.key === "F5") { event.preventDefault(); S.debugLine ? debugCmd("continue") : runFile(true); }
  else if (event.key === "F9") { event.preventDefault(); toggleBreak(cursorPos().line); }
  else if (event.key === "F10") { event.preventDefault(); debugCmd("step"); }
  else if (event.key === "F11") { event.preventDefault(); debugCmd("step_into"); }
  else if (event.key === "F12") { event.preventDefault(); gotoDef(); }
  else if (event.ctrlKey && key === "k" && !event.shiftKey) { event.preventDefault(); inlineEdit(); }
  else if (event.ctrlKey && event.code === "Space") { event.preventDefault(); completeAt(); }
  else if (S.complete.length && event.key === "ArrowDown") { event.preventDefault(); moveComplete(1); }
  else if (S.complete.length && event.key === "ArrowUp") { event.preventDefault(); moveComplete(-1); }
  else if (S.complete.length && (event.key === "Enter" || event.key === "Tab")) { event.preventDefault(); acceptComplete(S.completeIndex); }
  else if (event.key === "Tab") { event.preventDefault(); event.shiftKey ? shiftLines(true) : indentOrTab(); }
  else if (event.ctrlKey && !event.altKey && key === "f") { event.preventDefault(); openFind(false); }
  else if (event.ctrlKey && !event.altKey && key === "h") { event.preventDefault(); openFind(true); }
  else if (event.key === "F3") { event.preventDefault(); findNext(event.shiftKey ? -1 : 1); }
  else if (event.ctrlKey && (key === "/" || key === "#" || event.code === "Slash")) { event.preventDefault(); toggleComment(); }
  else if (event.ctrlKey && !event.shiftKey && key === "d") { event.preventDefault(); selectNextOccurrence(); }
  else if (event.ctrlKey && !event.shiftKey && key === "g") { event.preventDefault(); goToLine(); }
  else if (event.ctrlKey && event.shiftKey && key === "k") { event.preventDefault(); deleteLines(); }
  else if (event.ctrlKey && event.shiftKey && key === "j") { event.preventDefault(); joinLines(); }
  else if (event.ctrlKey && event.shiftKey && key === "u") { event.preventDefault(); toggleCase(); }
  else if (event.ctrlKey && event.shiftKey && key === "f") { event.preventDefault(); setBottom("search"); }
  else if (event.ctrlKey && event.shiftKey && key === "h") { event.preventDefault(); openProjectReplace(); }
  else if (event.altKey && event.shiftKey && event.key === "ArrowDown") { event.preventDefault(); duplicateLines(1); }
  else if (event.altKey && event.shiftKey && event.key === "ArrowUp") { event.preventDefault(); duplicateLines(-1); }
  else if (event.altKey && !event.shiftKey && !event.ctrlKey && event.key === "ArrowUp") { event.preventDefault(); moveLines(-1); }
  else if (event.altKey && !event.shiftKey && !event.ctrlKey && event.key === "ArrowDown") { event.preventDefault(); moveLines(1); }
  else if (event.altKey && !event.ctrlKey && key === "z") { event.preventDefault(); toggleWrap(); }
  else if (event.ctrlKey && !event.shiftKey && key === "z") { event.preventDefault(); editorHistory(false); }
  else if ((event.ctrlKey && key === "y") || (event.ctrlKey && event.shiftKey && key === "z")) { event.preventDefault(); editorHistory(true); }
  else if (event.key === "Escape") {
    if (!$("modal").classList.contains("hidden")) closeModal();
    else hidePopup();
  }
  else if (event.ctrlKey && !event.shiftKey && key === "w") { event.preventDefault(); closeTab(S.active); }
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
  document.querySelectorAll("#ribbon-tabs [data-ribbon]").forEach((button) => {
    button.onclick = () => showRibbon(button.dataset.ribbon);
  });
  document.querySelectorAll("[data-dock]").forEach((button) => {
    button.onclick = () => showDock(button.dataset.dock);
  });
  const bindClick = (id, fn) => {
    const node = $(id);
    if (node) node.onclick = () => Promise.resolve(fn()).catch((err) => toast(err.message));
  };
  bindFindbar();
  bindClick("btn-cut", cutSelection);
  bindClick("btn-copy", () => copySelection(false));
  bindClick("btn-paste", pasteClip);
  bindClick("btn-open", () => openFileDialog());
  bindClick("btn-save", saveTab);
  $("btn-run").onclick = () => runFile(false);
  $("btn-debug").onclick = () => runFile(true);
  $("btn-stop").onclick = () => stopAll();
  bindClick("btn-step-into", () => debugCmd("step_into"));
  bindClick("btn-step", () => debugCmd("step"));
  bindClick("btn-step-out", () => debugCmd("step_out"));
  bindClick("btn-break", () => toggleBreak(cursorPos().line));
  $("btn-format").onclick = () => formatCurrent();
  bindClick("btn-function", buildFunction);
  bindClick("btn-function-design", buildFunction);
  bindClick("btn-fold", () => foldAt(cursorPos().line));
  bindClick("btn-unfold", () => { unfoldAll(); renderEditor(); });
  bindClick("btn-goto", goToLine);
  bindClick("btn-kit", openKit);
  bindClick("btn-gui", openGuiDesigner);
  bindClick("btn-module", buildModule);
  bindClick("btn-script", openScriptCreator);
  bindClick("btn-database", openDatabaseCreator);
  bindClick("btn-exe", buildExe);
  bindClick("btn-msi", buildMsi);
  bindClick("btn-service", buildService);
  bindClick("btn-measure", measureFile);
  bindClick("btn-view-tree", () => toggleSide("tree"));
  bindClick("btn-view-outline", () => toggleSide("outline"));
  bindClick("btn-view-output", () => toggleBottom("output"));
  bindClick("btn-view-terminal", () => toggleBottom("terminal"));
  bindClick("btn-view-ai", () => toggleDock("ai"));
  bindClick("btn-close-window", closeWindow);
  bindClick("close-left", () => setPane("left", false));
  bindClick("close-right", () => setPane("right", false));
  bindClick("close-bottom", () => setPane("bottom", false));
  if ($("fn-filter")) $("fn-filter").addEventListener("input", () => renderFunctions());
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
    highlightEl().innerHTML = highlightSource(current.content, errorLineSet(), languageOf(current.path)) + "\n";
    renderGutter();
    renderTabs();
    renderFunctions();
    scheduleAnalyze();
    scheduleRecovery();
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
    if (event.key === "Escape" && !$("modal").classList.contains("hidden")) {
      event.preventDefault();
      closeModal();
      return;
    }
    if (event.target === area) return;
    if (event.ctrlKey && event.key.toLowerCase() === "s") { event.preventDefault(); saveTab(); }
    if (event.ctrlKey && !event.shiftKey && event.key.toLowerCase() === "w") { event.preventDefault(); closeTab(S.active); }
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
  apiGet("/api/studio?action=recovery").then((data) => {
    if (data.items && data.items.length) toast(data.items.length + " Wiederherstellungen unter Datei");
  }).catch(() => {});
  const welcome = state.workspace.replace(/[/\\]$/, "") + "/beispiele/hallo.py";
  openPath(welcome).catch(() => {});
  updateStatus("Bereit");
}

boot().catch((err) => toast(err.message));
