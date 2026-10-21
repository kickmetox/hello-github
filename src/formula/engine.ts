import { tryParseFormula, type Expr } from './parser';
import {
  type Addr,
  type FnCtx,
  type NameInput,
  type TableInput,
  registry,
} from './functions';
import { parseLiteral, formatGeneral, parseNumberDe } from './format';
import {
  BEZUG,
  DIV0,
  FError,
  FEHLER,
  isErr,
  isLambda,
  isLink,
  isMatrix,
  isSpark,
  LambdaVal,
  NAME,
  WERT,
  ZAHL,
  matrix,
  type CellVal,
  type Matrix,
  type Scalar,
  type Value,
} from './value';

export interface CellInput {
  raw: string;
}

export interface SheetInput {
  name: string;
  rows: number;
  cols: number;
  cells: Record<string, CellInput>;
  hiddenRows?: number[];
}

export interface CalcInput {
  sheets: SheetInput[];
  names?: NameInput[];
  tables?: TableInput[];
}

export interface Computed {
  value: Scalar;
  error: string | null;
  spill?: boolean;
  spark?: { values: number[]; mode: 'line' | 'col' | 'winloss' };
  href?: string;
  label?: string;
  lambda?: boolean;
}

interface FormulaPos {
  r: number;
  c: number;
}

export function calculate(model: CalcInput): Map<string, Computed> {
  const sheets = new Map<string, SheetInput>();
  const canon = new Map<string, string>();
  for (const s of model.sheets) {
    sheets.set(s.name, s);
    canon.set(s.name.toLowerCase(), s.name);
  }
  const hidden = new Set<string>();
  for (const s of model.sheets) for (const r of s.hiddenRows ?? []) hidden.add(`${s.name}\n${r}`);
  const formulas = new Map<string, FormulaPos[]>();
  for (const s of model.sheets) {
    const list: FormulaPos[] = [];
    for (const [k, cell] of Object.entries(s.cells)) {
      if (cell?.raw?.startsWith('=')) {
        const [r, c] = k.split(',').map(Number);
        list.push({ r, c });
      }
    }
    formulas.set(s.name, list);
  }
  const cache = new Map<string, Value>();
  const spills = new Map<string, Value>();
  const spillFrom = new Set<string>();
  const anchors = new Map<string, Addr>();
  const visiting = new Set<string>();
  const resolving = new Set<string>();
  const locals = new Map<string, Value>();
  const localStack: { name: string; had: boolean; prev: Value | undefined }[] = [];
  let depth = 0;
  const ctx = {} as FnCtx;

  const resolveSheet = (name?: string, fallback?: string): string => {
    if (!name) return fallback ?? model.sheets[0]?.name ?? 'Tabelle1';
    return canon.get(name.toLowerCase()) ?? name;
  };

  const keyOf = (sheet: string, r: number, c: number) => `${resolveSheet(sheet)}\n${r},${c}`;

  const rawOf = (sheet: string, r: number, c: number): string => {
    const s = sheets.get(resolveSheet(sheet));
    if (!s) return '';
    return s.cells[`${r},${c}`]?.raw ?? '';
  };

  function setLocal(name: string, value: Value): void {
    const k = name.toUpperCase();
    localStack.push({ name: k, had: locals.has(k), prev: locals.get(k) });
    locals.set(k, value);
  }
  function restoreLocals(mark: number): void {
    while (localStack.length > mark) {
      const s = localStack.pop()!;
      if (s.had) locals.set(s.name, s.prev as Value);
      else locals.delete(s.name);
    }
  }

  function readRange(sheet: string, r1: number, c1: number, r2: number, c2: number): Matrix | FError {
    const sh = resolveSheet(sheet);
    if (!sheets.has(sh)) return BEZUG();
    const top = Math.min(r1, r2);
    const bot = Math.max(r1, r2);
    const left = Math.min(c1, c2);
    const right = Math.max(c1, c2);
    if (top < 0 || left < 0) return BEZUG();
    if ((bot - top + 1) * (right - left + 1) > 20000) return WERT();
    const values: CellVal[][] = [];
    for (let r = top; r <= bot; r++) {
      const row: CellVal[] = [];
      for (let c = left; c <= right; c++) row.push(asCell(evalCell(sh, r, c)));
      values.push(row);
    }
    return matrix(values, { sheet: sh, r1: top, c1: left });
  }

  function addressOf(e: Expr): Addr | null {
    if (e.type === 'ref') {
      const sheet = resolveSheet(e.sheet, ctx.sheet);
      return { sheet, r1: e.row, c1: e.col, r2: e.row, c2: e.col };
    }
    if (e.type === 'range' && e.a.type === 'ref' && e.b.type === 'ref') {
      const sheet = resolveSheet(e.a.sheet ?? e.b.sheet, ctx.sheet);
      return {
        sheet,
        r1: Math.min(e.a.row, e.b.row),
        c1: Math.min(e.a.col, e.b.col),
        r2: Math.max(e.a.row, e.b.row),
        c2: Math.max(e.a.col, e.b.col),
      };
    }
    if (e.type === 'cols') {
      const sheet = resolveSheet(e.sheet, ctx.sheet);
      const s = sheets.get(sheet);
      return { sheet, r1: 0, c1: e.c1, r2: Math.max(0, (s?.rows ?? 1) - 1), c2: e.c2 };
    }
    if (e.type === 'rows') {
      const sheet = resolveSheet(e.sheet, ctx.sheet);
      const s = sheets.get(sheet);
      return { sheet, r1: e.r1, c1: 0, r2: e.r2, c2: Math.max(0, (s?.cols ?? 1) - 1) };
    }
    if (e.type === 'name') {
      const named = findName(e.name);
      if (named && named.r1 !== undefined && named.c1 !== undefined && named.r2 !== undefined && named.c2 !== undefined) {
        return { sheet: resolveSheet(named.sheet, ctx.sheet), r1: named.r1, c1: named.c1, r2: named.r2, c2: named.c2 };
      }
    }
    if (e.type === 'struct') {
      const table = findTable(e.table, ctx.sheet, ctx.row, ctx.col);
      if (!table) return null;
      const header = headerMap(table);
      const col = header.get(e.column.toLocaleLowerCase('de-DE'));
      if (col === undefined) return null;
      const r1 = table.r1 + 1;
      const r2 = table.totalsRow ? table.r2 - 1 : table.r2;
      if (e.thisRow) {
        if (ctx.row < r1 || ctx.row > r2) return null;
        return { sheet: table.sheet, r1: ctx.row, c1: col, r2: ctx.row, c2: col };
      }
      return { sheet: table.sheet, r1, c1: col, r2, c2: col };
    }
    if (e.type === 'spill' && e.ref.type === 'ref') {
      const sheet = resolveSheet(e.ref.sheet, ctx.sheet);
      evalCell(sheet, e.ref.row, e.ref.col);
      return anchors.get(keyOf(sheet, e.ref.row, e.ref.col)) ?? { sheet, r1: e.ref.row, c1: e.ref.col, r2: e.ref.row, c2: e.ref.col };
    }
    return null;
  }

  function findName(name: string): NameInput | undefined {
    const n = name.toLowerCase();
    return (model.names ?? []).find((x) => x.name.toLowerCase() === n);
  }

  function findTable(name: string | undefined, sheet: string, row: number, col: number): TableInput | undefined {
    const tables = model.tables ?? [];
    if (name) return tables.find((t) => t.name.toLowerCase() === name.toLowerCase());
    return tables.find((t) => t.sheet === sheet && row >= t.r1 && row <= t.r2 && col >= t.c1 && col <= t.c2);
  }

  function headerMap(table: TableInput): Map<string, number> {
    const map = new Map<string, number>();
    for (let c = table.c1; c <= table.c2; c++) {
      const v = evalCell(table.sheet, table.r1, c);
      const s = isErr(v) || v === null ? '' : String(isMatrix(v) ? '' : (v as Scalar));
      if (s) map.set(s.toLocaleLowerCase('de-DE'), c);
    }
    return map;
  }

  function rangeOf(e: Expr): Matrix | FError {
    const addr = addressOf(e);
    if (addr) return readRange(addr.sheet, addr.r1, addr.c1, addr.r2, addr.c2);
    if (e.type === 'ref' || e.type === 'range' || e.type === 'cols' || e.type === 'rows' || e.type === 'struct' || e.type === 'name' || e.type === 'spill') {
      return BEZUG();
    }
    const v = evalExpr(e);
    if (isErr(v)) return v;
    if (isMatrix(v)) return v;
    if (isSpark(v) || isLambda(v)) return WERT();
    if (isLink(v)) return matrix([[v.label]]);
    return matrix([[v as Scalar]]);
  }

  function callLambda(lam: LambdaVal, args: Value[]): Value {
    if (depth > 80) return ZAHL();
    if (args.length !== lam.params.length) return WERT();
    for (const a of args) if (isErr(a)) return a;
    depth++;
    const mark = localStack.length;
    try {
      lam.params.forEach((p, i) => setLocal(p, args[i]));
      return evalExpr(lam.body);
    } finally {
      restoreLocals(mark);
      depth--;
    }
  }

  function evalNamed(named: NameInput): Value {
    if (!named.formula) return NAME();
    if (depth > 80) return ZAHL();
    depth++;
    try {
      const body = named.formula.startsWith('=') ? named.formula.slice(1) : named.formula;
      return evalExpr(tryParseFormula(body));
    } finally {
      depth--;
    }
  }

  Object.assign(ctx, {
    sheet: model.sheets[0]?.name ?? 'Tabelle1',
    row: 0,
    col: 0,
    eval: (e: Expr) => evalExpr(e),
    rangeOf,
    addressOf,
    readRange,
    raw: rawOf,
    hidden: (sheet: string, row: number) => hidden.has(`${resolveSheet(sheet)}\n${row}`),
    names: model.names ?? [],
    tables: model.tables ?? [],
    rows: (sheet: string) => sheets.get(resolveSheet(sheet))?.rows ?? 0,
    cols: (sheet: string) => sheets.get(resolveSheet(sheet))?.cols ?? 0,
    sheetNames: model.sheets.map((s) => s.name),
    callLambda,
    localMark: () => localStack.length,
    setLocal,
    restoreLocals,
    spillOf: (sheet: string, r: number, c: number) => anchors.get(keyOf(sheet, r, c)) ?? null,
  } satisfies FnCtx);

  function evalCell(sheet: string, r: number, c: number): Value {
    const sh = resolveSheet(sheet);
    const key = keyOf(sh, r, c);
    if (cache.has(key)) return cache.get(key)!;
    if (visiting.has(key)) return BEZUG();
    const raw = rawOf(sh, r, c);
    if (!raw) {
      if (spills.has(key)) return spills.get(key)!;
      return resolveEmpty(sh, r, c);
    }
    visiting.add(key);
    const prev = { sheet: ctx.sheet, row: ctx.row, col: ctx.col };
    ctx.sheet = sh;
    ctx.row = r;
    ctx.col = c;
    let result: Value;
    try {
      if (raw.startsWith('=')) {
        result = evalExpr(tryParseFormula(raw.slice(1)));
        result = placeSpill(sh, r, c, result);
      } else result = parseLiteral(raw);
    } catch (e) {
      result = e instanceof FError ? e : FEHLER();
    } finally {
      ctx.sheet = prev.sheet;
      ctx.row = prev.row;
      ctx.col = prev.col;
      visiting.delete(key);
    }
    cache.set(key, result);
    return result;
  }

  function resolveEmpty(sheet: string, r: number, c: number): Value {
    const key = keyOf(sheet, r, c);
    if (resolving.has(key)) return null;
    resolving.add(key);
    for (const f of formulas.get(sheet) ?? []) {
      if (f.r <= r && f.c <= c && !(f.r === r && f.c === c)) {
        evalCell(sheet, f.r, f.c);
        if (spills.has(key)) {
          resolving.delete(key);
          const v = spills.get(key)!;
          cache.set(key, v);
          return v;
        }
      }
    }
    resolving.delete(key);
    const empty: Value = null;
    cache.set(key, empty);
    return empty;
  }

  function placeSpill(sheet: string, r: number, c: number, value: Value): Value {
    if (!isMatrix(value)) return value;
    const h = value.values.length;
    const w = value.values[0]?.length ?? 0;
    if (h === 0 || w === 0) return new FError('#NV');
    if (h === 1 && w === 1) {
      const only = value.values[0][0];
      return isErr(only) ? only : (only as Scalar);
    }
    for (let rr = 0; rr < h; rr++) {
      for (let cc = 0; cc < w; cc++) {
        if (rr === 0 && cc === 0) continue;
        const k = keyOf(sheet, r + rr, c + cc);
        if (rawOf(sheet, r + rr, c + cc)) return new FError('#ÜBERLAUF!');
        if (spills.has(k) && !spillFrom.has(k + '|' + keyOf(sheet, r, c))) return new FError('#ÜBERLAUF!');
      }
    }
    const anchor = keyOf(sheet, r, c);
    anchors.set(anchor, { sheet, r1: r, c1: c, r2: r + h - 1, c2: c + w - 1 });
    for (let rr = 0; rr < h; rr++) {
      for (let cc = 0; cc < w; cc++) {
        if (rr === 0 && cc === 0) continue;
        const cell = value.values[rr][cc];
        const k = keyOf(sheet, r + rr, c + cc);
        const v: Value = isErr(cell) ? cell : cell;
        spills.set(k, v);
        cache.set(k, v);
        spillFrom.add(k);
      }
    }
    const top = value.values[0][0];
    return isErr(top) ? top : (top as Scalar);
  }

  function evalExpr(e: Expr): Value {
    switch (e.type) {
      case 'num':
        return e.value;
      case 'str':
        return e.value;
      case 'bool':
        return e.value;
      case 'err':
        return new FError(e.code);
      case 'ref':
        return evalCell(resolveSheet(e.sheet, ctx.sheet), e.row, e.col);
      case 'range':
      case 'cols':
      case 'rows':
      case 'struct':
      case 'spill':
        return rangeOf(e);
      case 'name': {
        const local = locals.get(e.name.toUpperCase());
        if (local !== undefined) return local;
        const named = findName(e.name);
        if (!named) return NAME();
        if (named.formula) return evalNamed(named);
        if (named.r1 !== undefined && named.c1 !== undefined && named.r2 !== undefined && named.c2 !== undefined) {
          return readRange(named.sheet || ctx.sheet, named.r1, named.c1, named.r2, named.c2);
        }
        return NAME();
      }
      case 'unary':
        return evalUnary(e.op, evalExpr(e.expr));
      case 'binary':
        return evalBinary(e.op, evalExpr(e.left), evalExpr(e.right));
      case 'array': {
        const rows: CellVal[][] = [];
        for (const row of e.rows) {
          const out: CellVal[] = [];
          for (const cell of row) {
            const v = evalExpr(cell);
            if (isMatrix(v) || isSpark(v) || isLambda(v)) return WERT();
            if (isLink(v)) out.push(v.label);
            else if (isErr(v)) out.push(v);
            else out.push(v);
          }
          rows.push(out);
        }
        return matrix(rows);
      }
      case 'call': {
        if (depth > 100) return ZAHL();
        const builtin = registry.get(e.name.toUpperCase());
        if (builtin) {
          depth++;
          try {
            return builtin(e.args, ctx);
          } finally {
            depth--;
          }
        }
        const named = findName(e.name);
        if (!named) return NAME();
        const v = named.formula ? evalNamed(named) : NAME();
        if (isErr(v)) return v;
        if (isLambda(v)) return callLambda(v, e.args.map((a) => evalExpr(a)));
        return e.args.length ? WERT() : v;
      }
      case 'invoke': {
        const fn = evalExpr(e.fn);
        if (isErr(fn)) return fn;
        if (!isLambda(fn)) return WERT();
        return callLambda(fn, e.args.map((a) => evalExpr(a)));
      }
      default:
        return FEHLER();
    }
  }

  for (const s of model.sheets) {
    for (const [k, cell] of Object.entries(s.cells)) {
      if (!cell?.raw) continue;
      const [r, c] = k.split(',').map(Number);
      evalCell(s.name, r, c);
    }
  }

  const out = new Map<string, Computed>();
  for (const [k, v] of cache) {
    const [sheet, rc] = k.split('\n');
    const spill = spillFrom.has(k);
    out.set(`${sheet}!${rc}`, toComputed(v, spill));
  }
  return out;
}

function asCell(v: Value): CellVal {
  if (isErr(v)) return v;
  if (isMatrix(v)) {
    const c = v.values[0]?.[0];
    return c === undefined ? null : c;
  }
  if (isSpark(v) || isLambda(v)) return null;
  if (isLink(v)) return v.label;
  return v;
}

function toComputed(v: Value, spill: boolean): Computed {
  if (isErr(v)) return { value: null, error: v.code, spill };
  if (isSpark(v)) return { value: null, error: null, spill, spark: { values: v.values, mode: v.mode } };
  if (isLink(v)) return { value: v.label, error: null, spill, href: v.href, label: v.label };
  if (isLambda(v)) return { value: null, error: '#BERECH!', spill, lambda: true };
  if (isMatrix(v)) return toComputed(asCell(v) as Value, spill);
  return { value: v, error: null, spill };
}

function numOf(v: Value): number | FError {
  if (isErr(v)) return v;
  if (isMatrix(v)) return v.values.length === 1 && v.values[0].length === 1 ? numOf(v.values[0][0]) : WERT();
  if (typeof v === 'number') return v;
  if (typeof v === 'boolean') return v ? 1 : 0;
  if (v === null || v === '') return 0;
  if (typeof v === 'string') {
    const n = parseNumberDe(v);
    if (n !== null) return n;
    return WERT();
  }
  if (isLink(v)) return numOf(v.label);
  return WERT();
}

function textOf(v: Scalar): string {
  if (v === null) return '';
  if (typeof v === 'boolean') return v ? 'WAHR' : 'FALSCH';
  if (typeof v === 'number') return formatGeneral(v);
  return v;
}

function evalUnary(op: '+' | '-' | '%', v: Value): Value {
  if (isErr(v)) return v;
  if (isMatrix(v)) {
    const values = v.values.map((row) => row.map((c) => asCell(evalUnary(op, isErr(c) ? c : c))));
    return matrix(values);
  }
  const n = numOf(v);
  if (isErr(n)) return n;
  if (op === '%') return n / 100;
  if (op === '-') return -n;
  return n;
}

function evalBinary(op: string, left: Value, right: Value): Value {
  if (isErr(left)) return left;
  if (isErr(right)) return right;
  if (isMatrix(left) || isMatrix(right)) return broadcast(op, left, right);
  return scalarOp(op, left as Scalar, right as Scalar);
}

function scalarOp(op: string, l: Scalar, r: Scalar): Value {
  if (op === '&') return textOf(l) + textOf(r);
  if (op === '=' || op === '<>' || op === '<' || op === '>' || op === '<=' || op === '>=') {
    const c = cmp(l, r);
    if (op === '=') return c === 0;
    if (op === '<>') return c !== 0;
    if (op === '<') return c < 0;
    if (op === '>') return c > 0;
    if (op === '<=') return c <= 0;
    return c >= 0;
  }
  const ln = numOf(l);
  const rn = numOf(r);
  if (isErr(ln)) return ln;
  if (isErr(rn)) return rn;
  switch (op) {
    case '+':
      return ln + rn;
    case '-':
      return ln - rn;
    case '*':
      return ln * rn;
    case '/':
      return rn === 0 ? DIV0() : ln / rn;
    case '^': {
      if (ln === 0 && rn <= 0) return ZAHL();
      const v = ln ** rn;
      return Number.isFinite(v) ? v : ZAHL();
    }
    default:
      return FEHLER();
  }
}

function cmp(l: Scalar, r: Scalar): number {
  const lb = l === null || l === '';
  const rb = r === null || r === '';
  if (lb && rb) return 0;
  if (lb && typeof r === 'number') l = 0;
  if (rb && typeof l === 'number') r = 0;
  if (lb && typeof r === 'string') l = '';
  if (rb && typeof l === 'string') r = '';
  if (typeof l === 'number' && typeof r === 'number') return l === r ? 0 : l < r ? -1 : 1;
  if (typeof l === 'boolean' && typeof r === 'boolean') return l === r ? 0 : l ? 1 : -1;
  if (typeof l === 'number' && typeof r === 'string') return -1;
  if (typeof l === 'string' && typeof r === 'number') return 1;
  const as = String(l).toLocaleLowerCase('de-DE');
  const bs = String(r).toLocaleLowerCase('de-DE');
  return as < bs ? -1 : as > bs ? 1 : 0;
}

function broadcast(op: string, left: Value, right: Value): Value {
  const A = isMatrix(left) ? left : matrix([[asCell(left)]]);
  const B = isMatrix(right) ? right : matrix([[asCell(right)]]);
  const ah = A.values.length || 1;
  const aw = A.values[0]?.length || 1;
  const bh = B.values.length || 1;
  const bw = B.values[0]?.length || 1;
  const h = fitDim(ah, bh);
  const w = fitDim(aw, bw);
  if (h === null || w === null) return WERT();
  const av = expand(A, h, w);
  const bv = expand(B, h, w);
  if (isErr(av)) return av;
  if (isErr(bv)) return bv;
  const values: CellVal[][] = [];
  for (let r = 0; r < h; r++) {
    const row: CellVal[] = [];
    for (let c = 0; c < w; c++) {
      const x = av[r][c];
      const y = bv[r][c];
      if (isErr(x)) row.push(x);
      else if (isErr(y)) row.push(y);
      else {
        const v = scalarOp(op, x, y);
        row.push(isErr(v) ? v : isMatrix(v) ? WERT() : (v as Scalar));
      }
    }
    values.push(row);
  }
  return matrix(values);
}

function fitDim(a: number, b: number): number | null {
  if (a === b) return a;
  if (a === 1) return b;
  if (b === 1) return a;
  return null;
}

function expand(m: Matrix, h: number, w: number): CellVal[][] | FError {
  const mh = m.values.length || 1;
  const mw = m.values[0]?.length || 1;
  const src = m.values.length ? m.values : [[null]];
  if (mh === h && mw === w) return src;
  if (mh === 1 && mw === 1) return Array.from({ length: h }, () => Array.from({ length: w }, () => src[0][0]));
  if (mh === h && mw === 1) return src.map((row) => Array.from({ length: w }, () => row[0]));
  if (mh === 1 && mw === w) return Array.from({ length: h }, () => [...src[0]]);
  return WERT();
}

export function resultAt(map: Map<string, Computed>, sheet: string, addr: string): Computed | undefined {
  const m = /^([A-Za-z]+)(\d+)$/.exec(addr);
  if (!m) return undefined;
  let n = 0;
  for (const ch of m[1].toUpperCase()) n = n * 26 + (ch.charCodeAt(0) - 64);
  return map.get(`${sheet}!${Number(m[2]) - 1},${n - 1}`);
}
