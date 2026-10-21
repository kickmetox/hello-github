import { matchCriteria } from './criteria';
import {
  addMonths,
  dateToSerial,
  endOfMonth,
  formatDate,
  formatGeneral,
  formatNumber,
  isoWeek,
  parseDateStrict,
  parseDateTimeStrict,
  parseLiteral,
  parseNumberDe,
  parseTimeStrict,
  serialToParts,
} from './format';
import type { Expr } from './parser';
import { parseFormula } from './parser';
import { executeQuery } from './query';
import {
  BEZUG,
  BERECH,
  DIV0,
  FError,
  isErr,
  isLambda,
  isLink,
  isMatrix,
  isSpark,
  LambdaVal,
  LinkVal,
  matrix,
  NAME,
  NV,
  SparkVal,
  UEBER,
  WERT,
  ZAHL,
  type CellVal,
  type Matrix,
  type Scalar,
  type Value,
} from './value';

export interface NameInput {
  name: string;
  formula?: string;
  sheet?: string;
  r1?: number;
  c1?: number;
  r2?: number;
  c2?: number;
}

export interface TableInput {
  name: string;
  sheet: string;
  r1: number;
  c1: number;
  r2: number;
  c2: number;
  totalsRow?: boolean;
}

export interface Addr {
  sheet: string;
  r1: number;
  c1: number;
  r2: number;
  c2: number;
}

export interface FnCtx {
  sheet: string;
  row: number;
  col: number;
  eval: (e: Expr) => Value;
  rangeOf: (e: Expr) => Matrix | FError;
  addressOf: (e: Expr) => Addr | null;
  readRange: (sheet: string, r1: number, c1: number, r2: number, c2: number) => Matrix | FError;
  raw: (sheet: string, r: number, c: number) => string;
  hidden: (sheet: string, row: number) => boolean;
  names: NameInput[];
  tables: TableInput[];
  rows: (sheet: string) => number;
  cols: (sheet: string) => number;
  sheetNames: string[];
  callLambda: (lam: LambdaVal, args: Value[]) => Value;
  localMark: () => number;
  setLocal: (name: string, value: Value) => void;
  restoreLocals: (mark: number) => void;
  spillOf: (sheet: string, r: number, c: number) => Addr | null;
}

type Fn = (args: Expr[], ctx: FnCtx) => Value;

export interface FuncInfo {
  de: string;
  en: string;
  category: string;
  signature: string;
  desc: string;
}

export const FUNCTION_LIST: FuncInfo[] = [];
export const registry = new Map<string, Fn>();
export const deToEn = new Map<string, string>();
export const enToDe = new Map<string, string>();

function add(info: FuncInfo, fn: Fn, extra: string[] = []): void {
  FUNCTION_LIST.push(info);
  const names = new Set([info.de, info.en, ...extra].map((n) => n.toUpperCase()));
  for (const n of names) registry.set(n, fn);
  const de = info.de.toUpperCase();
  const en = info.en.toUpperCase();
  if (de !== en) {
    deToEn.set(de, en);
    enToDe.set(en, de);
  }
  for (const a of extra) {
    const u = a.toUpperCase();
    if (u !== de && u !== en && /^[A-Z]{2,}$/.test(en)) {
      /* alias stays callable, translator uses the primary pair */
    }
  }
}

function flat(v: Value): CellVal[] | FError {
  if (isErr(v)) return v;
  if (isMatrix(v)) {
    const out: CellVal[] = [];
    for (const row of v.values) {
      for (const c of row) {
        if (isErr(c)) return c;
        out.push(c);
      }
    }
    return out;
  }
  if (isSpark(v) || isLink(v) || isLambda(v)) return WERT();
  return [v];
}

function scalar(v: Value): Scalar | FError {
  if (isErr(v)) return v;
  if (isMatrix(v)) {
    if (v.values.length === 1 && v.values[0]?.length === 1) {
      const c = v.values[0][0];
      return isErr(c) ? c : c;
    }
    return WERT();
  }
  if (isSpark(v) || isLambda(v)) return WERT();
  if (isLink(v)) return v.label;
  return v;
}

function num(v: Value, blank = 0): number | FError {
  const s = scalar(v);
  if (isErr(s)) return s;
  if (typeof s === 'number') return s;
  if (typeof s === 'boolean') return s ? 1 : 0;
  if (s === null || s === '') return blank;
  if (typeof s === 'string') {
    if (/^(wahr|true)$/i.test(s)) return 1;
    if (/^(falsch|false)$/i.test(s)) return 0;
    const n = parseNumberDe(s);
    if (n !== null) return n;
    const d = parseDateTimeStrict(s) ?? (/^\d{1,2}\.\d{1,2}\.\d{2,4}$/.test(s) ? parseDateStrict(s) : null);
    if (d !== null) return d;
    return WERT();
  }
  return WERT();
}

function text(v: Value): string | FError {
  const s = scalar(v);
  if (isErr(s)) return s;
  if (s === null) return '';
  if (typeof s === 'boolean') return s ? 'WAHR' : 'FALSCH';
  if (typeof s === 'number') return formatGeneral(s);
  return String(s);
}

function truth(v: Value): boolean | FError {
  const s = scalar(v);
  if (isErr(s)) return s;
  if (typeof s === 'boolean') return s;
  if (typeof s === 'number') return s !== 0;
  if (s === null || s === '') return false;
  if (/^(wahr|true)$/i.test(s)) return true;
  if (/^(falsch|false)$/i.test(s)) return false;
  return WERT();
}

function numbers(v: Value, directBool = false): number[] | FError {
  if (isErr(v)) return v;
  if (isMatrix(v)) {
    const out: number[] = [];
    for (const row of v.values) {
      for (const c of row) {
        if (isErr(c)) return c;
        if (typeof c === 'number') out.push(c);
      }
    }
    return out;
  }
  if (typeof v === 'number') return [v];
  if (typeof v === 'boolean') return directBool ? [v ? 1 : 0] : [];
  if (isSpark(v) || isLink(v) || isLambda(v)) return WERT();
  return [];
}

function need(args: Expr[], n: number): FError | null {
  if (args.length < n) return WERT();
  return null;
}

function evalNum(ctx: FnCtx, e: Expr): number | FError {
  return num(ctx.eval(e));
}

function roundHalf(n: number, digits: number): number {
  const f = 10 ** digits;
  const x = n * f;
  const r = Math.round(x);
  return (Math.abs(x) % 1 === 0.5 && Math.abs(r) % 2 === 0 ? (n > 0 ? Math.floor(x) : Math.ceil(x)) : r) / f;
}

function roundMode(n: number, digits: number, mode: 'up' | 'down' | 'trunc'): number {
  const f = 10 ** Math.trunc(digits);
  const x = n * f;
  if (mode === 'trunc' || mode === 'down') return Math.trunc(x) / f;
  const y = n < 0 ? Math.floor(x - 1e-10) : Math.ceil(x + 1e-10);
  return y / f;
}

function avg(xs: number[]): number | FError {
  if (!xs.length) return DIV0();
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

function stdev(xs: number[], pop: boolean): number | FError {
  if (xs.length < (pop ? 1 : 2)) return DIV0();
  const m = xs.reduce((a, b) => a + b, 0) / xs.length;
  const s = xs.reduce((a, b) => a + (b - m) ** 2, 0);
  return Math.sqrt(s / (xs.length - (pop ? 0 : 1)));
}

function variance(xs: number[], pop: boolean): number | FError {
  const s = stdev(xs, pop);
  if (isErr(s)) return s;
  return s * s;
}

function percentile(xs: number[], p: number): number | FError {
  if (!xs.length || p < 0 || p > 1) return ZAHL();
  const s = [...xs].sort((a, b) => a - b);
  const rank = p * (s.length - 1);
  const lo = Math.floor(rank);
  const hi = Math.ceil(rank);
  if (lo === hi) return s[lo];
  return s[lo] + (s[hi] - s[lo]) * (rank - lo);
}

function gcd2(a: number, b: number): number {
  let x = Math.abs(Math.trunc(a));
  let y = Math.abs(Math.trunc(b));
  while (y) {
    const t = y;
    y = x % y;
    x = t;
  }
  return x;
}

function pmt(rate: number, nper: number, pv: number, fv = 0, type = 0): number | FError {
  if (nper === 0) return ZAHL();
  if (rate === 0) return -(pv + fv) / nper;
  const pow = (1 + rate) ** nper;
  let pay = (rate * (pv * pow + fv)) / (pow - 1);
  if (type === 1) pay /= 1 + rate;
  return -pay;
}

function fv(rate: number, nper: number, pmtv: number, pv = 0, type = 0): number | FError {
  if (rate === 0) return -(pv + pmtv * nper);
  const pow = (1 + rate) ** nper;
  return -(pv * pow + pmtv * (1 + rate * type) * ((pow - 1) / rate));
}

function pv(rate: number, nper: number, pmtv: number, fvVal = 0, type = 0): number | FError {
  if (rate === 0) return -(fvVal + pmtv * nper);
  const pow = (1 + rate) ** nper;
  return -((fvVal + pmtv * (1 + rate * type) * ((pow - 1) / rate)) / pow);
}

function nper(rate: number, pmtv: number, pvVal: number, fvVal = 0, type = 0): number | FError {
  if (pmtv === 0 && rate === 0) return ZAHL();
  if (rate === 0) return -(pvVal + fvVal) / pmtv;
  const z = (pmtv * (1 + rate * type)) / rate;
  const quot = (z - fvVal) / (pvVal + z);
  if (quot <= 0) return ZAHL();
  return Math.log(quot) / Math.log(1 + rate);
}

function irr(values: number[], guess = 0.1): number | FError {
  if (!values.some((v) => v > 0) || !values.some((v) => v < 0)) return ZAHL();
  let r = guess;
  for (let i = 0; i < 50; i++) {
    let npv = 0;
    let d = 0;
    for (let t = 0; t < values.length; t++) {
      const den = (1 + r) ** t;
      npv += values[t] / den;
      if (t > 0) d -= (t * values[t]) / (den * (1 + r));
    }
    if (Math.abs(d) < 1e-12) break;
    const next = r - npv / d;
    if (!Number.isFinite(next)) return ZAHL();
    if (Math.abs(next - r) < 1e-9) return next;
    r = Math.max(-0.999999, next);
  }
  return r;
}

function collectNums(ctx: FnCtx, args: Expr[], directBool = false): number[] | FError {
  const out: number[] = [];
  for (const a of args) {
    const v = ctx.eval(a);
    const xs = numbers(v, directBool && !isMatrix(v));
    if (isErr(xs)) return xs;
    out.push(...xs);
  }
  return out;
}

function rectMatch(range: Matrix, criteria: Scalar, sumRange?: Matrix): { sum: number; count: number; nums: number[] } | FError {
  const src = sumRange ?? range;
  const h = Math.min(range.values.length, src.values.length);
  let sum = 0;
  let count = 0;
  const nums: number[] = [];
  for (let r = 0; r < h; r++) {
    const w = Math.min(range.values[r].length, src.values[r].length);
    for (let c = 0; c < w; c++) {
      const left = range.values[r][c];
      if (isErr(left)) return left;
      if (!matchCriteria(left, criteria)) continue;
      const right = src.values[r][c];
      if (isErr(right)) return right;
      if (typeof right === 'number') {
        sum += right;
        count++;
        nums.push(right);
      }
    }
  }
  return { sum, count, nums };
}

function criteriaScalar(ctx: FnCtx, e: Expr): Scalar | FError {
  const v = scalar(ctx.eval(e));
  return v;
}

function ifsPairs(args: Expr[], ctx: FnCtx): Value {
  if (args.length < 2) return WERT();
  for (let i = 0; i + 1 < args.length; i += 2) {
    const cond = truth(ctx.eval(args[i]));
    if (isErr(cond)) return cond;
    if (cond) return ctx.eval(args[i + 1]);
  }
  return NV();
}

function dRows(db: Matrix, crit: Matrix): number[] | FError {
  if (!db.values.length || !crit.values.length) return WERT();
  const headers = db.values[0].map((h) => (h === null ? '' : String(h)).trim().toLocaleLowerCase('de-DE'));
  const ch = crit.values[0].map((h) => (h === null ? '' : String(h)).trim().toLocaleLowerCase('de-DE'));
  const mapIdx: (number | null)[] = [];
  for (const h of ch) {
    if (!h) {
      mapIdx.push(null);
      continue;
    }
    const i = headers.indexOf(h);
    if (i < 0) return WERT();
    mapIdx.push(i);
  }
  const rows: number[] = [];
  for (let r = 1; r < db.values.length; r++) {
    if (crit.values.length < 2) {
      rows.push(r);
      continue;
    }
    let any = false;
    for (let cr = 1; cr < crit.values.length; cr++) {
      let ok = true;
      for (let c = 0; c < mapIdx.length; c++) {
        const di = mapIdx[c];
        if (di === null) continue;
        const criterion = crit.values[cr][c];
        if (criterion === undefined || criterion === null || criterion === '') continue;
        if (isErr(criterion)) return criterion;
        const cell = db.values[r][di];
        if (isErr(cell)) return cell;
        if (!matchCriteria(cell, criterion)) {
          ok = false;
          break;
        }
      }
      if (ok) {
        any = true;
        break;
      }
    }
    if (any) rows.push(r);
  }
  return rows;
}

function fieldIndex(db: Matrix, field: Value): number | FError {
  const s = scalar(field);
  if (isErr(s)) return s;
  const width = db.values[0]?.length ?? 0;
  if (typeof s === 'number') {
    const i = Math.trunc(s) - 1;
    if (i < 0 || i >= width) return WERT();
    return i;
  }
  if (typeof s === 'string') {
    const want = s.trim().toLocaleLowerCase('de-DE');
    const i = db.values[0].findIndex((h) => String(h ?? '').trim().toLocaleLowerCase('de-DE') === want);
    if (i < 0) return WERT();
    return i;
  }
  return WERT();
}

function dField(args: Expr[], ctx: FnCtx): { rows: number[]; vals: CellVal[] } | FError {
  if (args.length < 3) return WERT();
  const db = ctx.rangeOf(args[0]);
  if (isErr(db)) return db;
  const field = ctx.eval(args[1]);
  if (isErr(field)) return field;
  const crit = ctx.rangeOf(args[2]);
  if (isErr(crit)) return crit;
  const idx = fieldIndex(db, field);
  if (isErr(idx)) return idx;
  const rows = dRows(db, crit);
  if (isErr(rows)) return rows;
  const vals = rows.map((r) => db.values[r][idx]);
  return { rows, vals };
}

function numericVals(vals: CellVal[]): number[] | FError {
  const out: number[] = [];
  for (const v of vals) {
    if (isErr(v)) return v;
    if (typeof v === 'number') out.push(v);
  }
  return out;
}

function mat(values: CellVal[][]): Matrix {
  return matrix(values);
}

function sameShape(a: Matrix, b: Matrix): boolean {
  if (a.values.length !== b.values.length) return false;
  return a.values.every((row, i) => row.length === b.values[i].length);
}

function parseComplex(input: string): { re: number; im: number } | null {
  const t = input.replace(/\s/g, '').replace(/j/gi, 'i').replace(',', '.');
  if (!t) return null;
  if (/^[+-]?i$/i.test(t)) return { re: 0, im: t.startsWith('-') ? -1 : 1 };
  let m = /^([+-]?(?:\d+(?:\.\d+)?))([+-](?:\d+(?:\.\d+)?)?)i$/i.exec(t);
  if (m) return { re: Number(m[1]), im: m[2] === '+' || m[2] === '-' ? Number(m[2] + '1') : Number(m[2]) };
  m = /^([+-]?(?:\d+(?:\.\d+)?))?i$/i.exec(t);
  if (m && /i$/i.test(t)) {
    const n = m[1] && m[1] !== '+' && m[1] !== '-' ? Number(m[1]) : t.startsWith('-') ? -1 : 1;
    return { re: 0, im: n };
  }
  if (/^[+-]?\d+(?:\.\d+)?$/.test(t)) return { re: Number(t), im: 0 };
  return null;
}

function fmtComplex(re: number, im: number): string {
  const a = formatGeneral(re);
  const b = formatGeneral(Math.abs(im));
  if (im === 0) return a;
  if (re === 0) return (im < 0 ? '-' : '') + b + 'i';
  return `${a}${im < 0 ? '-' : '+'}${b}i`;
}

const UNIT: Record<string, { dim: string; to: (n: number) => number; from: (n: number) => number }> = {};
function unit(name: string, dim: string, toBase: (n: number) => number, fromBase: (n: number) => number): void {
  UNIT[name.toLowerCase()] = { dim, to: toBase, from: fromBase };
}
unit('m', 'l', (n) => n, (n) => n);
unit('km', 'l', (n) => n * 1000, (n) => n / 1000);
unit('cm', 'l', (n) => n / 100, (n) => n * 100);
unit('mm', 'l', (n) => n / 1000, (n) => n * 1000);
unit('in', 'l', (n) => n * 0.0254, (n) => n / 0.0254);
unit('ft', 'l', (n) => n * 0.3048, (n) => n / 0.3048);
unit('yd', 'l', (n) => n * 0.9144, (n) => n / 0.9144);
unit('mi', 'l', (n) => n * 1609.344, (n) => n / 1609.344);
unit('g', 'm', (n) => n / 1000, (n) => n * 1000);
unit('kg', 'm', (n) => n, (n) => n);
unit('lb', 'm', (n) => n * 0.45359237, (n) => n / 0.45359237);
unit('lbm', 'm', (n) => n * 0.45359237, (n) => n / 0.45359237);
unit('oz', 'm', (n) => n * 0.028349523125, (n) => n / 0.028349523125);
unit('l', 'v', (n) => n / 1000, (n) => n * 1000);
unit('lt', 'v', (n) => n / 1000, (n) => n * 1000);
unit('ml', 'v', (n) => n / 1e6, (n) => n * 1e6);
unit('gal', 'v', (n) => n * 0.003785411784, (n) => n / 0.003785411784);
unit('c', 't', (n) => n, (n) => n);
unit('cel', 't', (n) => n, (n) => n);
unit('f', 't', (n) => ((n - 32) * 5) / 9, (n) => (n * 9) / 5 + 32);
unit('fah', 't', (n) => ((n - 32) * 5) / 9, (n) => (n * 9) / 5 + 32);
unit('k', 't', (n) => n - 273.15, (n) => n + 273.15);
unit('kel', 't', (n) => n - 273.15, (n) => n + 273.15);
unit('s', 's', (n) => n, (n) => n);
unit('sec', 's', (n) => n, (n) => n);
unit('min', 's', (n) => n * 60, (n) => n / 60);
unit('mn', 's', (n) => n * 60, (n) => n / 60);
unit('h', 's', (n) => n * 3600, (n) => n / 3600);
unit('hr', 's', (n) => n * 3600, (n) => n / 3600);
unit('d', 's', (n) => n * 86400, (n) => n / 86400);
unit('day', 's', (n) => n * 86400, (n) => n / 86400);
unit('j', 'e', (n) => n, (n) => n);
unit('cal', 'e', (n) => n * 4.184, (n) => n / 4.184);
unit('wh', 'e', (n) => n * 3600, (n) => n / 3600);
unit('kwh', 'e', (n) => n * 3.6e6, (n) => n / 3.6e6);
unit('pa', 'p', (n) => n, (n) => n);
unit('bar', 'p', (n) => n * 1e5, (n) => n / 1e5);
unit('psi', 'p', (n) => n * 6894.757, (n) => n / 6894.757);

function bin2dec(s: string): number | FError {
  const t = s.trim();
  if (!/^[01]+$/.test(t)) return ZAHL();
  if (t.length > 32) return ZAHL();
  const n = Number.parseInt(t, 2);
  if (t.length === 10 && t[0] === '1') return n - 1024;
  return n;
}
function dec2base(n: number, base: number, places?: number): string | FError {
  if (!Number.isFinite(n)) return ZAHL();
  let v = Math.trunc(n);
  let neg = false;
  if (base === 2 && v < 0) {
    if (v < -512) return ZAHL();
    v = (v + 1024) & 1023;
    neg = false;
  }
  if (v < 0) {
    neg = true;
    v = -v;
  }
  const digits = v.toString(base).toUpperCase();
  const body = places ? digits.padStart(places, '0') : digits;
  if (places && digits.length > places) return ZAHL();
  return (neg ? '-' : '') + body;
}

function networkdays(start: number, end: number, holidays: number[] = []): number {
  let a = Math.floor(start);
  let b = Math.floor(end);
  let sign = 1;
  if (a > b) {
    sign = -1;
    [a, b] = [b, a];
  }
  const hol = new Set(holidays.map((h) => Math.floor(h)));
  let count = 0;
  const span = b - a;
  if (span > 20000) return sign * Math.round((span * 5) / 7);
  for (let d = a; d <= b; d++) {
    const wd = serialToParts(d).wd;
    if (wd !== 0 && wd !== 6 && !hol.has(d)) count++;
  }
  return count * sign;
}

function workday(start: number, days: number, holidays: number[] = []): number | FError {
  let left = Math.trunc(days);
  let d = Math.floor(start);
  const step = left >= 0 ? 1 : -1;
  const hol = new Set(holidays.map((h) => Math.floor(h)));
  let guard = 0;
  while (left !== 0 && guard < 40000) {
    d += step;
    const wd = serialToParts(d).wd;
    if (wd !== 0 && wd !== 6 && !hol.has(d)) left -= step;
    guard++;
  }
  if (guard >= 40000) return ZAHL();
  return d;
}

function datedif(start: number, end: number, unit: string): number | FError {
  if (end < start) return ZAHL();
  const s = serialToParts(start);
  const e = serialToParts(end);
  const u = unit.toUpperCase();
  let months = (e.y - s.y) * 12 + (e.m - s.m);
  if (e.d < s.d) months--;
  if (u === 'Y' || u === 'J') return Math.floor(months / 12);
  if (u === 'M') return months;
  if (u === 'D' || u === 'T') return Math.floor(end) - Math.floor(start);
  if (u === 'YM') return ((months % 12) + 12) % 12;
  if (u === 'YD') {
    let probe = dateToSerial(e.y, s.m, Math.min(s.d, new Date(Date.UTC(e.y, s.m, 0)).getUTCDate()));
    if (probe > Math.floor(end)) probe = dateToSerial(e.y - 1, s.m, s.d);
    return Math.floor(end) - probe;
  }
  if (u === 'MD') {
    if (e.d >= s.d) return e.d - s.d;
    const dim = new Date(Date.UTC(e.y, e.m - 1, 0)).getUTCDate();
    return dim - s.d + e.d;
  }
  return WERT();
}

function lookupVector(m: Matrix): { vertical: boolean; values: CellVal[] } | FError {
  if (m.values.length > 1 && (m.values[0]?.length ?? 0) > 1) {
    const col = m.values.map((r) => r[0]);
    return { vertical: true, values: col };
  }
  if (m.values.length === 1) return { vertical: false, values: m.values[0] };
  return { vertical: true, values: m.values.map((r) => r[0]) };
}

function sameKey(k: CellVal, lookup: Scalar): boolean {
  if (isErr(k)) return false;
  if (typeof k === 'number' && typeof lookup === 'number') return Math.abs(k - lookup) <= 1e-9 * Math.max(1, Math.abs(lookup));
  if (typeof k === 'string' && typeof lookup === 'string') return k.toLocaleLowerCase('de-DE') === lookup.toLocaleLowerCase('de-DE');
  if ((k === null || k === '') && (lookup === null || lookup === '')) return true;
  return k === lookup;
}

function matchPos(keys: CellVal[], lookup: Scalar, mode: number, reverse: boolean): number | FError {
  const idxs = reverse ? [...keys.keys()].reverse() : [...keys.keys()];
  if (mode === 0 || mode === 2) {
    for (const i of idxs) {
      const k = keys[i];
      if (isErr(k)) return k;
      if (mode === 2 && typeof lookup === 'string' && matchCriteria((k ?? null) as Scalar, lookup)) return i;
      if (mode === 0 && sameKey(k, lookup)) return i;
    }
    return NV();
  }
  let best = -1;
  for (const i of idxs) {
    const k = keys[i];
    if (isErr(k) || k === null || k === '') continue;
    if (typeof lookup === 'number' && typeof k === 'number') {
      if (mode === -1 && k <= lookup && (best < 0 || k > (keys[best] as number))) best = i;
      if (mode === 1 && k >= lookup && (best < 0 || k < (keys[best] as number))) best = i;
    } else {
      const ks = String(k).toLocaleLowerCase('de-DE');
      const ls = String(lookup ?? '').toLocaleLowerCase('de-DE');
      const bestS = best < 0 ? '' : String(keys[best]).toLocaleLowerCase('de-DE');
      if (mode === -1 && ks <= ls && (best < 0 || ks > bestS)) best = i;
      if (mode === 1 && ks >= ls && (best < 0 || ks < bestS)) best = i;
    }
  }
  return best < 0 ? NV() : best;
}

function sortMatrix(m: Matrix, index: number, order: number, byCol: boolean): Matrix | FError {
  const rows = m.values.map((r) => [...r]);
  if (!byCol) {
    const idx = index - 1;
    if (idx < 0) return WERT();
    const keyed = rows.map((r, i) => ({ r, i }));
    keyed.sort((a, b) => {
      const av = a.r[idx] ?? null;
      const bv = b.r[idx] ?? null;
      const c = cmpVal(av, bv);
      return (order < 0 ? -c : c) || a.i - b.i;
    });
    return mat(keyed.map((k) => k.r));
  }
  return WERT();
}

function cmpVal(a: CellVal, b: CellVal): number {
  if (isErr(a) || isErr(b)) return 0;
  if (typeof a === 'number' && typeof b === 'number') return a === b ? 0 : a < b ? -1 : 1;
  if (a === null || a === '') return b === null || b === '' ? 0 : -1;
  if (b === null || b === '') return 1;
  const as = String(a).toLocaleLowerCase('de-DE');
  const bs = String(b).toLocaleLowerCase('de-DE');
  return as < bs ? -1 : as > bs ? 1 : 0;
}

function det(a: number[][]): number | FError {
  const n = a.length;
  const m = a.map((r) => [...r]);
  let sign = 1;
  for (let i = 0; i < n; i++) {
    let piv = i;
    for (let r = i + 1; r < n; r++) if (Math.abs(m[r][i]) > Math.abs(m[piv][i])) piv = r;
    if (Math.abs(m[piv][i]) < 1e-12) return 0;
    if (piv !== i) {
      [m[i], m[piv]] = [m[piv], m[i]];
      sign = -sign;
    }
    for (let r = i + 1; r < n; r++) {
      const f = m[r][i] / m[i][i];
      for (let c = i; c < n; c++) m[r][c] -= f * m[i][c];
    }
  }
  let d = sign;
  for (let i = 0; i < n; i++) d *= m[i][i];
  return d;
}

function invert(a: number[][]): number[][] | FError {
  const n = a.length;
  const m = a.map((r, i) => [...r, ...Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))]);
  for (let i = 0; i < n; i++) {
    let piv = i;
    for (let r = i + 1; r < n; r++) if (Math.abs(m[r][i]) > Math.abs(m[piv][i])) piv = r;
    if (Math.abs(m[piv][i]) < 1e-12) return ZAHL();
    if (piv !== i) [m[i], m[piv]] = [m[piv], m[i]];
    const div = m[i][i];
    for (let c = 0; c < 2 * n; c++) m[i][c] /= div;
    for (let r = 0; r < n; r++) {
      if (r === i) continue;
      const f = m[r][i];
      for (let c = 0; c < 2 * n; c++) m[r][c] -= f * m[i][c];
    }
  }
  return m.map((r) => r.slice(n));
}

function toNumMatrix(m: Matrix): number[][] | FError {
  const out: number[][] = [];
  for (const row of m.values) {
    const r: number[] = [];
    for (const c of row) {
      if (isErr(c)) return c;
      if (typeof c !== 'number') return WERT();
      r.push(c);
    }
    out.push(r);
  }
  if (!out.length || !out[0].length) return WERT();
  if (out.some((r) => r.length !== out[0].length)) return WERT();
  return out;
}

// --- Katalog ---

add({ de: 'SUMME', en: 'SUM', category: 'Mathematik', signature: 'SUMME(Zahl1; [Zahl2]; …)', desc: 'Addiert Zahlen. Text wird ignoriert.' }, (args, ctx) => {
  const xs = collectNums(ctx, args, true);
  if (isErr(xs)) return xs;
  return xs.reduce((a, b) => a + b, 0);
});
add({ de: 'PRODUKT', en: 'PRODUCT', category: 'Mathematik', signature: 'PRODUKT(Zahl1; …)', desc: 'Multipliziert alle Zahlen.' }, (args, ctx) => {
  const xs = collectNums(ctx, args, true);
  if (isErr(xs)) return xs;
  if (!xs.length) return 0;
  return xs.reduce((a, b) => a * b, 1);
});
add({ de: 'SUMMENPRODUKT', en: 'SUMPRODUCT', category: 'Mathematik', signature: 'SUMMENPRODUKT(Matrix1; [Matrix2]; …)', desc: 'Multipliziert Matrizen elementweise und summiert.' }, (args, ctx) => {
  if (!args.length) return WERT();
  const mats: Matrix[] = [];
  for (const a of args) {
    const m = ctx.rangeOf(a);
    if (isErr(m)) return m;
    mats.push(m);
  }
  const h = mats[0].values.length;
  const w = mats[0].values[0]?.length ?? 0;
  if (mats.some((m) => !sameShape(m, mats[0]))) return WERT();
  let s = 0;
  for (let r = 0; r < h; r++) {
    for (let c = 0; c < w; c++) {
      let p = 1;
      for (const m of mats) {
        const v = m.values[r][c];
        if (isErr(v)) return v;
        const nn = typeof v === 'number' ? v : typeof v === 'boolean' ? (v ? 1 : 0) : 0;
        p *= nn;
      }
      s += p;
    }
  }
  return s;
});
add({ de: 'ABS', en: 'ABS', category: 'Mathematik', signature: 'ABS(Zahl)', desc: 'Absolutwert.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  return isErr(n) ? n : Math.abs(n);
});
add({ de: 'VORZEICHEN', en: 'SIGN', category: 'Mathematik', signature: 'VORZEICHEN(Zahl)', desc: 'Vorzeichen: -1, 0 oder 1.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  return isErr(n) ? n : Math.sign(n);
});
add({ de: 'REST', en: 'MOD', category: 'Mathematik', signature: 'REST(Zahl; Divisor)', desc: 'Rest einer Division, Vorzeichen folgt dem Divisor.' }, (args, ctx) => {
  const a = evalNum(ctx, args[0]);
  const b = evalNum(ctx, args[1]);
  if (isErr(a)) return a;
  if (isErr(b)) return b;
  if (b === 0) return DIV0();
  return a - b * Math.floor(a / b);
});
add({ de: 'POTENZ', en: 'POWER', category: 'Mathematik', signature: 'POTENZ(Zahl; Potenz)', desc: 'Potenz.' }, (args, ctx) => {
  const a = evalNum(ctx, args[0]);
  const b = evalNum(ctx, args[1]);
  if (isErr(a) || isErr(b)) return isErr(a) ? a : b;
  if (a === 0 && b === 0) return ZAHL();
  const r = a ** b;
  return Number.isFinite(r) ? r : ZAHL();
});
add({ de: 'WURZEL', en: 'SQRT', category: 'Mathematik', signature: 'WURZEL(Zahl)', desc: 'Quadratwurzel.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  if (isErr(n)) return n;
  if (n < 0) return ZAHL();
  return Math.sqrt(n);
});
add({ de: 'RUNDEN', en: 'ROUND', category: 'Mathematik', signature: 'RUNDEN(Zahl; Stellen)', desc: 'Kaufmännisches Runden.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const d = args[1] ? evalNum(ctx, args[1]) : 0;
  if (isErr(n) || isErr(d)) return isErr(n) ? n : d;
  return roundHalf(n, Math.trunc(d));
});
add({ de: 'AUFRUNDEN', en: 'ROUNDUP', category: 'Mathematik', signature: 'AUFRUNDEN(Zahl; Stellen)', desc: 'Von Null weg runden.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const d = args[1] ? evalNum(ctx, args[1]) : 0;
  if (isErr(n) || isErr(d)) return isErr(n) ? n : d;
  return roundMode(n, d, 'up');
});
add({ de: 'ABRUNDEN', en: 'ROUNDDOWN', category: 'Mathematik', signature: 'ABRUNDEN(Zahl; Stellen)', desc: 'Richtung Null runden.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const d = args[1] ? evalNum(ctx, args[1]) : 0;
  if (isErr(n) || isErr(d)) return isErr(n) ? n : d;
  return roundMode(n, d, 'down');
});
add({ de: 'KÜRZEN', en: 'TRUNC', category: 'Mathematik', signature: 'KÜRZEN(Zahl; [Stellen])', desc: 'Nachkommastellen abschneiden.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const d = args[1] ? evalNum(ctx, args[1]) : 0;
  if (isErr(n) || isErr(d)) return isErr(n) ? n : d;
  return roundMode(n, d, 'trunc');
});
add({ de: 'GANZZAHL', en: 'INT', category: 'Mathematik', signature: 'GANZZAHL(Zahl)', desc: 'Abrunden auf die nächste ganze Zahl.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  return isErr(n) ? n : Math.floor(n);
});
add({ de: 'FAKULTÄT', en: 'FACT', category: 'Mathematik', signature: 'FAKULTÄT(Zahl)', desc: 'Fakultät n!.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  if (isErr(n)) return n;
  const k = Math.trunc(n);
  if (k < 0 || k > 170) return ZAHL();
  let r = 1;
  for (let i = 2; i <= k; i++) r *= i;
  return r;
});
add({ de: 'ZUFALLSZAHL', en: 'RAND', category: 'Mathematik', signature: 'ZUFALLSZAHL()', desc: 'Zufallszahl zwischen 0 und 1.' }, () => Math.random());
add({ de: 'ZUFALLSBEREICH', en: 'RANDBETWEEN', category: 'Mathematik', signature: 'ZUFALLSBEREICH(Unten; Oben)', desc: 'Ganze Zufallszahl im Bereich.' }, (args, ctx) => {
  const a = evalNum(ctx, args[0]);
  const b = evalNum(ctx, args[1]);
  if (isErr(a) || isErr(b)) return isErr(a) ? a : b;
  const lo = Math.ceil(Math.min(a, b));
  const hi = Math.floor(Math.max(a, b));
  return lo + Math.floor(Math.random() * (hi - lo + 1));
});
add({ de: 'PI', en: 'PI', category: 'Mathematik', signature: 'PI()', desc: 'Kreiszahl π.' }, () => Math.PI);
add({ de: 'BOGENMASS', en: 'RADIANS', category: 'Mathematik', signature: 'BOGENMASS(Grad)', desc: 'Grad in Bogenmaß.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  return isErr(n) ? n : (n * Math.PI) / 180;
});
add({ de: 'GRAD', en: 'DEGREES', category: 'Mathematik', signature: 'GRAD(Bogenmaß)', desc: 'Bogenmaß in Grad.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  return isErr(n) ? n : (n * 180) / Math.PI;
});
add({ de: 'SIN', en: 'SIN', category: 'Mathematik', signature: 'SIN(Zahl)', desc: 'Sinus (Bogenmaß).' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  return isErr(n) ? n : Math.sin(n);
});
add({ de: 'COS', en: 'COS', category: 'Mathematik', signature: 'COS(Zahl)', desc: 'Kosinus.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  return isErr(n) ? n : Math.cos(n);
});
add({ de: 'TAN', en: 'TAN', category: 'Mathematik', signature: 'TAN(Zahl)', desc: 'Tangens.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  return isErr(n) ? n : Math.tan(n);
});
add({ de: 'SINHYP', en: 'SINH', category: 'Mathematik', signature: 'SINHYP(Zahl)', desc: 'Hyperbelsinus.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  return isErr(n) ? n : Math.sinh(n);
});
add({ de: 'COSHYP', en: 'COSH', category: 'Mathematik', signature: 'COSHYP(Zahl)', desc: 'Hyperbelkosinus.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  return isErr(n) ? n : Math.cosh(n);
});
add({ de: 'TANHYP', en: 'TANH', category: 'Mathematik', signature: 'TANHYP(Zahl)', desc: 'Hyperbeltangens.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  return isErr(n) ? n : Math.tanh(n);
});
add({ de: 'LN', en: 'LN', category: 'Mathematik', signature: 'LN(Zahl)', desc: 'Natürlicher Logarithmus.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  if (isErr(n)) return n;
  if (n <= 0) return ZAHL();
  return Math.log(n);
});
add({ de: 'LOG', en: 'LOG', category: 'Mathematik', signature: 'LOG(Zahl; [Basis])', desc: 'Logarithmus.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const b = args[1] ? evalNum(ctx, args[1]) : 10;
  if (isErr(n) || isErr(b)) return isErr(n) ? n : b;
  if (n <= 0 || b <= 0 || b === 1) return ZAHL();
  return Math.log(n) / Math.log(b);
});
add({ de: 'LOG10', en: 'LOG10', category: 'Mathematik', signature: 'LOG10(Zahl)', desc: 'Zehnerlogarithmus.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  if (isErr(n)) return n;
  if (n <= 0) return ZAHL();
  return Math.log10(n);
});
add({ de: 'EXP', en: 'EXP', category: 'Mathematik', signature: 'EXP(Zahl)', desc: 'e hoch Zahl.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  return isErr(n) ? n : Math.exp(n);
});
add({ de: 'GGT', en: 'GCD', category: 'Mathematik', signature: 'GGT(Zahl1; …)', desc: 'Größter gemeinsamer Teiler.' }, (args, ctx) => {
  const xs = collectNums(ctx, args, true);
  if (isErr(xs) || !xs.length) return isErr(xs) ? xs : WERT();
  return xs.reduce((a, b) => gcd2(a, b));
});
add({ de: 'KGV', en: 'LCM', category: 'Mathematik', signature: 'KGV(Zahl1; …)', desc: 'Kleinstes gemeinsames Vielfaches.' }, (args, ctx) => {
  const xs = collectNums(ctx, args, true);
  if (isErr(xs) || !xs.length) return isErr(xs) ? xs : WERT();
  return xs.reduce((a, b) => {
    const g = gcd2(a, b);
    return g === 0 ? 0 : Math.abs(a * b) / g;
  });
});
add({ de: 'KOMBINATIONEN', en: 'COMBIN', category: 'Mathematik', signature: 'KOMBINATIONEN(n; k)', desc: 'Binomialkoeffizient.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const k = evalNum(ctx, args[1]);
  if (isErr(n) || isErr(k)) return isErr(n) ? n : k;
  const nn = Math.trunc(n);
  const kk = Math.trunc(k);
  if (kk < 0 || nn < 0 || kk > nn) return ZAHL();
  let r = 1;
  for (let i = 1; i <= kk; i++) r = (r * (nn - kk + i)) / i;
  return r;
});
add({ de: 'QUOTIENT', en: 'QUOTIENT', category: 'Mathematik', signature: 'QUOTIENT(Zähler; Nenner)', desc: 'Ganzzahliger Anteil der Division.' }, (args, ctx) => {
  const a = evalNum(ctx, args[0]);
  const b = evalNum(ctx, args[1]);
  if (isErr(a) || isErr(b)) return isErr(a) ? a : b;
  if (b === 0) return DIV0();
  return Math.trunc(a / b);
});
add({ de: 'OBERGRENZE', en: 'CEILING', category: 'Mathematik', signature: 'OBERGRENZE(Zahl; Schritt)', desc: 'Aufrunden auf ein Vielfaches.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const s = evalNum(ctx, args[1]);
  if (isErr(n) || isErr(s)) return isErr(n) ? n : s;
  if (s === 0) return 0;
  if (n * s < 0) return ZAHL();
  return Math.ceil(n / s - 1e-12) * s;
});
add({ de: 'UNTERGRENZE', en: 'FLOOR', category: 'Mathematik', signature: 'UNTERGRENZE(Zahl; Schritt)', desc: 'Abrunden auf ein Vielfaches.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const s = evalNum(ctx, args[1]);
  if (isErr(n) || isErr(s)) return isErr(n) ? n : s;
  if (s === 0) return 0;
  if (n * s < 0) return ZAHL();
  return Math.floor(n / s + 1e-12) * s;
});

add({ de: 'MITTELWERT', en: 'AVERAGE', category: 'Statistik', signature: 'MITTELWERT(Zahl1; …)', desc: 'Arithmetisches Mittel.' }, (args, ctx) => {
  const xs = collectNums(ctx, args);
  if (isErr(xs)) return xs;
  return avg(xs);
});
add({ de: 'MEDIAN', en: 'MEDIAN', category: 'Statistik', signature: 'MEDIAN(Zahl1; …)', desc: 'Median.' }, (args, ctx) => {
  const xs = collectNums(ctx, args);
  if (isErr(xs) || !xs.length) return isErr(xs) ? xs : ZAHL();
  return percentile(xs, 0.5);
});
add({ de: 'MIN', en: 'MIN', category: 'Statistik', signature: 'MIN(Zahl1; …)', desc: 'Kleinster Wert.' }, (args, ctx) => {
  const xs = collectNums(ctx, args);
  if (isErr(xs) || !xs.length) return isErr(xs) ? xs : 0;
  return Math.min(...xs);
});
add({ de: 'MAX', en: 'MAX', category: 'Statistik', signature: 'MAX(Zahl1; …)', desc: 'Größter Wert.' }, (args, ctx) => {
  const xs = collectNums(ctx, args);
  if (isErr(xs) || !xs.length) return isErr(xs) ? xs : 0;
  return Math.max(...xs);
});
add({ de: 'ANZAHL', en: 'COUNT', category: 'Statistik', signature: 'ANZAHL(Wert1; …)', desc: 'Zählt Zahlen.' }, (args, ctx) => {
  const xs = collectNums(ctx, args);
  return isErr(xs) ? xs : xs.length;
});
add({ de: 'ANZAHL2', en: 'COUNTA', category: 'Statistik', signature: 'ANZAHL2(Wert1; …)', desc: 'Zählt nichtleere Zellen.' }, (args, ctx) => {
  let n = 0;
  for (const a of args) {
    const v = ctx.eval(a);
    const f = flat(v);
    if (isErr(f)) return f;
    n += f.filter((c) => c !== null && c !== '').length;
  }
  return n;
});
add({ de: 'ANZAHLLEEREZELLEN', en: 'COUNTBLANK', category: 'Statistik', signature: 'ANZAHLLEEREZELLEN(Bereich)', desc: 'Zählt leere Zellen.' }, (args, ctx) => {
  const m = ctx.rangeOf(args[0]);
  if (isErr(m)) return m;
  let n = 0;
  for (const row of m.values) for (const c of row) if (c === null || c === '') n++;
  return n;
});
add({ de: 'STABW', en: 'STDEV', category: 'Statistik', signature: 'STABW(Zahl1; …)', desc: 'Standardabweichung einer Stichprobe.' }, (args, ctx) => {
  const xs = collectNums(ctx, args);
  if (isErr(xs)) return xs;
  return stdev(xs, false);
}, ['STABW.S', 'STDEV.S']);
add({ de: 'STABWN', en: 'STDEVP', category: 'Statistik', signature: 'STABWN(Zahl1; …)', desc: 'Standardabweichung der Grundgesamtheit.' }, (args, ctx) => {
  const xs = collectNums(ctx, args);
  if (isErr(xs)) return xs;
  return stdev(xs, true);
}, ['STABW.N', 'STDEV.P']);
add({ de: 'VARIANZ', en: 'VAR', category: 'Statistik', signature: 'VARIANZ(Zahl1; …)', desc: 'Varianz einer Stichprobe.' }, (args, ctx) => {
  const xs = collectNums(ctx, args);
  if (isErr(xs)) return xs;
  return variance(xs, false);
}, ['VAR.S']);
add({ de: 'VARIANZEN', en: 'VARP', category: 'Statistik', signature: 'VARIANZEN(Zahl1; …)', desc: 'Varianz der Grundgesamtheit.' }, (args, ctx) => {
  const xs = collectNums(ctx, args);
  if (isErr(xs)) return xs;
  return variance(xs, true);
}, ['VAR.P']);
add({ de: 'QUANTIL', en: 'PERCENTILE', category: 'Statistik', signature: 'QUANTIL(Bereich; k)', desc: 'Quantil zwischen 0 und 1.' }, (args, ctx) => {
  const xs = numbers(ctx.eval(args[0]));
  const p = evalNum(ctx, args[1]);
  if (isErr(xs) || isErr(p)) return isErr(xs) ? xs : p;
  return percentile(xs, p);
});
add({ de: 'RANG', en: 'RANK', category: 'Statistik', signature: 'RANG(Zahl; Bezug; [Ordnung])', desc: 'Rang einer Zahl. Ordnung 0 = absteigend.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const xs = numbers(ctx.eval(args[1]));
  const order = args[2] ? evalNum(ctx, args[2]) : 0;
  if (isErr(n) || isErr(xs) || isErr(order)) return isErr(n) ? n : isErr(xs) ? xs : order;
  const sorted = [...xs].sort((a, b) => (order ? a - b : b - a));
  const i = sorted.findIndex((x) => Math.abs(x - n) <= 1e-9 * Math.max(1, Math.abs(n)));
  return i < 0 ? NV() : i + 1;
});
add({ de: 'KGRÖSSTE', en: 'LARGE', category: 'Statistik', signature: 'KGRÖSSTE(Bereich; k)', desc: 'k-größter Wert.' }, (args, ctx) => {
  const xs = numbers(ctx.eval(args[0]));
  const k = evalNum(ctx, args[1]);
  if (isErr(xs) || isErr(k)) return isErr(xs) ? xs : k;
  const s = [...xs].sort((a, b) => b - a);
  const i = Math.trunc(k) - 1;
  if (i < 0 || i >= s.length) return ZAHL();
  return s[i];
});
add({ de: 'KKLEINSTE', en: 'SMALL', category: 'Statistik', signature: 'KKLEINSTE(Bereich; k)', desc: 'k-kleinster Wert.' }, (args, ctx) => {
  const xs = numbers(ctx.eval(args[0]));
  const k = evalNum(ctx, args[1]);
  if (isErr(xs) || isErr(k)) return isErr(xs) ? xs : k;
  const s = [...xs].sort((a, b) => a - b);
  const i = Math.trunc(k) - 1;
  if (i < 0 || i >= s.length) return ZAHL();
  return s[i];
});
add({ de: 'RGP', en: 'LINEST', category: 'Statistik', signature: 'RGP(Y; [X])', desc: 'Lineare Regression: Steigung und Achsenabschnitt.' }, (args, ctx) => {
  const y = numbers(ctx.eval(args[0]));
  if (isErr(y) || y.length < 2) return isErr(y) ? y : ZAHL();
  let x: number[];
  if (args[1]) {
    const xx = numbers(ctx.eval(args[1]));
    if (isErr(xx)) return xx;
    x = xx;
  } else x = y.map((_, i) => i + 1);
  const n = Math.min(x.length, y.length);
  let sx = 0, sy = 0, sxy = 0, sx2 = 0;
  for (let i = 0; i < n; i++) {
    sx += x[i];
    sy += y[i];
    sxy += x[i] * y[i];
    sx2 += x[i] * x[i];
  }
  const den = n * sx2 - sx * sx;
  if (Math.abs(den) < 1e-12) return ZAHL();
  const slope = (n * sxy - sx * sy) / den;
  const intercept = (sy - slope * sx) / n;
  return mat([[slope, intercept]]);
});

function aggIf(kind: 'sum' | 'count' | 'avg' | 'max' | 'min', args: Expr[], ctx: FnCtx): Value {
  const range = ctx.rangeOf(args[0]);
  if (isErr(range)) return range;
  const crit = criteriaScalar(ctx, args[1]);
  if (isErr(crit)) return crit;
  const sumRange = args[2] ? ctx.rangeOf(args[2]) : undefined;
  if (sumRange && isErr(sumRange)) return sumRange;
  const hit = rectMatch(range, crit, sumRange && !isErr(sumRange) ? sumRange : undefined);
  if (isErr(hit)) return hit;
  if (kind === 'sum') return hit.sum;
  if (kind === 'count') return kind === 'count' ? countMatches(range, crit) : hit.count;
  if (kind === 'avg') return hit.nums.length ? hit.sum / hit.nums.length : DIV0();
  if (!hit.nums.length) return 0;
  return kind === 'max' ? Math.max(...hit.nums) : Math.min(...hit.nums);
}
function countMatches(range: Matrix, crit: Scalar): number | FError {
  let n = 0;
  for (const row of range.values) {
    for (const c of row) {
      if (isErr(c)) return c;
      if (matchCriteria(c, crit)) n++;
    }
  }
  return n;
}
add({ de: 'SUMMEWENN', en: 'SUMIF', category: 'Statistik', signature: 'SUMMEWENN(Bereich; Kriterium; [Summe_Bereich])', desc: 'Summe der Werte, die ein Kriterium erfüllen.' }, (args, ctx) => aggIf('sum', args, ctx));
add({ de: 'ZÄHLENWENN', en: 'COUNTIF', category: 'Statistik', signature: 'ZÄHLENWENN(Bereich; Kriterium)', desc: 'Zählt Zellen, die ein Kriterium erfüllen.' }, (args, ctx) => {
  const range = ctx.rangeOf(args[0]);
  if (isErr(range)) return range;
  const crit = criteriaScalar(ctx, args[1]);
  if (isErr(crit)) return crit;
  return countMatches(range, crit);
});
add({ de: 'MITTELWERTWENN', en: 'AVERAGEIF', category: 'Statistik', signature: 'MITTELWERTWENN(Bereich; Kriterium; [Mittelwert_Bereich])', desc: 'Mittelwert mit Kriterium.' }, (args, ctx) => aggIf('avg', args, ctx));
add({ de: 'MAXWENNS', en: 'MAXIFS', category: 'Statistik', signature: 'MAXWENNS(Max_Bereich; Bereich; Kriterium; …)', desc: 'Maximum mit mehreren Kriterien.' }, (args, ctx) => multiIf('max', args, ctx));
add({ de: 'MINWENNS', en: 'MINIFS', category: 'Statistik', signature: 'MINWENNS(Min_Bereich; Bereich; Kriterium; …)', desc: 'Minimum mit mehreren Kriterien.' }, (args, ctx) => multiIf('min', args, ctx));
add({ de: 'SUMMEWENNS', en: 'SUMIFS', category: 'Statistik', signature: 'SUMMEWENNS(Summe_Bereich; Bereich; Kriterium; …)', desc: 'Summe mit mehreren Kriterien.' }, (args, ctx) => multiIf('sum', args, ctx));
add({ de: 'ZÄHLENWENNS', en: 'COUNTIFS', category: 'Statistik', signature: 'ZÄHLENWENNS(Bereich; Kriterium; …)', desc: 'Anzahl mit mehreren Kriterien.' }, (args, ctx) => multiIf('count', args, ctx));
add({ de: 'MITTELWERTWENNS', en: 'AVERAGEIFS', category: 'Statistik', signature: 'MITTELWERTWENNS(Bereich; Kriterium_Bereich; Kriterium; …)', desc: 'Mittelwert mit mehreren Kriterien.' }, (args, ctx) => multiIf('avg', args, ctx));

function multiIf(kind: 'sum' | 'count' | 'avg' | 'max' | 'min', args: Expr[], ctx: FnCtx): Value {
  if (args.length < 2) return WERT();
  const valueRange = ctx.rangeOf(args[0]);
  if (isErr(valueRange)) return valueRange;
  const pairs: { range: Matrix; crit: Scalar }[] = [];
  const start = kind === 'count' ? 0 : 1;
  if ((args.length - start) % 2 !== 0) return WERT();
  for (let i = start; i < args.length; i += 2) {
    const range = ctx.rangeOf(args[i]);
    if (isErr(range)) return range;
    const crit = criteriaScalar(ctx, args[i + 1]);
    if (isErr(crit)) return crit;
    pairs.push({ range, crit });
  }
  const h = valueRange.values.length;
  const w = valueRange.values[0]?.length ?? 0;
  const nums: number[] = [];
  let matches = 0;
  for (let r = 0; r < h; r++) {
    for (let c = 0; c < w; c++) {
      let ok = true;
      for (const p of pairs) {
        const cell = p.range.values[r]?.[c];
        if (cell === undefined) {
          ok = false;
          break;
        }
        if (isErr(cell)) return cell;
        if (!matchCriteria(cell, p.crit)) {
          ok = false;
          break;
        }
      }
      if (!ok) continue;
      matches++;
      const v = valueRange.values[r][c];
      if (isErr(v)) return v;
      if (typeof v === 'number') nums.push(v);
    }
  }
  if (kind === 'count') return matches;
  if (kind === 'sum') return nums.reduce((a, b) => a + b, 0);
  if (kind === 'avg') return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : DIV0();
  if (!nums.length) return 0;
  return kind === 'max' ? Math.max(...nums) : Math.min(...nums);
}

add({ de: 'TEILERGEBNIS', en: 'SUBTOTAL', category: 'Statistik', signature: 'TEILERGEBNIS(Funktion; Bereich; …)', desc: 'Aggregation, die gefilterte Zeilen auslässt. 9 = Summe.' }, (args, ctx) => {
  const code = evalNum(ctx, args[0]);
  if (isErr(code)) return code;
  const fn = Math.trunc(code);
  const base = fn > 100 ? fn - 100 : fn;
  const addr0 = ctx.addressOf(args[1]);
  const nums: number[] = [];
  const all: CellVal[] = [];
  for (let i = 1; i < args.length; i++) {
    const addr = ctx.addressOf(args[i]);
    const m = ctx.rangeOf(args[i]);
    if (isErr(m)) return m;
    for (let r = 0; r < m.values.length; r++) {
      const absR = addr ? addr.r1 + r : -1;
      if (addr && ctx.hidden(addr.sheet, absR)) continue;
      if (addr && fn > 100 && ctx.hidden(addr.sheet, absR)) continue;
      for (let c = 0; c < m.values[r].length; c++) {
        if (addr) {
          const raw = ctx.raw(addr.sheet, absR, addr.c1 + c);
          if (/^=\s*(TEILERGEBNIS|SUBTOTAL)\s*\(/i.test(raw)) continue;
        }
        const v = m.values[r][c];
        if (isErr(v)) return v;
        all.push(v);
        if (typeof v === 'number') nums.push(v);
      }
    }
  }
  void addr0;
  switch (base) {
    case 1:
      return avg(nums);
    case 2:
      return nums.length;
    case 3:
      return all.filter((v) => v !== null && v !== '').length;
    case 4:
      return nums.length ? Math.max(...nums) : 0;
    case 5:
      return nums.length ? Math.min(...nums) : 0;
    case 6:
      return nums.length ? nums.reduce((a, b) => a * b, 1) : 0;
    case 7:
      return stdev(nums, false);
    case 8:
      return stdev(nums, true);
    case 9:
      return nums.reduce((a, b) => a + b, 0);
    case 10:
      return variance(nums, false);
    case 11:
      return variance(nums, true);
    default:
      return WERT();
  }
});

add({ de: 'WENN', en: 'IF', category: 'Logik', signature: 'WENN(Prüfung; Dann; [Sonst])', desc: 'Fallunterscheidung.' }, (args, ctx) => {
  const c = truth(ctx.eval(args[0]));
  if (isErr(c)) return c;
  if (c) return args[1] ? ctx.eval(args[1]) : true;
  return args[2] ? ctx.eval(args[2]) : false;
});
add({ de: 'WENNS', en: 'IFS', category: 'Logik', signature: 'WENNS(Prüfung1; Wert1; …)', desc: 'Mehrere Bedingungen der Reihe nach.' }, (args, ctx) => ifsPairs(args, ctx));
add({ de: 'WENNFEHLER', en: 'IFERROR', category: 'Logik', signature: 'WENNFEHLER(Wert; Wert_falls_Fehler)', desc: 'Ersatzwert, wenn die Formel einen Fehler liefert.' }, (args, ctx) => {
  const v = ctx.eval(args[0]);
  if (isErr(v)) return args[1] ? ctx.eval(args[1]) : '';
  return v;
});
add({ de: 'WENNNV', en: 'IFNA', category: 'Logik', signature: 'WENNNV(Wert; Wert_falls_NV)', desc: 'Ersatzwert nur bei #NV.' }, (args, ctx) => {
  const v = ctx.eval(args[0]);
  if (isErr(v) && v.code === '#NV') return args[1] ? ctx.eval(args[1]) : '';
  return v;
});
add({ de: 'UND', en: 'AND', category: 'Logik', signature: 'UND(Wahrheitswert1; …)', desc: 'Wahr, wenn alle Argumente wahr sind.' }, (args, ctx) => logicFold(args, ctx, 'and'));
add({ de: 'ODER', en: 'OR', category: 'Logik', signature: 'ODER(Wahrheitswert1; …)', desc: 'Wahr, wenn mindestens ein Argument wahr ist.' }, (args, ctx) => logicFold(args, ctx, 'or'));
add({ de: 'XODER', en: 'XOR', category: 'Logik', signature: 'XODER(Wahrheitswert1; …)', desc: 'Exklusives Oder.' }, (args, ctx) => logicFold(args, ctx, 'xor'));
add({ de: 'NICHT', en: 'NOT', category: 'Logik', signature: 'NICHT(Wahrheitswert)', desc: 'Verneint einen Wahrheitswert.' }, (args, ctx) => {
  const v = truth(ctx.eval(args[0]));
  return isErr(v) ? v : !v;
});
add({ de: 'WAHR', en: 'TRUE', category: 'Logik', signature: 'WAHR()', desc: 'Der Wahrheitswert WAHR.' }, () => true);
add({ de: 'FALSCH', en: 'FALSE', category: 'Logik', signature: 'FALSCH()', desc: 'Der Wahrheitswert FALSCH.' }, () => false);
add({ de: 'WAHL', en: 'CHOOSE', category: 'Logik', signature: 'WAHL(Index; Wert1; …)', desc: 'Wählt einen Wert anhand eines Index.' }, (args, ctx) => {
  const i = evalNum(ctx, args[0]);
  if (isErr(i)) return i;
  const k = Math.trunc(i);
  if (k < 1 || k >= args.length) return WERT();
  return ctx.eval(args[k]);
});
add({ de: 'ERSTERWERT', en: 'SWITCH', category: 'Logik', signature: 'ERSTERWERT(Ausdruck; Wert1; Ergebnis1; …; [Standard])', desc: 'Vergleicht einen Ausdruck mit einer Liste.' }, (args, ctx) => {
  if (args.length < 3) return WERT();
  const base = ctx.eval(args[0]);
  if (isErr(base)) return base;
  const b = scalar(base);
  if (isErr(b)) return b;
  for (let i = 1; i + 1 < args.length; i += 2) {
    const key = scalar(ctx.eval(args[i]));
    if (isErr(key)) return key;
    if (matchCriteria(b, key) || b === key) return ctx.eval(args[i + 1]);
  }
  if (args.length % 2 === 0) return ctx.eval(args[args.length - 1]);
  return NV();
});
add({ de: 'LET', en: 'LET', category: 'Logik', signature: 'LET(Name; Wert; …; Berechnung)', desc: 'Benennt Zwischenergebnisse innerhalb einer Formel.' }, (args, ctx) => {
  if (args.length < 3 || args.length % 2 === 0) return WERT();
  const mark = ctx.localMark();
  try {
    for (let i = 0; i < args.length - 1; i += 2) {
      const name = args[i];
      if (name.type !== 'name') return NAME();
      const v = ctx.eval(args[i + 1]);
      if (isErr(v)) return v;
      ctx.setLocal(name.name, v);
    }
    return ctx.eval(args[args.length - 1]);
  } finally {
    ctx.restoreLocals(mark);
  }
});
add({ de: 'LAMBDA', en: 'LAMBDA', category: 'Logik', signature: 'LAMBDA(Parameter…; Berechnung)', desc: 'Eigene Funktion. Aufruf: LAMBDA(x; x*2)(5) oder als Name.' }, (args, ctx) => {
  if (args.length < 2) return WERT();
  const params: string[] = [];
  for (const a of args.slice(0, -1)) {
    if (a.type !== 'name') return NAME();
    params.push(a.name);
  }
  return new LambdaVal(params, args[args.length - 1], ctx.sheet);
});
add({ de: 'MAP', en: 'MAP', category: 'Dynamisch', signature: 'MAP(Matrix; LAMBDA)', desc: 'Wendet eine LAMBDA-Funktion auf jedes Element an.' }, (args, ctx) => {
  const m = ctx.rangeOf(args[0]);
  if (isErr(m)) return m;
  const lam = ctx.eval(args[1]);
  if (!isLambda(lam)) return WERT();
  const values: CellVal[][] = [];
  for (const row of m.values) {
    const out: CellVal[] = [];
    for (const c of row) {
      const r = ctx.callLambda(lam, [isErr(c) ? c : c]);
      if (isMatrix(r) || isLambda(r) || isSpark(r) || isLink(r)) return WERT();
      out.push(isErr(r) ? r : (r as Scalar));
    }
    values.push(out);
  }
  return mat(values);
});

function logicFold(args: Expr[], ctx: FnCtx, kind: 'and' | 'or' | 'xor'): Value {
  const vals: boolean[] = [];
  const take = (v: Value): FError | null => {
    if (isErr(v)) return v;
    if (isMatrix(v)) {
      for (const row of v.values) for (const c of row) {
        const e = take(c);
        if (e) return e;
      }
      return null;
    }
    if (typeof v === 'boolean') vals.push(v);
    else if (typeof v === 'number') vals.push(v !== 0);
    else if (typeof v === 'string') {
      if (/^(wahr|true)$/i.test(v)) vals.push(true);
      else if (/^(falsch|false)$/i.test(v)) vals.push(false);
    }
    return null;
  };
  for (const a of args) {
    const e = take(ctx.eval(a));
    if (e) return e;
  }
  if (!vals.length) return WERT();
  if (kind === 'and') return vals.every(Boolean);
  if (kind === 'or') return vals.some(Boolean);
  return vals.filter(Boolean).length % 2 === 1;
}

add({ de: 'LINKS', en: 'LEFT', category: 'Text', signature: 'LINKS(Text; [Anzahl])', desc: 'Linke Zeichen.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  const n = args[1] ? evalNum(ctx, args[1]) : 1;
  if (isErr(t) || isErr(n)) return isErr(t) ? t : n;
  return [...t].slice(0, Math.max(0, Math.trunc(n))).join('');
});
add({ de: 'RECHTS', en: 'RIGHT', category: 'Text', signature: 'RECHTS(Text; [Anzahl])', desc: 'Rechte Zeichen.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  const n = args[1] ? evalNum(ctx, args[1]) : 1;
  if (isErr(t) || isErr(n)) return isErr(t) ? t : n;
  const chars = [...t];
  return chars.slice(Math.max(0, chars.length - Math.trunc(n))).join('');
});
add({ de: 'TEIL', en: 'MID', category: 'Text', signature: 'TEIL(Text; Beginn; Anzahl)', desc: 'Zeichen ab einer Position (1-basiert).' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  const start = evalNum(ctx, args[1]);
  const len = evalNum(ctx, args[2]);
  if (isErr(t) || isErr(start) || isErr(len)) return isErr(t) ? t : isErr(start) ? start : len;
  if (start < 1) return WERT();
  return [...t].slice(Math.trunc(start) - 1, Math.trunc(start) - 1 + Math.trunc(len)).join('');
});
add({ de: 'LÄNGE', en: 'LEN', category: 'Text', signature: 'LÄNGE(Text)', desc: 'Anzahl der Zeichen.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  return isErr(t) ? t : [...t].length;
});
add({ de: 'GLÄTTEN', en: 'TRIM', category: 'Text', signature: 'GLÄTTEN(Text)', desc: 'Überflüssige Leerzeichen entfernen.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  return isErr(t) ? t : t.trim().replace(/\s+/g, ' ');
});
add({ de: 'SÄUBERN', en: 'CLEAN', category: 'Text', signature: 'SÄUBERN(Text)', desc: 'Nicht druckbare Zeichen entfernen.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  return isErr(t) ? t : [...t].filter((ch) => ch.charCodeAt(0) >= 32).join('');
});
add({ de: 'GROSS', en: 'UPPER', category: 'Text', signature: 'GROSS(Text)', desc: 'In Großbuchstaben.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  return isErr(t) ? t : t.toLocaleUpperCase('de-DE');
});
add({ de: 'KLEIN', en: 'LOWER', category: 'Text', signature: 'KLEIN(Text)', desc: 'In Kleinbuchstaben.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  return isErr(t) ? t : t.toLocaleLowerCase('de-DE');
});
add({ de: 'GROSS2', en: 'PROPER', category: 'Text', signature: 'GROSS2(Text)', desc: 'Ersten Buchstaben jedes Worts groß.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  if (isErr(t)) return t;
  return t.toLocaleLowerCase('de-DE').replace(/\p{L}+/gu, (w) => w.charAt(0).toLocaleUpperCase('de-DE') + w.slice(1));
});
add({ de: 'TEXTKETTE', en: 'CONCAT', category: 'Text', signature: 'TEXTKETTE(Text1; …)', desc: 'Texte aneinanderfügen.' }, (args, ctx) => joinText(args, ctx, '', false));
add({ de: 'VERKETTEN', en: 'CONCATENATE', category: 'Text', signature: 'VERKETTEN(Text1; …)', desc: 'Texte aneinanderfügen.' }, (args, ctx) => joinText(args, ctx, '', false));
add({ de: 'TEXTVERBINDEN', en: 'TEXTJOIN', category: 'Text', signature: 'TEXTVERBINDEN(Trennzeichen; Leer_ignorieren; Text1; …)', desc: 'Texte mit Trennzeichen verbinden.' }, (args, ctx) => {
  const d = text(ctx.eval(args[0]));
  const ign = truth(ctx.eval(args[1]));
  if (isErr(d) || isErr(ign)) return isErr(d) ? d : ign;
  return joinText(args.slice(2), ctx, d, ign);
});
function joinText(args: Expr[], ctx: FnCtx, delim: string, ignore: boolean): Value {
  const parts: string[] = [];
  for (const a of args) {
    const v = ctx.eval(a);
    const f = flat(v);
    if (isErr(f)) return f;
    for (const c of f) {
      if ((c === null || c === '') && ignore) continue;
      const tx = text(c);
      if (isErr(tx)) return tx;
      parts.push(tx);
    }
  }
  return parts.join(delim);
}
add({ de: 'FINDEN', en: 'FIND', category: 'Text', signature: 'FINDEN(Suchtext; Text; [Beginn])', desc: 'Sucht exakt, Groß/Klein zählt. Position ab 1.' }, (args, ctx) => findText(args, ctx, true));
add({ de: 'SUCHEN', en: 'SEARCH', category: 'Text', signature: 'SUCHEN(Suchtext; Text; [Beginn])', desc: 'Sucht ohne Groß/Klein und mit Platzhaltern.' }, (args, ctx) => findText(args, ctx, false));
function findText(args: Expr[], ctx: FnCtx, cs: boolean): Value {
  const needle = text(ctx.eval(args[0]));
  const hay = text(ctx.eval(args[1]));
  const start = args[2] ? evalNum(ctx, args[2]) : 1;
  if (isErr(needle) || isErr(hay) || isErr(start)) return isErr(needle) ? needle : isErr(hay) ? hay : start;
  const from = Math.max(1, Math.trunc(start)) - 1;
  const h = [...hay];
  const slice = h.slice(from).join('');
  if (!cs && /[*?]/.test(needle)) {
    const pat = needle.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.');
    const m = new RegExp(pat, 'i').exec(slice);
    return m ? from + [...slice.slice(0, m.index)].length + 1 : WERT();
  }
  const idx = cs ? slice.indexOf(needle) : slice.toLocaleLowerCase('de-DE').indexOf(needle.toLocaleLowerCase('de-DE'));
  if (idx < 0) return WERT();
  return from + [...slice.slice(0, idx)].length + 1;
}
add({ de: 'ERSETZEN', en: 'REPLACE', category: 'Text', signature: 'ERSETZEN(Text; Beginn; Anzahl; Neu)', desc: 'Ersetzt einen Abschnitt nach Position.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  const start = evalNum(ctx, args[1]);
  const len = evalNum(ctx, args[2]);
  const neu = text(ctx.eval(args[3]));
  if (isErr(t) || isErr(start) || isErr(len) || isErr(neu)) return isErr(t) ? t : isErr(start) ? start : isErr(len) ? len : neu;
  const chars = [...t];
  const i = Math.trunc(start) - 1;
  chars.splice(i, Math.max(0, Math.trunc(len)), neu);
  return chars.join('');
});
add({ de: 'WECHSELN', en: 'SUBSTITUTE', category: 'Text', signature: 'WECHSELN(Text; Alt; Neu; [Instanz])', desc: 'Ersetzt Text durch Text.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  const old = text(ctx.eval(args[1]));
  const neu = text(ctx.eval(args[2]));
  const inst = args[3] ? evalNum(ctx, args[3]) : 0;
  if (isErr(t) || isErr(old) || isErr(neu) || isErr(inst)) return isErr(t) ? t : isErr(old) ? old : isErr(neu) ? neu : inst;
  if (!old) return t;
  if (!inst) return t.split(old).join(neu);
  let seen = 0;
  let out = '';
  let i = 0;
  while (i < t.length) {
    if (t.startsWith(old, i)) {
      seen++;
      if (seen === Math.trunc(inst)) {
        out += neu;
        i += old.length;
        continue;
      }
    }
    out += t[i++];
  }
  return out;
});
add({ de: 'WIEDERHOLEN', en: 'REPT', category: 'Text', signature: 'WIEDERHOLEN(Text; Anzahl)', desc: 'Text wiederholen.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  const n = evalNum(ctx, args[1]);
  if (isErr(t) || isErr(n)) return isErr(t) ? t : n;
  const k = Math.trunc(n);
  if (k < 0 || t.length * k > 20000) return WERT();
  return t.repeat(k);
});
add({ de: 'TEXT', en: 'TEXT', category: 'Text', signature: 'TEXT(Wert; Format)', desc: 'Formatiert eine Zahl oder ein Datum als Text.' }, (args, ctx) => {
  const v = ctx.eval(args[0]);
  const fmt = text(ctx.eval(args[1]));
  if (isErr(v) || isErr(fmt)) return isErr(v) ? v : fmt;
  const n = num(v, NaN);
  if (isErr(n)) return text(v);
  const f = fmt.toUpperCase();
  if (f.includes('T') || f.includes('J') || f.includes('M') && f.includes('D')) return formatDate(n);
  if (f.includes('%')) return formatNumber(n * 100, (f.split('0').length > 2 ? f.split(',')[1]?.replace(/\D/g, '').length : 0) || 0, false) + ' %';
  const dec = f.includes(',') ? (f.split(',')[1]?.replace(/\D/g, '').length ?? 0) : 0;
  return formatNumber(n, dec, f.includes('.') || f.includes('#'));
});
add({ de: 'WERT', en: 'VALUE', category: 'Text', signature: 'WERT(Text)', desc: 'Wandelt Text in eine Zahl oder ein Datum.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  if (isErr(t)) return t;
  const lit = parseLiteral(t);
  return typeof lit === 'number' ? lit : WERT();
});
add({ de: 'FEST', en: 'FIXED', category: 'Text', signature: 'FEST(Zahl; [Dezimalen]; [Keine_Tsd])', desc: 'Zahl als formatierten Text.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const d = args[1] ? evalNum(ctx, args[1]) : 2;
  const no = args[2] ? truth(ctx.eval(args[2])) : false;
  if (isErr(n) || isErr(d) || isErr(no)) return isErr(n) ? n : isErr(d) ? d : no;
  return formatNumber(n, Math.max(0, Math.trunc(d)), !no);
});
add({ de: 'IDENTISCH', en: 'EXACT', category: 'Text', signature: 'IDENTISCH(Text1; Text2)', desc: 'Vergleicht Texte unter Beachtung der Groß-/Kleinschreibung.' }, (args, ctx) => {
  const a = text(ctx.eval(args[0]));
  const b = text(ctx.eval(args[1]));
  if (isErr(a) || isErr(b)) return isErr(a) ? a : b;
  return a === b;
});
add({ de: 'CODE', en: 'CODE', category: 'Text', signature: 'CODE(Text)', desc: 'Zeichencode des ersten Zeichens.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  if (isErr(t) || !t) return isErr(t) ? t : WERT();
  return t.codePointAt(0) ?? WERT();
});
add({ de: 'ZEICHEN', en: 'CHAR', category: 'Text', signature: 'ZEICHEN(Code)', desc: 'Zeichen zu einem Zeichencode.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  if (isErr(n)) return n;
  const c = Math.trunc(n);
  if (c < 1 || c > 1114111) return ZAHL();
  return String.fromCodePoint(c);
});

add({ de: 'HEUTE', en: 'TODAY', category: 'Datum', signature: 'HEUTE()', desc: 'Heutiges Datum als Seriennummer.' }, () => {
  const d = new Date();
  return dateToSerial(d.getFullYear(), d.getMonth() + 1, d.getDate());
});
add({ de: 'JETZT', en: 'NOW', category: 'Datum', signature: 'JETZT()', desc: 'Datum und Uhrzeit als Seriennummer.' }, () => {
  const d = new Date();
  return dateToSerial(d.getFullYear(), d.getMonth() + 1, d.getDate()) + (d.getHours() * 3600 + d.getMinutes() * 60 + d.getSeconds()) / 86400;
});
add({ de: 'DATUM', en: 'DATE', category: 'Datum', signature: 'DATUM(Jahr; Monat; Tag)', desc: 'Erzeugt ein Datum.' }, (args, ctx) => {
  const y = evalNum(ctx, args[0]);
  const m = evalNum(ctx, args[1]);
  const d = evalNum(ctx, args[2]);
  if (isErr(y) || isErr(m) || isErr(d)) return isErr(y) ? y : isErr(m) ? m : d;
  const dt = new Date(Date.UTC(Math.trunc(y), Math.trunc(m) - 1, Math.trunc(d)));
  return dateToSerial(dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate());
});
add({ de: 'ZEIT', en: 'TIME', category: 'Datum', signature: 'ZEIT(Stunde; Minute; Sekunde)', desc: 'Uhrzeit als Tagesbruchteil.' }, (args, ctx) => {
  const h = evalNum(ctx, args[0]);
  const m = evalNum(ctx, args[1]);
  const s = evalNum(ctx, args[2]);
  if (isErr(h) || isErr(m) || isErr(s)) return isErr(h) ? h : isErr(m) ? m : s;
  return (Math.trunc(h) * 3600 + Math.trunc(m) * 60 + Math.trunc(s)) / 86400;
});
add({ de: 'DATWERT', en: 'DATEVALUE', category: 'Datum', signature: 'DATWERT(Text)', desc: 'Datumstext in eine Seriennummer.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  if (isErr(t)) return t;
  const d = parseDateStrict(t) ?? parseDateTimeStrict(t);
  return d === null ? WERT() : Math.floor(d);
});
add({ de: 'ZEITWERT', en: 'TIMEVALUE', category: 'Datum', signature: 'ZEITWERT(Text)', desc: 'Zeittext in einen Tagesbruchteil.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  if (isErr(t)) return t;
  const d = parseTimeStrict(t);
  return d === null ? WERT() : d;
});
add({ de: 'JAHR', en: 'YEAR', category: 'Datum', signature: 'JAHR(Datum)', desc: 'Jahr einer Seriennummer.' }, (args, ctx) => part(ctx, args, 'y'));
add({ de: 'MONAT', en: 'MONTH', category: 'Datum', signature: 'MONAT(Datum)', desc: 'Monat einer Seriennummer.' }, (args, ctx) => part(ctx, args, 'm'));
add({ de: 'TAG', en: 'DAY', category: 'Datum', signature: 'TAG(Datum)', desc: 'Tag einer Seriennummer.' }, (args, ctx) => part(ctx, args, 'd'));
function part(ctx: FnCtx, args: Expr[], k: 'y' | 'm' | 'd'): Value {
  const n = evalNum(ctx, args[0]);
  if (isErr(n)) return n;
  return serialToParts(n)[k];
}
add({ de: 'STUNDE', en: 'HOUR', category: 'Datum', signature: 'STUNDE(Zahl)', desc: 'Stunde aus einer Uhrzeit.' }, (args, ctx) => timePart(ctx, args, 'h'));
add({ de: 'MINUTE', en: 'MINUTE', category: 'Datum', signature: 'MINUTE(Zahl)', desc: 'Minute aus einer Uhrzeit.' }, (args, ctx) => timePart(ctx, args, 'm'));
add({ de: 'SEKUNDE', en: 'SECOND', category: 'Datum', signature: 'SEKUNDE(Zahl)', desc: 'Sekunde aus einer Uhrzeit.' }, (args, ctx) => timePart(ctx, args, 's'));
function timePart(ctx: FnCtx, args: Expr[], k: 'h' | 'm' | 's'): Value {
  const n = evalNum(ctx, args[0]);
  if (isErr(n)) return n;
  let secs = Math.round((((n % 1) + 1) % 1) * 86400);
  const h = Math.floor(secs / 3600);
  secs %= 3600;
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return k === 'h' ? h : k === 'm' ? m : s;
}
add({ de: 'WOCHENTAG', en: 'WEEKDAY', category: 'Datum', signature: 'WOCHENTAG(Datum; [Typ])', desc: 'Wochentag. Typ 2: Montag = 1.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const typ = args[1] ? evalNum(ctx, args[1]) : 1;
  if (isErr(n) || isErr(typ)) return isErr(n) ? n : typ;
  const wd = serialToParts(n).wd;
  if (typ === 2) return wd === 0 ? 7 : wd;
  if (typ === 3) return wd === 0 ? 6 : wd - 1;
  return wd + 1;
});
add({ de: 'KALENDERWOCHE', en: 'WEEKNUM', category: 'Datum', signature: 'KALENDERWOCHE(Datum; [Typ])', desc: 'Kalenderwoche. Standard ist die ISO-Woche (Typ 21).' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const typ = args[1] ? evalNum(ctx, args[1]) : 21;
  if (isErr(n) || isErr(typ)) return isErr(n) ? n : typ;
  if (typ === 21 || typ === 2) return isoWeek(n);
  const p = serialToParts(n);
  const start = dateToSerial(p.y, 1, 1);
  const sow = serialToParts(start).wd;
  return Math.floor((Math.floor(n) - start + sow) / 7) + 1;
});
add({ de: 'TAGE', en: 'DAYS', category: 'Datum', signature: 'TAGE(Ende; Anfang)', desc: 'Anzahl der Tage zwischen zwei Daten.' }, (args, ctx) => {
  const a = evalNum(ctx, args[0]);
  const b = evalNum(ctx, args[1]);
  if (isErr(a) || isErr(b)) return isErr(a) ? a : b;
  return Math.floor(a) - Math.floor(b);
});
add({ de: 'DATEDIF', en: 'DATEDIF', category: 'Datum', signature: 'DATEDIF(Anfang; Ende; Einheit)', desc: 'Differenz in Y, M, D, YM, MD oder YD.' }, (args, ctx) => {
  const a = evalNum(ctx, args[0]);
  const b = evalNum(ctx, args[1]);
  const u = text(ctx.eval(args[2]));
  if (isErr(a) || isErr(b) || isErr(u)) return isErr(a) ? a : isErr(b) ? b : u;
  return datedif(a, b, u);
});
add({ de: 'NETTOARBEITSTAGE', en: 'NETWORKDAYS', category: 'Datum', signature: 'NETTOARBEITSTAGE(Anfang; Ende; [Feiertage])', desc: 'Arbeitstage, Wochenenden zählen nicht.' }, (args, ctx) => {
  const a = evalNum(ctx, args[0]);
  const b = evalNum(ctx, args[1]);
  if (isErr(a) || isErr(b)) return isErr(a) ? a : b;
  let hol: number[] = [];
  if (args[2]) {
    const xs = numbers(ctx.eval(args[2]));
    if (isErr(xs)) return xs;
    hol = xs;
  }
  return networkdays(a, b, hol);
});
add({ de: 'ARBEITSTAG', en: 'WORKDAY', category: 'Datum', signature: 'ARBEITSTAG(Anfang; Tage; [Feiertage])', desc: 'Datum nach einer Anzahl Arbeitstagen.' }, (args, ctx) => {
  const a = evalNum(ctx, args[0]);
  const d = evalNum(ctx, args[1]);
  if (isErr(a) || isErr(d)) return isErr(a) ? a : d;
  let hol: number[] = [];
  if (args[2]) {
    const xs = numbers(ctx.eval(args[2]));
    if (isErr(xs)) return xs;
    hol = xs;
  }
  return workday(a, d, hol);
});
add({ de: 'EDATUM', en: 'EDATE', category: 'Datum', signature: 'EDATUM(Anfang; Monate)', desc: 'Datum um Monate verschieben.' }, (args, ctx) => {
  const a = evalNum(ctx, args[0]);
  const m = evalNum(ctx, args[1]);
  if (isErr(a) || isErr(m)) return isErr(a) ? a : m;
  return addMonths(a, Math.trunc(m));
});
add({ de: 'MONATSENDE', en: 'EOMONTH', category: 'Datum', signature: 'MONATSENDE(Anfang; Monate)', desc: 'Letzter Tag des Monats.' }, (args, ctx) => {
  const a = evalNum(ctx, args[0]);
  const m = evalNum(ctx, args[1]);
  if (isErr(a) || isErr(m)) return isErr(a) ? a : m;
  return endOfMonth(a, Math.trunc(m));
});

add({ de: 'SVERWEIS', en: 'VLOOKUP', category: 'Suche', signature: 'SVERWEIS(Suchwert; Matrix; Spalte; [Ungefähr])', desc: 'Sucht in der ersten Spalte. Standard ist die exakte Suche.' }, (args, ctx) => {
  const look = scalar(ctx.eval(args[0]));
  if (isErr(look)) return look;
  const table = ctx.rangeOf(args[1]);
  if (isErr(table)) return table;
  const col = evalNum(ctx, args[2]);
  if (isErr(col)) return col;
  const approx = args[3] ? truth(ctx.eval(args[3])) : false;
  if (isErr(approx)) return approx;
  const ci = Math.trunc(col) - 1;
  if (ci < 0 || ci >= (table.values[0]?.length ?? 0)) return BEZUG();
  const keys = table.values.map((r) => r[0]);
  if (!approx) {
    const pos = matchPos(keys, look, 0, false);
    if (isErr(pos)) return pos;
    return table.values[pos][ci];
  }
  const pos = matchPos(keys, look, -1, false);
  if (isErr(pos)) return pos;
  return table.values[pos][ci];
});
add({ de: 'WVERWEIS', en: 'HLOOKUP', category: 'Suche', signature: 'WVERWEIS(Suchwert; Matrix; Zeile; [Ungefähr])', desc: 'Sucht in der ersten Zeile.' }, (args, ctx) => {
  const look = scalar(ctx.eval(args[0]));
  if (isErr(look)) return look;
  const table = ctx.rangeOf(args[1]);
  if (isErr(table)) return table;
  const row = evalNum(ctx, args[2]);
  if (isErr(row)) return row;
  const approx = args[3] ? truth(ctx.eval(args[3])) : false;
  if (isErr(approx)) return approx;
  const ri = Math.trunc(row) - 1;
  if (ri < 0 || ri >= table.values.length) return BEZUG();
  const keys = table.values[0];
  const pos = matchPos(keys, look, approx ? -1 : 0, false);
  if (isErr(pos)) return pos;
  return table.values[ri][pos];
});
add({ de: 'XVERWEIS', en: 'XLOOKUP', category: 'Suche', signature: 'XVERWEIS(Suchwert; Suchvektor; Rückgabe; [Falls_nv]; [Modus]; [Suchmodus])', desc: 'Flexibler Nachschlagewert, auch rückwärts.' }, (args, ctx) => {
  const look = scalar(ctx.eval(args[0]));
  if (isErr(look)) return look;
  const keysM = ctx.rangeOf(args[1]);
  const retM = ctx.rangeOf(args[2]);
  if (isErr(keysM) || isErr(retM)) return isErr(keysM) ? keysM : retM;
  const keysV = lookupVector(keysM);
  if (isErr(keysV)) return keysV;
  const mode = args[4] ? evalNum(ctx, args[4]) : 0;
  const search = args[5] ? evalNum(ctx, args[5]) : 1;
  if (isErr(mode) || isErr(search)) return isErr(mode) ? mode : search;
  const pos = matchPos(keysV.values, look, Math.trunc(mode), Math.trunc(search) < 0);
  if (isErr(pos)) return args[3] ? ctx.eval(args[3]) : pos;
  if (keysV.vertical) {
    if (retM.values.length === keysV.values.length) {
      const row = retM.values[pos];
      return row.length === 1 ? row[0] : mat([row]);
    }
  } else if ((retM.values[0]?.length ?? 0) === keysV.values.length) {
    const col = retM.values.map((r) => r[pos]);
    return col.length === 1 ? col[0] : mat(col.map((v) => [v]));
  }
  return NV();
});
add({ de: 'XVERGLEICH', en: 'XMATCH', category: 'Suche', signature: 'XVERGLEICH(Suchwert; Suchvektor; [Modus]; [Suchmodus])', desc: 'Relative Position, 1-basiert.' }, (args, ctx) => {
  const look = scalar(ctx.eval(args[0]));
  if (isErr(look)) return look;
  const keysM = ctx.rangeOf(args[1]);
  if (isErr(keysM)) return keysM;
  const keysV = lookupVector(keysM);
  if (isErr(keysV)) return keysV;
  const mode = args[2] ? evalNum(ctx, args[2]) : 0;
  const search = args[3] ? evalNum(ctx, args[3]) : 1;
  if (isErr(mode) || isErr(search)) return isErr(mode) ? mode : search;
  const pos = matchPos(keysV.values, look, Math.trunc(mode), Math.trunc(search) < 0);
  return isErr(pos) ? pos : pos + 1;
});
add({ de: 'VERGLEICH', en: 'MATCH', category: 'Suche', signature: 'VERGLEICH(Suchwert; Bereich; [Typ])', desc: 'Position im Bereich. Typ 0 = exakt (Standard).' }, (args, ctx) => {
  const look = scalar(ctx.eval(args[0]));
  if (isErr(look)) return look;
  const keysM = ctx.rangeOf(args[1]);
  if (isErr(keysM)) return keysM;
  const keysV = lookupVector(keysM);
  if (isErr(keysV)) return keysV;
  const typ = args[2] ? evalNum(ctx, args[2]) : 0;
  if (isErr(typ)) return typ;
  const mode = Math.trunc(typ) === 1 ? -1 : Math.trunc(typ) === -1 ? 1 : 0;
  const pos = matchPos(keysV.values, look, mode, false);
  return isErr(pos) ? pos : pos + 1;
});
add({ de: 'INDEX', en: 'INDEX', category: 'Suche', signature: 'INDEX(Matrix; Zeile; [Spalte])', desc: 'Zelle oder Teilbereich aus einer Matrix. 0 liefert die ganze Zeile oder Spalte.' }, (args, ctx) => {
  const m = ctx.rangeOf(args[0]);
  if (isErr(m)) return m;
  const row = evalNum(ctx, args[1]);
  if (isErr(row)) return row;
  const col = args[2] ? evalNum(ctx, args[2]) : 1;
  if (isErr(col)) return col;
  const r = Math.trunc(row);
  const c = Math.trunc(col);
  if (m.values.length === 1 || (m.values[0]?.length === 1 && args.length < 3)) {
    const vec = lookupVector(m);
    if (isErr(vec)) return vec;
    if (r < 1 || r > vec.values.length) return BEZUG();
    return vec.values[r - 1];
  }
  if (r === 0 && c > 0) {
    if (c > (m.values[0]?.length ?? 0)) return BEZUG();
    return mat(m.values.map((rr) => [rr[c - 1]]));
  }
  if (c === 0 && r > 0) {
    if (r > m.values.length) return BEZUG();
    return mat([m.values[r - 1]]);
  }
  if (r < 1 || c < 1 || r > m.values.length || c > m.values[0].length) return BEZUG();
  return m.values[r - 1][c - 1];
});
add({ de: 'ZEILE', en: 'ROW', category: 'Suche', signature: 'ZEILE([Bezug])', desc: 'Zeilennummer.' }, (args, ctx) => {
  if (!args.length) return ctx.row + 1;
  const a = ctx.addressOf(args[0]);
  if (!a) return WERT();
  if (a.r1 === a.r2) return a.r1 + 1;
  return mat(Array.from({ length: a.r2 - a.r1 + 1 }, (_, i) => [a.r1 + 1 + i]));
});
add({ de: 'SPALTE', en: 'COLUMN', category: 'Suche', signature: 'SPALTE([Bezug])', desc: 'Spaltennummer.' }, (args, ctx) => {
  if (!args.length) return ctx.col + 1;
  const a = ctx.addressOf(args[0]);
  if (!a) return WERT();
  if (a.c1 === a.c2) return a.c1 + 1;
  return mat([Array.from({ length: a.c2 - a.c1 + 1 }, (_, i) => a.c1 + 1 + i)]);
});
add({ de: 'ZEILEN', en: 'ROWS', category: 'Suche', signature: 'ZEILEN(Matrix)', desc: 'Anzahl der Zeilen.' }, (args, ctx) => {
  const m = ctx.rangeOf(args[0]);
  return isErr(m) ? m : m.values.length;
});
add({ de: 'SPALTEN', en: 'COLUMNS', category: 'Suche', signature: 'SPALTEN(Matrix)', desc: 'Anzahl der Spalten.' }, (args, ctx) => {
  const m = ctx.rangeOf(args[0]);
  return isErr(m) ? m : m.values[0]?.length ?? 0;
});
add({ de: 'INDIREKT', en: 'INDIRECT', category: 'Suche', signature: 'INDIREKT(Bezug)', desc: 'Wert eines als Text angegebenen Bezugs.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  if (isErr(t)) return t;
  try {
    const expr = parseFormula(t.startsWith('=') ? t.slice(1) : t);
    return ctx.eval(expr);
  } catch {
    return BEZUG();
  }
});
add({ de: 'BEREICH.VERSCHIEBEN', en: 'OFFSET', category: 'Suche', signature: 'BEREICH.VERSCHIEBEN(Bezug; Zeilen; Spalten; [Höhe]; [Breite])', desc: 'Verschobener Bereich.' }, (args, ctx) => {
  const a = ctx.addressOf(args[0]);
  if (!a) return WERT();
  const dr = evalNum(ctx, args[1]);
  const dc = evalNum(ctx, args[2]);
  if (isErr(dr) || isErr(dc)) return isErr(dr) ? dr : dc;
  const h = args[3] ? evalNum(ctx, args[3]) : a.r2 - a.r1 + 1;
  const w = args[4] ? evalNum(ctx, args[4]) : a.c2 - a.c1 + 1;
  if (isErr(h) || isErr(w)) return isErr(h) ? h : w;
  if (h < 1 || w < 1) return BEZUG();
  const r1 = a.r1 + Math.trunc(dr);
  const c1 = a.c1 + Math.trunc(dc);
  return ctx.readRange(a.sheet, r1, c1, r1 + Math.trunc(h) - 1, c1 + Math.trunc(w) - 1);
});
add({ de: 'HYPERLINK', en: 'HYPERLINK', category: 'Suche', signature: 'HYPERLINK(URL; [Name])', desc: 'Klickbarer Link.' }, (args, ctx) => {
  const href = text(ctx.eval(args[0]));
  if (isErr(href)) return href;
  const label = args[1] ? text(ctx.eval(args[1])) : href;
  if (isErr(label)) return label;
  return new LinkVal(href, label);
});
add({ de: 'FILTER', en: 'FILTER', category: 'Dynamisch', signature: 'FILTER(Matrix; Einschließen; [Wenn_leer])', desc: 'Zeilen, deren Kriterium wahr ist, als dynamisches Array.' }, (args, ctx) => {
  const m = ctx.rangeOf(args[0]);
  const inc = ctx.rangeOf(args[1]);
  if (isErr(m) || isErr(inc)) return isErr(m) ? m : inc;
  const rows: CellVal[][] = [];
  if (inc.values.length === m.values.length) {
    for (let r = 0; r < m.values.length; r++) {
      const flag = inc.values[r][0];
      if (isErr(flag)) return flag;
      const ok = flag === true || (typeof flag === 'number' && flag !== 0);
      if (ok) rows.push(m.values[r]);
    }
  } else return WERT();
  if (!rows.length) return args[2] ? ctx.eval(args[2]) : NV();
  return mat(rows);
});
add({ de: 'SORTIEREN', en: 'SORT', category: 'Dynamisch', signature: 'SORTIEREN(Matrix; [Index]; [Reihenfolge]; [Nach_Spalte])', desc: 'Sortiert eine Matrix. Reihenfolge 1 aufsteigend, -1 absteigend.' }, (args, ctx) => {
  const m = ctx.rangeOf(args[0]);
  if (isErr(m)) return m;
  const index = args[1] ? evalNum(ctx, args[1]) : 1;
  const order = args[2] ? evalNum(ctx, args[2]) : 1;
  const byCol = args[3] ? truth(ctx.eval(args[3])) : false;
  if (isErr(index) || isErr(order) || isErr(byCol)) return isErr(index) ? index : isErr(order) ? order : byCol;
  if (byCol) return WERT();
  return sortMatrix(m, Math.trunc(index), order, false);
});
add({ de: 'SORTIERENNACH', en: 'SORTBY', category: 'Dynamisch', signature: 'SORTIERENNACH(Matrix; Nach_Matrix; [Reihenfolge]; …)', desc: 'Sortiert nach einer anderen Spalte.' }, (args, ctx) => {
  const m = ctx.rangeOf(args[0]);
  if (isErr(m)) return m;
  const keys: { col: CellVal[]; order: number }[] = [];
  for (let i = 1; i < args.length; i += 2) {
    const km = ctx.rangeOf(args[i]);
    if (isErr(km)) return km;
    const order = args[i + 1] ? evalNum(ctx, args[i + 1]) : 1;
    if (isErr(order)) return order;
    keys.push({ col: km.values.map((r) => r[0]), order });
  }
  const keyed = m.values.map((r, i) => ({ r, i }));
  keyed.sort((a, b) => {
    for (const k of keys) {
      const c = cmpVal(k.col[a.i] ?? null, k.col[b.i] ?? null);
      if (c) return k.order < 0 ? -c : c;
    }
    return a.i - b.i;
  });
  return mat(keyed.map((k) => k.r));
});
add({ de: 'EINDEUTIG', en: 'UNIQUE', category: 'Dynamisch', signature: 'EINDEUTIG(Matrix; [Nach_Spalte]; [Genau_einmal])', desc: 'Dublettenfreie Zeilen.' }, (args, ctx) => {
  const m = ctx.rangeOf(args[0]);
  if (isErr(m)) return m;
  const once = args[2] ? truth(ctx.eval(args[2])) : false;
  if (isErr(once)) return once;
  const seen = new Map<string, { row: CellVal[]; n: number }>();
  for (const row of m.values) {
    const key = JSON.stringify(row);
    const e = seen.get(key);
    if (e) e.n++;
    else seen.set(key, { row, n: 1 });
  }
  const rows = [...seen.values()].filter((e) => (once ? e.n === 1 : true)).map((e) => e.row);
  if (!rows.length) return NV();
  return mat(rows);
});
add({ de: 'SEQUENZ', en: 'SEQUENCE', category: 'Dynamisch', signature: 'SEQUENZ(Zeilen; [Spalten]; [Start]; [Schritt])', desc: 'Zahlenfolge als Array.' }, (args, ctx) => {
  const rows = evalNum(ctx, args[0]);
  const cols = args[1] ? evalNum(ctx, args[1]) : 1;
  const start = args[2] ? evalNum(ctx, args[2]) : 1;
  const step = args[3] ? evalNum(ctx, args[3]) : 1;
  if (isErr(rows) || isErr(cols) || isErr(start) || isErr(step)) return isErr(rows) ? rows : isErr(cols) ? cols : isErr(start) ? start : step;
  const h = Math.trunc(rows);
  const w = Math.trunc(cols);
  if (h < 1 || w < 1 || h * w > 20000) return WERT();
  let n = start;
  const values: number[][] = [];
  for (let r = 0; r < h; r++) {
    const row: number[] = [];
    for (let c = 0; c < w; c++) {
      row.push(n);
      n += step;
    }
    values.push(row);
  }
  return mat(values);
});
add({ de: 'MTRANS', en: 'TRANSPOSE', category: 'Matrix', signature: 'MTRANS(Matrix)', desc: 'Transponiert eine Matrix.' }, (args, ctx) => {
  const m = ctx.rangeOf(args[0]);
  if (isErr(m)) return m;
  const h = m.values.length;
  const w = m.values[0]?.length ?? 0;
  const values: CellVal[][] = [];
  for (let c = 0; c < w; c++) {
    const row: CellVal[] = [];
    for (let r = 0; r < h; r++) row.push(m.values[r][c]);
    values.push(row);
  }
  return mat(values);
});
add({ de: 'MMULT', en: 'MMULT', category: 'Matrix', signature: 'MMULT(Matrix1; Matrix2)', desc: 'Matrixprodukt.' }, (args, ctx): Value => {
  const a = ctx.rangeOf(args[0]);
  const b = ctx.rangeOf(args[1]);
  if (isErr(a) || isErr(b)) return isErr(a) ? a : b;
  const A = toNumMatrix(a);
  const B = toNumMatrix(b);
  if (isErr(A)) return A;
  if (isErr(B)) return B;
  if (A[0].length !== B.length) return WERT();
  const values: number[][] = [];
  for (let i = 0; i < A.length; i++) {
    const row: number[] = [];
    for (let j = 0; j < B[0].length; j++) {
      let s = 0;
      for (let k = 0; k < B.length; k++) s += A[i][k] * B[k][j];
      row.push(s);
    }
    values.push(row);
  }
  return mat(values);
});
add({ de: 'MINV', en: 'MINVERSE', category: 'Matrix', signature: 'MINV(Matrix)', desc: 'Inverse einer quadratischen Matrix.' }, (args, ctx) => {
  const m = ctx.rangeOf(args[0]);
  if (isErr(m)) return m;
  const A = toNumMatrix(m);
  if (isErr(A)) return A;
  if (A.length !== A[0].length) return WERT();
  const inv = invert(A);
  if (isErr(inv)) return inv;
  return mat(inv);
});
add({ de: 'MDET', en: 'MDETERM', category: 'Matrix', signature: 'MDET(Matrix)', desc: 'Determinante.' }, (args, ctx) => {
  const m = ctx.rangeOf(args[0]);
  if (isErr(m)) return m;
  const A = toNumMatrix(m);
  if (isErr(A)) return A;
  if (A.length !== A[0].length) return WERT();
  return det(A);
}, ['MDETERM']);
add({ de: 'MEINHEIT', en: 'MUNIT', category: 'Matrix', signature: 'MEINHEIT(Dimension)', desc: 'Einheitsmatrix.' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  if (isErr(n)) return n;
  const k = Math.trunc(n);
  if (k < 1 || k > 50) return WERT();
  return mat(Array.from({ length: k }, (_, r) => Array.from({ length: k }, (_, c) => (r === c ? 1 : 0))));
});

function dAgg(kind: string, args: Expr[], ctx: FnCtx): Value {
  const got = dField(args, ctx);
  if (isErr(got)) return got;
  const nums = numericVals(got.vals);
  if (isErr(nums)) return nums;
  if (kind === 'dget') {
    if (got.rows.length === 0) return WERT();
    if (got.rows.length > 1) return ZAHL();
    return got.vals[0];
  }
  if (kind === 'dcount') return nums.length;
  if (kind === 'dcounta') return got.vals.filter((v) => !isErr(v) && v !== null && v !== '').length;
  if (kind === 'dsum') return nums.reduce((a, b) => a + b, 0);
  if (kind === 'dproduct') return nums.length ? nums.reduce((a, b) => a * b, 1) : 0;
  if (kind === 'davg') return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : DIV0();
  if (kind === 'dmax') return nums.length ? Math.max(...nums) : 0;
  if (kind === 'dmin') return nums.length ? Math.min(...nums) : 0;
  if (kind === 'dstdev') return stdev(nums, false);
  if (kind === 'dstdevp') return stdev(nums, true);
  if (kind === 'dvar') return variance(nums, false);
  if (kind === 'dvarp') return variance(nums, true);
  return WERT();
}
add({ de: 'DSUMME', en: 'DSUM', category: 'Datenbank', signature: 'DSUMME(Datenbank; Feld; Suchkriterien)', desc: 'Summe einer Spalte für alle Zeilen, die den Kriterien entsprechen.' }, (a, c) => dAgg('dsum', a, c));
add({ de: 'DMITTELWERT', en: 'DAVERAGE', category: 'Datenbank', signature: 'DMITTELWERT(Datenbank; Feld; Suchkriterien)', desc: 'Mittelwert der passenden Datensätze.' }, (a, c) => dAgg('davg', a, c));
add({ de: 'DANZAHL', en: 'DCOUNT', category: 'Datenbank', signature: 'DANZAHL(Datenbank; Feld; Suchkriterien)', desc: 'Anzahl numerischer Felder, die den Kriterien entsprechen.' }, (a, c) => dAgg('dcount', a, c));
add({ de: 'DANZAHL2', en: 'DCOUNTA', category: 'Datenbank', signature: 'DANZAHL2(Datenbank; Feld; Suchkriterien)', desc: 'Anzahl nichtleerer Felder, die den Kriterien entsprechen.' }, (a, c) => dAgg('dcounta', a, c));
add({ de: 'DMAX', en: 'DMAX', category: 'Datenbank', signature: 'DMAX(Datenbank; Feld; Suchkriterien)', desc: 'Größter Wert unter den passenden Datensätzen.' }, (a, c) => dAgg('dmax', a, c));
add({ de: 'DMIN', en: 'DMIN', category: 'Datenbank', signature: 'DMIN(Datenbank; Feld; Suchkriterien)', desc: 'Kleinster Wert unter den passenden Datensätzen.' }, (a, c) => dAgg('dmin', a, c));
add({ de: 'DPRODUKT', en: 'DPRODUCT', category: 'Datenbank', signature: 'DPRODUKT(Datenbank; Feld; Suchkriterien)', desc: 'Produkt der passenden Werte.' }, (a, c) => dAgg('dproduct', a, c));
add({ de: 'DSTABW', en: 'DSTDEV', category: 'Datenbank', signature: 'DSTABW(Datenbank; Feld; Suchkriterien)', desc: 'Stichproben-Standardabweichung der Treffer.' }, (a, c) => dAgg('dstdev', a, c));
add({ de: 'DSTABWN', en: 'DSTDEVP', category: 'Datenbank', signature: 'DSTABWN(Datenbank; Feld; Suchkriterien)', desc: 'Standardabweichung der Grundgesamtheit.' }, (a, c) => dAgg('dstdevp', a, c));
add({ de: 'DVARIANZ', en: 'DVAR', category: 'Datenbank', signature: 'DVARIANZ(Datenbank; Feld; Suchkriterien)', desc: 'Stichprobenvarianz der Treffer.' }, (a, c) => dAgg('dvar', a, c));
add({ de: 'DVARIANZEN', en: 'DVARP', category: 'Datenbank', signature: 'DVARIANZEN(Datenbank; Feld; Suchkriterien)', desc: 'Varianz der Grundgesamtheit.' }, (a, c) => dAgg('dvarp', a, c));
add({ de: 'DAUSZUG', en: 'DGET', category: 'Datenbank', signature: 'DAUSZUG(Datenbank; Feld; Suchkriterien)', desc: 'Genau ein Feld. Mehrere Treffer ergeben #ZAHL!, keiner #WERT!.' }, (a, c) => dAgg('dget', a, c));
add({ de: 'ABFRAGE', en: 'QUERY', category: 'Datenbank', signature: 'ABFRAGE("SELECT … FROM A1:E20 WHERE …")', desc: 'SQL-artige Abfrage über einen Bereich mit Kopfzeile.' }, (args, ctx) => {
  const sql = text(ctx.eval(args[0]));
  if (isErr(sql)) return sql;
  return executeQuery(sql, (source) => {
    const table = ctx.tables.find((t) => t.name.toLocaleLowerCase('de-DE') === source.toLocaleLowerCase('de-DE'));
    if (table) {
      const r2 = table.totalsRow ? table.r2 - 1 : table.r2;
      return ctx.readRange(table.sheet, table.r1, table.c1, r2, table.c2);
    }
    const named = ctx.names.find((n) => n.name.toLocaleLowerCase('de-DE') === source.toLocaleLowerCase('de-DE') && n.r1 !== undefined);
    if (named && named.r1 !== undefined && named.c1 !== undefined && named.r2 !== undefined && named.c2 !== undefined) {
      return ctx.readRange(named.sheet || ctx.sheet, named.r1, named.c1, named.r2, named.c2);
    }
    try {
      return ctx.rangeOf(parseFormula(source));
    } catch {
      return WERT();
    }
  });
});

add({ de: 'RMZ', en: 'PMT', category: 'Finanzen', signature: 'RMZ(Zins; Zzr; Bw; [Zw]; [F])', desc: 'Regelmäßige Zahlung eines Kredits.' }, (args, ctx) => fin((a) => pmt(a[0], a[1], a[2], a[3] ?? 0, a[4] ?? 0), args, ctx));
add({ de: 'ZW', en: 'FV', category: 'Finanzen', signature: 'ZW(Zins; Zzr; Rmz; [Bw]; [F])', desc: 'Zukünftiger Wert.' }, (args, ctx) => fin((a) => fv(a[0], a[1], a[2], a[3] ?? 0, a[4] ?? 0), args, ctx));
add({ de: 'BW', en: 'PV', category: 'Finanzen', signature: 'BW(Zins; Zzr; Rmz; [Zw]; [F])', desc: 'Barwert.' }, (args, ctx) => fin((a) => pv(a[0], a[1], a[2], a[3] ?? 0, a[4] ?? 0), args, ctx));
add({ de: 'ZZR', en: 'NPER', category: 'Finanzen', signature: 'ZZR(Zins; Rmz; Bw; [Zw]; [F])', desc: 'Anzahl der Zahlungsperioden.' }, (args, ctx) => fin((a) => nper(a[0], a[1], a[2], a[3] ?? 0, a[4] ?? 0), args, ctx));
add({ de: 'ZINS', en: 'RATE', category: 'Finanzen', signature: 'ZINS(Zzr; Rmz; Bw; [Zw]; [F]; [Schätzwert])', desc: 'Zinssatz je Periode.' }, (args, ctx) => {
  const xs: number[] = [];
  for (let i = 0; i < args.length; i++) {
    const n = evalNum(ctx, args[i]);
    if (isErr(n)) return n;
    xs.push(n);
  }
  if (xs.length < 3) return WERT();
  const nperV = xs[0];
  const pmtV = xs[1];
  const pvV = xs[2];
  const fvV = xs[3] ?? 0;
  const type = xs[4] ?? 0;
  let r = xs[5] ?? 0.1;
  for (let i = 0; i < 40; i++) {
    if (Math.abs(r) < 1e-10) r = 1e-10;
    const pow = (1 + r) ** nperV;
    const f = pvV * pow + pmtV * (1 + r * type) * ((pow - 1) / r) + fvV;
    const df =
      nperV * pvV * (1 + r) ** (nperV - 1) +
      pmtV * type * ((pow - 1) / r) +
      pmtV * (1 + r * type) * ((r * nperV * (1 + r) ** (nperV - 1) - (pow - 1)) / (r * r));
    if (!Number.isFinite(df) || Math.abs(df) < 1e-14) break;
    const next = r - f / df;
    if (Math.abs(next - r) < 1e-10) return next;
    r = next;
  }
  return Number.isFinite(r) ? r : ZAHL();
});
function fin(fn: (a: number[]) => number | FError, args: Expr[], ctx: FnCtx): Value {
  const xs: number[] = [];
  for (const a of args) {
    const n = evalNum(ctx, a);
    if (isErr(n)) return n;
    xs.push(n);
  }
  if (xs.length < 3) return WERT();
  return fn(xs);
}
add({ de: 'ZINSZ', en: 'IPMT', category: 'Finanzen', signature: 'ZINSZ(Zins; Zr; Zzr; Bw; [Zw]; [F])', desc: 'Zinsanteil einer Zahlung.' }, (args, ctx) => {
  const rate = evalNum(ctx, args[0]);
  const per = evalNum(ctx, args[1]);
  const np = evalNum(ctx, args[2]);
  const pvVal = evalNum(ctx, args[3]);
  const fvVal = args[4] ? evalNum(ctx, args[4]) : 0;
  const type = args[5] ? evalNum(ctx, args[5]) : 0;
  if (isErr(rate)) return rate;
  if (isErr(per)) return per;
  if (isErr(np)) return np;
  if (isErr(pvVal)) return pvVal;
  if (isErr(fvVal)) return fvVal;
  if (isErr(type)) return type;
  if (per < 1 || per > np) return ZAHL();
  const pay = pmt(rate, np, pvVal, fvVal, type);
  if (isErr(pay)) return pay;
  if (type === 1 && per === 1) return 0;
  const base = fv(rate, per - (type === 1 ? 2 : 1), pay, pvVal, type);
  if (isErr(base)) return base;
  return base * rate;
});
add({ de: 'KAPZ', en: 'PPMT', category: 'Finanzen', signature: 'KAPZ(Zins; Zr; Zzr; Bw; [Zw]; [F])', desc: 'Tilgungsanteil einer Zahlung.' }, (args, ctx) => {
  const rate = evalNum(ctx, args[0]);
  const per = evalNum(ctx, args[1]);
  const np = evalNum(ctx, args[2]);
  const pvVal = evalNum(ctx, args[3]);
  const fvVal = args[4] ? evalNum(ctx, args[4]) : 0;
  const type = args[5] ? evalNum(ctx, args[5]) : 0;
  if (isErr(rate)) return rate;
  if (isErr(per)) return per;
  if (isErr(np)) return np;
  if (isErr(pvVal)) return pvVal;
  if (isErr(fvVal)) return fvVal;
  if (isErr(type)) return type;
  const pay = pmt(rate, np, pvVal, fvVal, type);
  if (isErr(pay)) return pay;
  const interestFn = registry.get('ZINSZ');
  if (!interestFn) return pay;
  const interest = interestFn(args, ctx);
  if (isErr(interest) || typeof interest !== 'number') return isErr(interest) ? interest : WERT();
  return pay - interest;
});
add({ de: 'NBW', en: 'NPV', category: 'Finanzen', signature: 'NBW(Zins; Wert1; …)', desc: 'Kapitalwert späterer Zahlungen (erste Zahlung eine Periode nach heute).' }, (args, ctx) => {
  const rate = evalNum(ctx, args[0]);
  if (isErr(rate)) return rate;
  const xs = collectNums(ctx, args.slice(1), true);
  if (isErr(xs)) return xs;
  return xs.reduce((acc, v, i) => acc + v / (1 + rate) ** (i + 1), 0);
}, ['BARWERT']);
add({ de: 'IKV', en: 'IRR', category: 'Finanzen', signature: 'IKV(Werte; [Schätzwert])', desc: 'Interner Zinsfuß einer Zahlungsreihe.' }, (args, ctx) => {
  const xs = numbers(ctx.eval(args[0]), true);
  if (isErr(xs)) return xs;
  const guess = args[1] ? evalNum(ctx, args[1]) : 0.1;
  if (isErr(guess)) return guess;
  return irr(xs, guess);
}, ['IZF']);

add({ de: 'ISTLEER', en: 'ISBLANK', category: 'Information', signature: 'ISTLEER(Wert)', desc: 'Wahr, wenn die Zelle leer ist.' }, (args, ctx) => {
  const v = ctx.eval(args[0]);
  if (isMatrix(v)) return v.values.length === 1 && v.values[0].length === 1 && (v.values[0][0] === null || v.values[0][0] === '');
  return v === null || v === '';
});
add({ de: 'ISTZAHL', en: 'ISNUMBER', category: 'Information', signature: 'ISTZAHL(Wert)', desc: 'Wahr bei einer Zahl.' }, (args, ctx) => typeof scalar(ctx.eval(args[0])) === 'number');
add({ de: 'ISTTEXT', en: 'ISTEXT', category: 'Information', signature: 'ISTTEXT(Wert)', desc: 'Wahr bei Text.' }, (args, ctx) => {
  const s = scalar(ctx.eval(args[0]));
  return !isErr(s) && typeof s === 'string';
});
add({ de: 'ISTFORMEL', en: 'ISFORMULA', category: 'Information', signature: 'ISTFORMEL(Bezug)', desc: 'Wahr, wenn die Zelle eine Formel enthält.' }, (args, ctx) => {
  const a = ctx.addressOf(args[0]);
  if (!a) return false;
  return ctx.raw(a.sheet, a.r1, a.c1).startsWith('=');
});
add({ de: 'ISTFEHLER', en: 'ISERROR', category: 'Information', signature: 'ISTFEHLER(Wert)', desc: 'Wahr bei jedem Fehlerwert.' }, (args, ctx) => isErr(ctx.eval(args[0])));
add({ de: 'ISTFEHL', en: 'ISERR', category: 'Information', signature: 'ISTFEHL(Wert)', desc: 'Wahr bei einem Fehler außer #NV.' }, (args, ctx) => {
  const v = ctx.eval(args[0]);
  return isErr(v) && v.code !== '#NV';
});
add({ de: 'ISTNV', en: 'ISNA', category: 'Information', signature: 'ISTNV(Wert)', desc: 'Wahr bei #NV.' }, (args, ctx) => {
  const v = ctx.eval(args[0]);
  return isErr(v) && v.code === '#NV';
});
add({ de: 'NV', en: 'NA', category: 'Information', signature: 'NV()', desc: 'Der Fehlerwert #NV.' }, () => NV());
add({ de: 'FORMELTEXT', en: 'FORMULATEXT', category: 'Information', signature: 'FORMELTEXT(Bezug)', desc: 'Formel einer Zelle als Text.' }, (args, ctx) => {
  const a = ctx.addressOf(args[0]);
  if (!a) return WERT();
  const raw = ctx.raw(a.sheet, a.r1, a.c1);
  if (!raw.startsWith('=')) return NV();
  return raw;
});
add({ de: 'TYP', en: 'TYPE', category: 'Information', signature: 'TYP(Wert)', desc: '1 Zahl, 2 Text, 4 Wahrheitswert, 16 Fehler, 64 Matrix.' }, (args, ctx) => {
  const v = ctx.eval(args[0]);
  if (isErr(v)) return 16;
  if (isMatrix(v)) return 64;
  if (typeof v === 'number') return 1;
  if (typeof v === 'string' || isLink(v)) return 2;
  if (typeof v === 'boolean') return 4;
  if (v === null) return 1;
  return 2;
});
add({ de: 'N', en: 'N', category: 'Information', signature: 'N(Wert)', desc: 'Wandelt in eine Zahl, Text wird 0.' }, (args, ctx) => {
  const v = ctx.eval(args[0]);
  if (isErr(v)) return v;
  if (typeof v === 'number') return v;
  if (typeof v === 'boolean') return v ? 1 : 0;
  if (v === null) return 0;
  return 0;
});
add({ de: 'T', en: 'T', category: 'Information', signature: 'T(Wert)', desc: 'Text bleibt Text, sonst leer.' }, (args, ctx) => {
  const s = scalar(ctx.eval(args[0]));
  if (isErr(s)) return s;
  return typeof s === 'string' ? s : '';
});

add({ de: 'UMWANDELN', en: 'CONVERT', category: 'Technik', signature: 'UMWANDELN(Zahl; Von; Nach)', desc: 'Einheiten umrechnen, z. B. "km" in "mi" oder "C" in "F".' }, (args, ctx) => {
  const n = evalNum(ctx, args[0]);
  const from = text(ctx.eval(args[1]));
  const to = text(ctx.eval(args[2]));
  if (isErr(n) || isErr(from) || isErr(to)) return isErr(n) ? n : isErr(from) ? from : to;
  const a = UNIT[from.toLowerCase()];
  const b = UNIT[to.toLowerCase()];
  if (!a || !b || a.dim !== b.dim) return NV();
  return b.from(a.to(n));
}, ['UMRECHNEN']);
add({ de: 'BININDEZ', en: 'BIN2DEC', category: 'Technik', signature: 'BININDEZ(Zahl)', desc: 'Binär nach Dezimal.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  return isErr(t) ? t : bin2dec(t);
});
add({ de: 'DEZINBIN', en: 'DEC2BIN', category: 'Technik', signature: 'DEZINBIN(Zahl; [Stellen])', desc: 'Dezimal nach Binär.' }, (args, ctx) => baseFn(ctx, args, 2));
add({ de: 'DEZINHEX', en: 'DEC2HEX', category: 'Technik', signature: 'DEZINHEX(Zahl; [Stellen])', desc: 'Dezimal nach Hexadezimal.' }, (args, ctx) => baseFn(ctx, args, 16));
add({ de: 'DEZINOKT', en: 'DEC2OCT', category: 'Technik', signature: 'DEZINOKT(Zahl; [Stellen])', desc: 'Dezimal nach Oktal.' }, (args, ctx) => baseFn(ctx, args, 8));
function baseFn(ctx: FnCtx, args: Expr[], base: number): Value {
  const n = evalNum(ctx, args[0]);
  const p = args[1] ? evalNum(ctx, args[1]) : undefined;
  if (isErr(n) || (p !== undefined && isErr(p))) return isErr(n) ? n : (p as FError);
  return dec2base(n, base, p === undefined ? undefined : Math.trunc(p));
}
add({ de: 'HEXINDEZ', en: 'HEX2DEC', category: 'Technik', signature: 'HEXINDEZ(Zahl)', desc: 'Hexadezimal nach Dezimal.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  if (isErr(t)) return t;
  if (!/^[0-9a-f]+$/i.test(t.trim())) return ZAHL();
  const n = Number.parseInt(t.trim(), 16);
  return Number.isFinite(n) ? n : ZAHL();
});
add({ de: 'OKTINDEZ', en: 'OCT2DEC', category: 'Technik', signature: 'OKTINDEZ(Zahl)', desc: 'Oktal nach Dezimal.' }, (args, ctx) => {
  const t = text(ctx.eval(args[0]));
  if (isErr(t)) return t;
  if (!/^[0-7]+$/.test(t.trim())) return ZAHL();
  return Number.parseInt(t.trim(), 8);
});
add({ de: 'IMSUMME', en: 'IMSUM', category: 'Technik', signature: 'IMSUMME(Komplex1; …)', desc: 'Summe komplexer Zahlen, z. B. "3+4i".' }, (args, ctx) => complexFold(args, ctx, 'sum'));
add({ de: 'IMPRODUKT', en: 'IMPRODUCT', category: 'Technik', signature: 'IMPRODUKT(Komplex1; …)', desc: 'Produkt komplexer Zahlen.' }, (args, ctx) => complexFold(args, ctx, 'prod'));
add({ de: 'IMABS', en: 'IMABS', category: 'Technik', signature: 'IMABS(Komplex)', desc: 'Betrag einer komplexen Zahl.' }, (args, ctx) => {
  const c = oneComplex(ctx, args[0]);
  if (isErr(c)) return c;
  return Math.hypot(c.re, c.im);
});
function oneComplex(ctx: FnCtx, e: Expr): { re: number; im: number } | FError {
  const v = ctx.eval(e);
  if (isErr(v)) return v;
  if (typeof v === 'number') return { re: v, im: 0 };
  const t = text(v);
  if (isErr(t)) return t;
  const c = parseComplex(t);
  return c ?? ZAHL();
}
function complexFold(args: Expr[], ctx: FnCtx, kind: 'sum' | 'prod'): Value {
  let re = kind === 'sum' ? 0 : 1;
  let im = 0;
  for (const a of args) {
    const list = flat(ctx.eval(a));
    if (isErr(list)) return list;
    const items = list.length ? list : [null];
    for (const item of items) {
      const c = typeof item === 'number' ? { re: item, im: 0 } : parseComplex(String(item ?? '0'));
      if (!c) return ZAHL();
      if (kind === 'sum') {
        re += c.re;
        im += c.im;
      } else {
        const nr = re * c.re - im * c.im;
        const ni = re * c.im + im * c.re;
        re = nr;
        im = ni;
      }
    }
  }
  return fmtComplex(re, im);
}

add({ de: 'MINIATUR', en: 'SPARKLINE', category: 'Dynamisch', signature: 'MINIATUR(Bereich; [Typ])', desc: 'Miniaturdiagramm in der Zelle. Typ: linie, säule oder gewinn.' }, (args, ctx) => {
  const xs = numbers(ctx.eval(args[0]));
  if (isErr(xs)) return xs;
  const modeText = args[1] ? text(ctx.eval(args[1])) : 'linie';
  if (isErr(modeText)) return modeText;
  const m = modeText.toLowerCase();
  const mode = m.startsWith('s') || m.startsWith('c') ? 'col' : m.startsWith('g') || m.startsWith('w') ? 'winloss' : 'line';
  return new SparkVal(xs, mode);
}, ['SPARKLINE']);

void UEBER;
void BERECH;
void need;
