import { colName } from '../model/addr';

export interface ScriptApi {
  get(addr: string): string;
  set(addr: string, value: string): void;
  formula(addr: string): string;
  value(addr: string): string;
  style(addr: string, patch: Record<string, unknown>): void;
  sheet(name?: string): string;
  sheets(): string[];
  log(msg: string): void;
}

type PyVal = number | string | boolean | null;

export function runJavaScript(code: string, api: ScriptApi): string {
  const logs: string[] = [];
  const rg = {
    get: (addr: string) => api.get(addr),
    set: (addr: string, value: unknown) => api.set(addr, value == null ? '' : String(value)),
    formula: (addr: string) => api.formula(addr),
    value: (addr: string) => api.value(addr),
    style: (addr: string, patch: Record<string, unknown>) => api.style(addr, patch),
    sheet: (name?: string) => api.sheet(name),
    sheets: () => api.sheets(),
    log: (msg: unknown) => {
      const line = String(msg);
      logs.push(line);
      api.log(line);
    },
  };
  const fn = new Function('rg', `'use strict';\n${code}`);
  fn(rg);
  return logs.join('\n');
}

export function runPython(code: string, api: ScriptApi): string {
  const lines = code.replace(/\t/g, '    ').split(/\r?\n/);
  const env = new Map<string, PyVal>();
  const logs: string[] = [];
  const evalAt = (expr: string): PyVal => evalPy(expr, env, api, logs);
  const exec = (from: number, to: number, indent: number): number => {
    let i = from;
    while (i < to) {
      const rawLine = lines[i] ?? '';
      if (rawLine.trim() === '' || rawLine.trim().startsWith('#')) {
        i++;
        continue;
      }
      const ind = rawLine.match(/^ */)?.[0].length ?? 0;
      if (ind < indent) return i;
      if (ind !== indent) throw new Error(`Einrückung in Zeile ${i + 1}`);
      const line = rawLine.trim();
      const forMatch = /^for\s+([A-Za-z_]\w*)\s+in\s+range\((.*)\)\s*:$/.exec(line);
      if (forMatch) {
        const args = splitArgs(forMatch[2]).map((part) => asNum(evalAt(part)));
        let start = 0;
        let end = 0;
        let step = 1;
        if (args.length === 1) end = args[0];
        else if (args.length >= 2) {
          start = args[0];
          end = args[1];
          step = args[2] || 1;
        }
        let j = i + 1;
        while (j < to) {
          const probe = lines[j] ?? '';
          if (probe.trim() === '') {
            j++;
            continue;
          }
          const pid = probe.match(/^ */)?.[0].length ?? 0;
          if (pid <= indent) break;
          j++;
        }
        if (step === 0) throw new Error('range-Schritt 0');
        for (let n = start; step > 0 ? n < end : n > end; n += step) {
          env.set(forMatch[1], n);
          exec(i + 1, j, indent + 4);
        }
        i = j;
        continue;
      }
      if (line.startsWith('print(') && line.endsWith(')')) {
        const shown = splitArgs(line.slice(6, -1)).map((part) => showPy(evalAt(part)));
        const msg = shown.join(' ');
        logs.push(msg);
        api.log(msg);
        i++;
        continue;
      }
      const assign = /^([A-Za-z_]\w*)\s*=\s*(.+)$/.exec(line);
      if (assign && !assign[1].includes('(')) {
        env.set(assign[1], evalAt(assign[2]));
        i++;
        continue;
      }
      evalAt(line);
      i++;
    }
    return i;
  };
  exec(0, lines.length, 0);
  return logs.join('\n');
}

export function runVba(code: string, api: ScriptApi): string {
  const lines = code.split(/\r?\n/).map((line) => line.trim()).filter((line) => line && !line.startsWith("'"));
  const env = new Map<string, number>();
  const logs: string[] = [];
  const evalV = (expr: string): string => String(evalVba(expr.trim(), env, api));
  const exec = (from: number, to: number): number => {
    let i = from;
    while (i < to) {
      const line = lines[i];
      const forMatch = /^For\s+([A-Za-z_]\w*)\s*=\s*(.+?)\s+To\s+(.+?)(?:\s+Step\s+(.+))?$/i.exec(line);
      if (forMatch) {
        let j = i + 1;
        let depth = 1;
        while (j < to) {
          if (/^For\s+/i.test(lines[j])) depth++;
          if (/^Next\b/i.test(lines[j])) {
            depth--;
            if (depth === 0) break;
          }
          j++;
        }
        const start = asNum(evalVba(forMatch[2], env, api));
        const end = asNum(evalVba(forMatch[3], env, api));
        const step = forMatch[4] ? asNum(evalVba(forMatch[4], env, api)) : start <= end ? 1 : -1;
        for (let n = start; step > 0 ? n <= end : n >= end; n += step) {
          env.set(forMatch[1].toLowerCase(), n);
          exec(i + 1, j);
        }
        i = j + 1;
        continue;
      }
      const msg = /^MsgBox\s+(.+)$/i.exec(line);
      if (msg) {
        const text = evalV(msg[1]);
        logs.push(text);
        api.log(text);
        i++;
        continue;
      }
      const setRange = /^Range\(\s*(.+?)\s*\)\.Value\s*=\s*(.+)$/i.exec(line);
      if (setRange) {
        api.set(unquote(evalV(setRange[1])), evalV(setRange[2]));
        i++;
        continue;
      }
      const setCells = /^Cells\(\s*(.+?)\s*,\s*(.+?)\s*\)\.Value\s*=\s*(.+)$/i.exec(line);
      if (setCells) {
        const r = asNum(evalVba(setCells[1], env, api));
        const c = asNum(evalVba(setCells[2], env, api));
        api.set(cellAddr(r - 1, c - 1), evalV(setCells[3]));
        i++;
        continue;
      }
      i++;
    }
    return i;
  };
  exec(0, lines.length);
  return logs.join('\n');
}

function evalPy(expr: string, env: Map<string, PyVal>, api: ScriptApi, logs: string[]): PyVal {
  const src = expr.trim();
  if (!src) return null;
  let i = 0;
  const peek = () => src[i] ?? '';
  const eat = (s: string) => {
    if (src.slice(i, i + s.length) !== s) throw new Error(`Erwartet ${s} in „${src}“`);
    i += s.length;
  };
  const parseOr = (): PyVal => {
    let left = parseAnd();
    while (src.slice(i).trimStart().startsWith('or ')) {
      i += src.slice(i).length - src.slice(i).trimStart().length;
      eat('or');
      const right = parseAnd();
      left = Boolean(left) || Boolean(right);
    }
    return left;
  };
  const parseAnd = (): PyVal => {
    let left = parseCmp();
    while (true) {
      const rest = src.slice(i).trimStart();
      if (!rest.startsWith('and ')) break;
      i += src.slice(i).length - src.slice(i).trimStart().length;
      eat('and');
      const right = parseCmp();
      left = Boolean(left) && Boolean(right);
    }
    return left;
  };
  const parseCmp = (): PyVal => {
    let left = parseAdd();
    const ops = ['==', '!=', '<=', '>=', '<', '>'] as const;
    while (true) {
      skip();
      const op = ops.find((item) => src.startsWith(item, i));
      if (!op) break;
      i += op.length;
      const right = parseAdd();
      left = comparePy(left, right, op);
    }
    return left;
  };
  const parseAdd = (): PyVal => {
    let left = parseMul();
    while (true) {
      skip();
      if (peek() !== '+' && peek() !== '-') break;
      const op = peek();
      i++;
      const right = parseMul();
      if (op === '+') {
        if (typeof left === 'string' || typeof right === 'string') left = showPy(left) + showPy(right);
        else left = asNum(left) + asNum(right);
      } else left = asNum(left) - asNum(right);
    }
    return left;
  };
  const parseMul = (): PyVal => {
    let left = parsePow();
    while (true) {
      skip();
      if (src.startsWith('//', i)) {
        i += 2;
        const right = parsePow();
        left = Math.trunc(asNum(left) / asNum(right));
        continue;
      }
      if (peek() !== '*' && peek() !== '/' && peek() !== '%') break;
      const op = peek();
      i++;
      const right = parsePow();
      if (op === '*') left = asNum(left) * asNum(right);
      else if (op === '/') left = asNum(left) / asNum(right);
      else left = asNum(left) % asNum(right);
    }
    return left;
  };
  const parsePow = (): PyVal => {
    const left = parseUnary();
    skip();
    if (!src.startsWith('**', i)) return left;
    i += 2;
    return asNum(left) ** asNum(parsePow());
  };
  const parseUnary = (): PyVal => {
    skip();
    if (src.startsWith('not ', i)) {
      i += 4;
      return !evalPy(src.slice(i), env, api, logs);
    }
    if (peek() === '-') {
      i++;
      return -asNum(parseUnary());
    }
    if (peek() === '+') {
      i++;
      return asNum(parseUnary());
    }
    return parseAtom();
  };
  const parseAtom = (): PyVal => {
    skip();
    if (peek() === '(') {
      i++;
      const innerStart = i;
      let depth = 1;
      while (i < src.length && depth) {
        if (src[i] === '(') depth++;
        else if (src[i] === ')') depth--;
        if (depth) i++;
      }
      const inner = src.slice(innerStart, i);
      i++;
      return evalPy(inner, env, api, logs);
    }
    if (peek() === '"' || peek() === "'") {
      const q = peek();
      i++;
      let s = '';
      while (i < src.length && src[i] !== q) {
        s += src[i];
        i++;
      }
      i++;
      return s;
    }
    const num = /^(\d+(?:[.,]\d+)?)/.exec(src.slice(i));
    if (num) {
      i += num[1].length;
      return Number(num[1].replace(',', '.'));
    }
    const ident = /^[A-Za-z_]\w*/.exec(src.slice(i));
    if (ident) {
      i += ident[0].length;
      skip();
      if (peek() === '(') {
        i++;
        const args: string[] = [];
        let cur = '';
        let depth = 1;
        let quote: string | null = null;
        while (i < src.length && depth) {
          const ch = src[i];
          if (quote) {
            cur += ch;
            if (ch === quote) quote = null;
          } else if (ch === '"' || ch === "'") {
            quote = ch;
            cur += ch;
          } else if (ch === '(') {
            depth++;
            cur += ch;
          } else if (ch === ')') {
            depth--;
            if (depth) cur += ch;
          } else if (ch === ',' && depth === 1) {
            args.push(cur);
            cur = '';
          } else cur += ch;
          i++;
        }
        if (cur.trim()) args.push(cur);
        return callPy(ident[0], args.map((a) => evalPy(a, env, api, logs)), api, logs);
      }
      const name = ident[0];
      if (name === 'True') return true;
      if (name === 'False') return false;
      if (name === 'None') return null;
      if (!env.has(name)) throw new Error(`Unbekannter Name ${name}`);
      return env.get(name) ?? null;
    }
    throw new Error(`Python-Ausdruck nicht lesbar: ${src.slice(i)}`);
  };
  const skip = () => {
    while (src[i] === ' ') i++;
  };
  const value = parseOr();
  return value;
}

function callPy(name: string, args: PyVal[], api: ScriptApi, logs: string[]): PyVal {
  const fn = name.toLowerCase();
  if (fn === 'set') {
    api.set(String(args[0] ?? ''), args[1] == null ? '' : String(args[1]));
    return args[1] ?? null;
  }
  if (fn === 'get' || fn === 'cell') {
    const shown = api.value(String(args[0] ?? ''));
    const n = Number(String(shown).replace(/\./g, '').replace(',', '.'));
    if (shown && Number.isFinite(n) && /^-?\d/.test(shown)) return n;
    return api.get(String(args[0] ?? ''));
  }
  if (fn === 'print') {
    const msg = args.map(showPy).join(' ');
    logs.push(msg);
    api.log(msg);
    return null;
  }
  if (fn === 'int') return Math.trunc(asNum(args[0]));
  if (fn === 'str') return showPy(args[0]);
  if (fn === 'abs') return Math.abs(asNum(args[0]));
  if (fn === 'len') return String(args[0] ?? '').length;
  if (fn === 'round') return Number(asNum(args[0]).toFixed(asNum(args[1] ?? 0)));
  throw new Error(`Unbekannte Python-Funktion ${name}`);
}

function comparePy(left: PyVal, right: PyVal, op: '==' | '!=' | '<=' | '>=' | '<' | '>'): boolean {
  if (op === '==') return left === right;
  if (op === '!=') return left !== right;
  const a = typeof left === 'number' && typeof right === 'number' ? left : showPy(left);
  const b = typeof left === 'number' && typeof right === 'number' ? (right as number) : showPy(right);
  if (op === '<') return a < b;
  if (op === '>') return a > b;
  if (op === '<=') return a <= b;
  return a >= b;
}

function evalVba(expr: string, env: Map<string, number>, api: ScriptApi): string | number {
  const src = expr.trim();
  if (/^"[\s\S]*"$/.test(src)) return src.slice(1, -1).replace(/""/g, '"');
  const range = /^Range\(\s*(.+)\s*\)\.Value$/i.exec(src);
  if (range) return api.value(unquote(String(evalVba(range[1], env, api))));
  const cells = /^Cells\(\s*(.+?)\s*,\s*(.+?)\s*\)\.Value$/i.exec(src);
  if (cells) {
    const r = asNum(evalVba(cells[1], env, api));
    const c = asNum(evalVba(cells[2], env, api));
    return api.value(cellAddr(r - 1, c - 1));
  }
  if (/^[A-Za-z_]\w*$/.test(src) && env.has(src.toLowerCase())) return env.get(src.toLowerCase()) ?? 0;
  if (/^-?\d+(?:[.,]\d+)?$/.test(src)) return Number(src.replace(',', '.'));
  const math = /^(.+?)\s*([+\-*/])\s*(.+)$/.exec(src);
  if (math && !src.startsWith('"')) {
    const a = asNum(evalVba(math[1], env, api));
    const b = asNum(evalVba(math[3], env, api));
    if (math[2] === '+') return a + b;
    if (math[2] === '-') return a - b;
    if (math[2] === '*') return a * b;
    return b === 0 ? 0 : a / b;
  }
  return src;
}

function splitArgs(input: string): string[] {
  const args: string[] = [];
  let cur = '';
  let depth = 0;
  let quote: string | null = null;
  for (const ch of input) {
    if (quote) {
      cur += ch;
      if (ch === quote) quote = null;
    } else if (ch === '"' || ch === "'") {
      quote = ch;
      cur += ch;
    } else if (ch === '(') {
      depth++;
      cur += ch;
    } else if (ch === ')') {
      depth--;
      cur += ch;
    } else if (ch === ',' && depth === 0) {
      args.push(cur.trim());
      cur = '';
    } else cur += ch;
  }
  if (cur.trim()) args.push(cur.trim());
  return args;
}

function asNum(v: PyVal | string | number): number {
  if (typeof v === 'number') return v;
  if (typeof v === 'boolean') return v ? 1 : 0;
  const n = Number(String(v ?? '').replace(',', '.'));
  return Number.isFinite(n) ? n : 0;
}

function showPy(v: PyVal): string {
  if (v === null || v === undefined) return 'None';
  if (typeof v === 'boolean') return v ? 'True' : 'False';
  return String(v);
}

function unquote(value: string): string {
  const t = value.trim();
  if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) return t.slice(1, -1);
  return t;
}

function cellAddr(r: number, c: number): string {
  return `${colName(c)}${r + 1}`;
}
