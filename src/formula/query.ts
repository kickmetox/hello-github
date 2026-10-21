import { isErr, WERT, ZAHL, type CellVal, type FError, type Matrix, type Scalar } from './value';

type Tok = { k: 'id' | 'num' | 'str' | 'op' | 'sym'; v: string; n?: number };

function tokenize(sql: string): Tok[] {
  const s = sql.trim().replace(/;+\s*$/, '');
  const out: Tok[] = [];
  let i = 0;
  const isWord = (c: string) => /[A-Za-zÄÖÜäöü0-9_]/.test(c);
  while (i < s.length) {
    const c = s[i];
    if (/\s/.test(c)) {
      i++;
      continue;
    }
    if (c === '"' || c === "'") {
      const q = c;
      i++;
      let v = '';
      while (i < s.length) {
        if (s[i] === q) {
          if (s[i + 1] === q) {
            v += q;
            i += 2;
            continue;
          }
          i++;
          break;
        }
        v += s[i++];
      }
      out.push({ k: 'str', v });
      continue;
    }
    if (/\d/.test(c) || (c === '.' && /\d/.test(s[i + 1] ?? ''))) {
      let j = i;
      while (/[\d.,]/.test(s[j] ?? '')) j++;
      const raw = s.slice(i, j);
      let n: number;
      if (/^\d{1,3}(\.\d{3})+(,\d+)?$/.test(raw)) n = Number(raw.replace(/\./g, '').replace(',', '.'));
      else if (raw.includes(',') && !raw.includes('.')) n = Number(raw.replace(',', '.'));
      else n = Number(raw.replace(/,/g, ''));
      out.push({ k: 'num', v: raw, n });
      i = j;
      continue;
    }
    if (/[A-Za-zÄÖÜäöü_]/.test(c)) {
      let j = i + 1;
      while (isWord(s[j] ?? '') || s[j] === '.') j++;
      out.push({ k: 'id', v: s.slice(i, j) });
      i = j;
      continue;
    }
    const two = s.slice(i, i + 2);
    if (['>=', '<=', '<>', '!='].includes(two)) {
      out.push({ k: 'op', v: two === '!=' ? '<>' : two });
      i += 2;
      continue;
    }
    if ('=<>+-*/(),*:!'.includes(c)) {
      const sym = c === '*' || c === '(' || c === ')' || c === ',' || c === ':' || c === '!';
      out.push({ k: sym ? 'sym' : 'op', v: c });
      i++;
      continue;
    }
    throw new Error('sql');
  }
  return out;
}

const KW = new Set(['SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'ORDER', 'AS', 'AND', 'OR', 'NOT', 'ASC', 'DESC', 'LIKE', 'UND', 'ODER', 'NICHT']);

class QParser {
  i = 0;
  constructor(private t: Tok[]) {}
  peek(): Tok | undefined {
    return this.t[this.i];
  }
  eat(): Tok {
    const t = this.t[this.i++];
    if (!t) throw new Error('sql');
    return t;
  }
  isKw(w: string): boolean {
    const t = this.peek();
    return !!t && t.k === 'id' && t.v.toUpperCase() === w;
  }
  eatKw(w: string): boolean {
    if (!this.isKw(w)) return false;
    this.i++;
    return true;
  }
}

type E =
  | { t: 'num'; n: number }
  | { t: 'str'; v: string }
  | { t: 'col'; name: string }
  | { t: 'star' }
  | { t: 'un'; op: string; x: E }
  | { t: 'bin'; op: string; l: E; r: E }
  | { t: 'agg'; fn: string; arg: E }
  | { t: 'callstar'; fn: string };

interface SelectItem {
  expr: E;
  alias?: string;
  star?: boolean;
}

function parseExpr(p: QParser, min = 0): E {
  let left = parseUnary(p);
  for (;;) {
    const t = p.peek();
    if (!t) break;
    const op = t.k === 'op' || (t.k === 'sym' && t.v === '*') ? t.v : t.k === 'id' && KW.has(t.v.toUpperCase()) ? t.v.toUpperCase() : '';
    const prec = PREC[op];
    if (prec === undefined || prec < min) break;
    p.eat();
    const right = parseExpr(p, prec + 1);
    left = { t: 'bin', op: op === 'UND' ? 'AND' : op === 'ODER' ? 'OR' : op, l: left, r: right };
  }
  return left;
}

const PREC: Record<string, number> = {
  OR: 1,
  ODER: 1,
  AND: 2,
  UND: 2,
  '=': 3,
  '<>': 3,
  '<': 3,
  '>': 3,
  '<=': 3,
  '>=': 3,
  LIKE: 3,
  '+': 4,
  '-': 4,
  '*': 5,
  '/': 5,
};

function parseUnary(p: QParser): E {
  if (p.isKw('NOT') || p.isKw('NICHT')) {
    p.eat();
    return { t: 'un', op: 'NOT', x: parseUnary(p) };
  }
  const t = p.peek();
  if (t && t.k === 'op' && (t.v === '+' || t.v === '-')) {
    p.eat();
    return { t: 'un', op: t.v, x: parseUnary(p) };
  }
  return parsePrimary(p);
}

function parsePrimary(p: QParser): E {
  const t = p.eat();
  if (t.k === 'num') return { t: 'num', n: t.n ?? 0 };
  if (t.k === 'str') return { t: 'str', v: t.v };
  if (t.k === 'sym' && t.v === '(') {
    const e = parseExpr(p, 0);
    if (p.peek()?.v !== ')') throw new Error('sql');
    p.eat();
    return e;
  }
  if (t.k === 'sym' && t.v === '*') return { t: 'star' };
  if (t.k === 'id') {
    const name = t.v;
    const up = name.toUpperCase();
    if (['SUM', 'SUMME', 'AVG', 'MITTELWERT', 'COUNT', 'ANZAHL', 'DANZAHL', 'MIN', 'MAX', 'COUNTD'].includes(up) && p.peek()?.v === '(') {
      p.eat();
      if (p.peek()?.k === 'sym' && p.peek()?.v === '*') {
        p.eat();
        if (p.peek()?.v !== ')') throw new Error('sql');
        p.eat();
        return { t: 'callstar', fn: normAgg(up) };
      }
      const arg = parseExpr(p, 0);
      if (p.peek()?.v !== ')') throw new Error('sql');
      p.eat();
      return { t: 'agg', fn: normAgg(up), arg };
    }
    if (p.peek()?.v === '.') {
      /* ignore */
    }
    return { t: 'col', name };
  }
  throw new Error('sql');
}

function normAgg(fn: string): string {
  if (fn === 'SUMME' || fn === 'SUM') return 'SUM';
  if (fn === 'MITTELWERT' || fn === 'AVG') return 'AVG';
  if (fn === 'ANZAHL' || fn === 'COUNT' || fn === 'DANZAHL') return 'COUNT';
  return fn;
}

function parseSelect(p: QParser): SelectItem[] {
  const items: SelectItem[] = [];
  for (;;) {
    if (p.peek()?.k === 'sym' && p.peek()?.v === '*') {
      p.eat();
      items.push({ expr: { t: 'star' }, star: true });
    } else {
      const expr = parseExpr(p, 0);
      let alias: string | undefined;
      if (p.eatKw('AS')) {
        const a = p.eat();
        alias = a.v;
      } else if (p.peek()?.k === 'id' && !KW.has(p.peek()!.v.toUpperCase())) {
        alias = p.eat().v;
      }
      items.push({ expr, alias });
    }
    if (p.peek()?.k === 'sym' && p.peek()?.v === ',') {
      p.eat();
      continue;
    }
    break;
  }
  return items;
}

function headerKey(v: CellVal, i: number): string {
  if (v === null || v === '') return `Spalte${i + 1}`;
  if (isErr(v)) return v.code;
  return String(v);
}

function num(v: Scalar | FError): number | null {
  if (typeof v === 'number') return v;
  if (typeof v === 'boolean') return v ? 1 : 0;
  if (typeof v === 'string') {
    const n = Number(v.replace(/\./g, '').replace(',', '.'));
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function truth(v: Scalar | FError): boolean {
  if (isErr(v)) return false;
  if (v === true) return true;
  if (typeof v === 'number') return v !== 0;
  if (typeof v === 'string') return v !== '' && v.toLowerCase() !== 'falsch';
  return false;
}

function cmp(a: Scalar | FError, b: Scalar | FError): number {
  if (isErr(a) || isErr(b)) return 1;
  if (typeof a === 'number' && typeof b === 'number') return a === b ? 0 : a < b ? -1 : 1;
  const as = a === null ? '' : String(a).toLocaleLowerCase('de-DE');
  const bs = b === null ? '' : String(b).toLocaleLowerCase('de-DE');
  const an = num(a);
  const bn = num(b);
  if (an !== null && bn !== null && typeof a !== 'boolean' && typeof b !== 'boolean') return an === bn ? 0 : an < bn ? -1 : 1;
  return as < bs ? -1 : as > bs ? 1 : 0;
}

interface Frame {
  headers: string[];
  rec: (Scalar | FError)[];
  group?: (Scalar | FError)[][];
}

function colIndex(headers: string[], name: string): number {
  const n = name.toLocaleLowerCase('de-DE');
  return headers.findIndex((h) => h.toLocaleLowerCase('de-DE') === n);
}

function evalE(e: E, f: Frame): Scalar | FError {
  switch (e.t) {
    case 'num':
      return e.n;
    case 'str':
      return e.v;
    case 'star':
      return WERT();
    case 'col': {
      const i = colIndex(f.headers, e.name);
      if (i < 0) return WERT();
      return f.rec[i];
    }
    case 'un': {
      const v = evalE(e.x, f);
      if (isErr(v)) return v;
      if (e.op === 'NOT') return !truth(v);
      const n = num(v);
      if (n === null) return WERT();
      return e.op === '-' ? -n : n;
    }
    case 'callstar':
      return f.group ? f.group.length : 1;
    case 'agg':
      return evalAgg(e.fn, e.arg, f);
    case 'bin': {
      if (e.op === 'AND') return truth(evalE(e.l, f)) && truth(evalE(e.r, f));
      if (e.op === 'OR') return truth(evalE(e.l, f)) || truth(evalE(e.r, f));
      const l = evalE(e.l, f);
      const r = evalE(e.r, f);
      if (isErr(l)) return l;
      if (isErr(r)) return r;
      if (e.op === 'LIKE' || e.op === '=') {
        if (typeof r === 'string' && /[*?%]/.test(r)) {
          const pat = '^' + r.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/%/g, '.*').replace(/\*/g, '.*').replace(/\?/g, '.') + '$';
          return new RegExp(pat, 'i').test(l === null ? '' : String(l));
        }
      }
      if ('=<> < > <= >='.includes(e.op) || ['=', '<>', '<', '>', '<=', '>=', 'LIKE'].includes(e.op)) {
        const c = cmp(l, r);
        if (e.op === '=' || e.op === 'LIKE') return c === 0;
        if (e.op === '<>') return c !== 0;
        if (e.op === '<') return c < 0;
        if (e.op === '>') return c > 0;
        if (e.op === '<=') return c <= 0;
        if (e.op === '>=') return c >= 0;
      }
      const ln = num(l);
      const rn = num(r);
      if (ln === null || rn === null) return WERT();
      if (e.op === '+') return ln + rn;
      if (e.op === '-') return ln - rn;
      if (e.op === '*') return ln * rn;
      if (e.op === '/') return rn === 0 ? WERT() : ln / rn;
      return WERT();
    }
    default:
      return WERT();
  }
}

function evalAgg(fn: string, arg: E, f: Frame): Scalar | FError {
  const rows = f.group ?? [f.rec];
  if (fn === 'COUNT' && arg.t === 'star') return rows.length;
  const vals: (Scalar | FError)[] = [];
  for (const rec of rows) {
    vals.push(evalE(arg, { headers: f.headers, rec }));
  }
  if (fn === 'COUNT') return vals.filter((v) => !isErr(v) && v !== null && v !== '').length;
  const nums = vals.map(num).filter((n): n is number => n !== null);
  if (fn === 'SUM') return nums.reduce((a, b) => a + b, 0);
  if (fn === 'AVG') return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : ZAHL();
  if (fn === 'MIN') return nums.length ? Math.min(...nums) : ZAHL();
  if (fn === 'MAX') return nums.length ? Math.max(...nums) : ZAHL();
  return WERT();
}

function hasAgg(e: E): boolean {
  if (e.t === 'agg' || e.t === 'callstar') return true;
  if (e.t === 'bin') return hasAgg(e.l) || hasAgg(e.r);
  if (e.t === 'un') return hasAgg(e.x);
  return false;
}

/**
 * SQL-Untermenge über einen Bereich mit Kopfzeile:
 * SELECT … FROM A1:E20 WHERE … GROUP BY … ORDER BY …
 */
export function executeQuery(sql: string, lookup: (source: string) => Matrix | FError): Matrix | FError {
  let tokens: Tok[];
  try {
    tokens = tokenize(sql);
  } catch {
    return WERT();
  }
  const p = new QParser(tokens);
  try {
    if (!p.eatKw('SELECT')) return WERT();
    const items = parseSelect(p);
    if (!p.eatKw('FROM')) return WERT();
    let from = '';
    while (p.peek() && !p.isKw('WHERE') && !p.isKw('GROUP') && !p.isKw('ORDER')) {
      from += p.eat().v;
    }
    let where: E | null = null;
    if (p.eatKw('WHERE')) where = parseExpr(p, 0);
    const groupCols: string[] = [];
    if (p.eatKw('GROUP')) {
      if (!p.eatKw('BY')) return WERT();
      for (;;) {
        const id = p.eat();
        groupCols.push(id.v);
        if (p.peek()?.v === ',') {
          p.eat();
          continue;
        }
        break;
      }
    }
    const order: { expr: E; desc: boolean }[] = [];
    if (p.eatKw('ORDER')) {
      if (!p.eatKw('BY')) return WERT();
      for (;;) {
        const expr = parseExpr(p, 0);
        let desc = false;
        if (p.eatKw('DESC')) desc = true;
        else p.eatKw('ASC');
        order.push({ expr, desc });
        if (p.peek()?.v === ',') {
          p.eat();
          continue;
        }
        break;
      }
    }
    if (p.peek()) return WERT();
    const src = lookup(from);
    if (isErr(src)) return src;
    if (!src.values.length) return { type: 'matrix', values: [['(leer)']] };
    const headers = src.values[0].map(headerKey);
    const data = src.values.slice(1).filter((r) => r.some((c) => c !== null && c !== ''));
    const filtered = data.filter((rec) => (where ? truth(evalE(where, { headers, rec })) : true));
    const aggregated = groupCols.length > 0 || items.some((it) => hasAgg(it.expr));
    type Out = { headers: string[]; rows: (Scalar | FError)[][] };
    const build = (groups: { keyRec: (Scalar | FError)[]; rows: (Scalar | FError)[][] }[]): Out => {
      const outHeaders: string[] = [];
      const exprs: { expr: E; star?: boolean }[] = [];
      for (const it of items) {
        if (it.star) {
          headers.forEach((h) => {
            outHeaders.push(h);
            exprs.push({ expr: { t: 'col', name: h } });
          });
        } else {
          outHeaders.push(it.alias ?? labelOf(it.expr));
          exprs.push({ expr: it.expr });
        }
      }
      const rows = groups.map((g) =>
        exprs.map(({ expr }) => {
          const frame: Frame = { headers, rec: g.keyRec, group: aggregated ? g.rows : undefined };
          return evalE(expr, frame);
        }),
      );
      return { headers: outHeaders, rows };
    };
    let groups: { keyRec: (Scalar | FError)[]; rows: (Scalar | FError)[][] }[];
    if (aggregated) {
      const map = new Map<string, { keyRec: (Scalar | FError)[]; rows: (Scalar | FError)[][] }>();
      for (const rec of filtered) {
        const key = groupCols.map((c) => String(rec[colIndex(headers, c)] ?? '')).join('\u0001');
        let g = map.get(key);
        if (!g) {
          const keyRec = headers.map((_, i) => rec[i]);
          g = { keyRec, rows: [] };
          map.set(key, g);
        }
        g.rows.push(rec);
      }
      if (map.size === 0 && groupCols.length === 0) groups = [{ keyRec: headers.map(() => null), rows: [] }];
      else groups = [...map.values()];
    } else {
      groups = filtered.map((rec) => ({ keyRec: rec, rows: [rec] }));
    }
    let out = build(groups);
    if (order.length) {
      const indexed = out.rows.map((row, i) => ({ row, g: groups[i] }));
      indexed.sort((a, b) => {
        for (const o of order) {
          const av = evalE(o.expr, { headers: out.headers, rec: a.row, group: a.g.rows });
          const bv = evalE(o.expr, { headers: out.headers, rec: b.row, group: b.g.rows });
          const c = cmp(av, bv);
          if (c !== 0) return o.desc ? -c : c;
        }
        return 0;
      });
      out = { headers: out.headers, rows: indexed.map((x) => x.row) };
    }
    return { type: 'matrix', values: [out.headers, ...out.rows] };
  } catch {
    return WERT();
  }
}

function labelOf(e: E): string {
  if (e.t === 'col') return e.name;
  if (e.t === 'agg') return `${e.fn}(${labelOf(e.arg)})`;
  if (e.t === 'callstar') return 'ANZAHL(*)';
  if (e.t === 'bin') return `${labelOf(e.l)} ${e.op} ${labelOf(e.r)}`;
  return 'Wert';
}
