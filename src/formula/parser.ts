import { FEHLER, FError } from './value';

export type Expr =
  | { type: 'num'; value: number }
  | { type: 'str'; value: string }
  | { type: 'bool'; value: boolean }
  | { type: 'err'; code: string }
  | { type: 'ref'; sheet?: string; row: number; col: number; absRow: boolean; absCol: boolean }
  | { type: 'range'; a: Expr; b: Expr }
  | { type: 'cols'; sheet?: string; c1: number; c2: number; abs1: boolean; abs2: boolean }
  | { type: 'rows'; sheet?: string; r1: number; r2: number }
  | { type: 'name'; name: string }
  | { type: 'unary'; op: '+' | '-' | '%'; expr: Expr }
  | { type: 'binary'; op: string; left: Expr; right: Expr }
  | { type: 'call'; name: string; args: Expr[] }
  | { type: 'invoke'; fn: Expr; args: Expr[] }
  | { type: 'struct'; table?: string; column: string; thisRow: boolean }
  | { type: 'array'; rows: Expr[][] }
  | { type: 'spill'; ref: Expr };

const COL = /^[A-Za-z]{1,3}$/;

export function colToIndex(name: string): number {
  let n = 0;
  const s = name.toUpperCase();
  for (let i = 0; i < s.length; i++) n = n * 26 + (s.charCodeAt(i) - 64);
  return n - 1;
}

export function indexToCol(index: number): string {
  let n = index + 1;
  let s = '';
  while (n > 0) {
    const m = (n - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

export function parseFormula(input: string): Expr {
  const p = new Parser(input);
  const expr = p.parseComparison();
  p.skip();
  if (!p.eof()) throw new FError('#FEHLER!');
  return expr;
}

export function tryParseFormula(input: string): Expr {
  try {
    return parseFormula(input);
  } catch (e) {
    if (e instanceof FError) return { type: 'err', code: e.code };
    return { type: 'err', code: '#FEHLER!' };
  }
}

class Parser {
  private i = 0;
  constructor(private readonly s: string) {}

  eof(): boolean {
    return this.i >= this.s.length;
  }

  skip(): void {
    while (this.i < this.s.length && /\s/.test(this.s[this.i])) this.i++;
  }

  peek(n = 0): string {
    return this.s[this.i + n] ?? '';
  }

  parseComparison(): Expr {
    let left = this.parseConcat();
    for (;;) {
      this.skip();
      const op = this.matchOp(['<=', '>=', '<>', '=', '<', '>']);
      if (!op) break;
      const right = this.parseConcat();
      left = { type: 'binary', op, left, right };
    }
    return left;
  }

  parseConcat(): Expr {
    let left = this.parseAdd();
    for (;;) {
      this.skip();
      if (this.peek() !== '&') break;
      this.i++;
      const right = this.parseAdd();
      left = { type: 'binary', op: '&', left, right };
    }
    return left;
  }

  parseAdd(): Expr {
    let left = this.parseMul();
    for (;;) {
      this.skip();
      const op = this.matchOp(['+', '-']);
      if (!op) break;
      const right = this.parseMul();
      left = { type: 'binary', op, left, right };
    }
    return left;
  }

  parseMul(): Expr {
    let left = this.parsePow();
    for (;;) {
      this.skip();
      const op = this.matchOp(['*', '/']);
      if (!op) break;
      const right = this.parsePow();
      left = { type: 'binary', op, left, right };
    }
    return left;
  }

  /** ^ ist rechtsassoziativ. -3^2 = 9 (Vorzeichen am Literal), -A1^2 = -(A1^2). */
  parsePow(): Expr {
    this.skip();
    if ((this.peek() === '-' || this.peek() === '+') && this.startsSignedNumber()) {
      const expr = this.parseUnaryLiteralThenPow();
      return expr;
    }
    if (this.peek() === '-' || this.peek() === '+') {
      const op = this.peek() as '+' | '-';
      this.i++;
      const expr = this.parsePow();
      return { type: 'unary', op, expr };
    }
    let base = this.parsePostfix();
    this.skip();
    if (this.peek() === '^') {
      this.i++;
      const exp = this.parsePow();
      base = { type: 'binary', op: '^', left: base, right: exp };
    }
    return base;
  }

  private startsSignedNumber(): boolean {
    const sign = this.peek() === '-' || this.peek() === '+';
    if (!sign) return false;
    let j = this.i + 1;
    while (j < this.s.length && /\s/.test(this.s[j])) j++;
    return /\d/.test(this.s[j] ?? '');
  }

  private parseUnaryLiteralThenPow(): Expr {
    const op = this.peek();
    this.i++;
    this.skip();
    const num = this.readNumber();
    if (num === null) throw FEHLER();
    let base: Expr = { type: 'num', value: op === '-' ? -num : num };
    base = this.finishPostfix(base);
    this.skip();
    if (this.peek() === '^') {
      this.i++;
      const exp = this.parsePow();
      base = { type: 'binary', op: '^', left: base, right: exp };
    }
    return base;
  }

  parsePostfix(): Expr {
    const base = this.parsePrimary();
    return this.finishPostfix(base);
  }

  private finishPostfix(base: Expr): Expr {
    for (;;) {
      this.skip();
      if (this.peek() === '%') {
        this.i++;
        base = { type: 'unary', op: '%', expr: base };
        continue;
      }
      if (this.peek() === '(') {
        const args = this.parseArgList();
        base = { type: 'invoke', fn: base, args };
        continue;
      }
      break;
    }
    return base;
  }

  parsePrimary(): Expr {
    this.skip();
    const c = this.peek();
    if (!c) throw FEHLER();
    if (c === '(') {
      this.i++;
      const e = this.parseComparison();
      this.skip();
      if (this.peek() !== ')') throw FEHLER();
      this.i++;
      return e;
    }
    if (c === '{') return this.parseArray();
    if (c === '"') return { type: 'str', value: this.readString() };
    if (c === '#') return { type: 'err', code: this.readErrorToken() };
    if (c === '[') return this.parseStruct(undefined);
    if (c === '-' || c === '+') {
      const op = c as '+' | '-';
      this.i++;
      return { type: 'unary', op, expr: this.parsePow() };
    }
    if (/\d/.test(c)) return this.parseNumberish();
    if (c === "'") {
      const sheet = this.readQuotedSheet();
      return this.parseRefAfterSheet(sheet);
    }
    if (/[A-Za-zÄÖÜäöü_]/.test(c) || c === '$') return this.parseIdentOrRef(undefined);
    throw FEHLER();
  }

  private parseNumberish(): Expr {
    const n = this.readNumber();
    if (n === null) throw FEHLER();
    if (this.peek() === ':') {
      const h = n;
      const save = this.i;
      this.i++;
      if (/\d/.test(this.peek())) {
        const mRaw = this.readRawInt();
        if (mRaw !== null && mRaw.text.length === 2 && h <= 23 && Number(mRaw.text) <= 59) {
          let sec = 0;
          if (this.peek() === ':') {
            this.i++;
            const sRaw = this.readRawInt();
            if (sRaw && Number(sRaw.text) <= 59) sec = Number(sRaw.text);
            else throw FEHLER();
          }
          const serial = (Math.trunc(h) * 3600 + Number(mRaw.text) * 60 + sec) / 86400;
          return { type: 'num', value: serial };
        }
        if (mRaw !== null && this.peek() !== ':' && !/[A-Za-z]/.test(this.peek())) {
          const r1 = Math.trunc(h) - 1;
          const r2 = Number(mRaw.text) - 1;
          if (r1 < 0 || r2 < 0) throw FEHLER();
          const a = Math.min(r1, r2);
          const b = Math.max(r1, r2);
          return { type: 'rows', r1: a, r2: b };
        }
      }
      this.i = save;
    }
    return { type: 'num', value: n };
  }

  private parseArray(): Expr {
    if (this.peek() !== '{') throw FEHLER();
    this.i++;
    const rows: Expr[][] = [];
    let row: Expr[] = [];
    this.skip();
    if (this.peek() === '}') throw FEHLER();
    for (;;) {
      row.push(this.parseComparison());
      this.skip();
      const ch = this.peek();
      if (ch === '\\' || ch === ',' || ch === '.') {
        if (ch === '.' && /\d/.test(this.peek(1))) {
          throw FEHLER();
        }
        this.i++;
        continue;
      }
      if (ch === ';') {
        this.i++;
        rows.push(row);
        row = [];
        this.skip();
        continue;
      }
      if (ch === '}') {
        this.i++;
        rows.push(row);
        break;
      }
      throw FEHLER();
    }
    const w = Math.max(...rows.map((r) => r.length));
    for (const r of rows) while (r.length < w) r.push({ type: 'num', value: 0 });
    return { type: 'array', rows };
  }

  private parseArgList(): Expr[] {
    if (this.peek() !== '(') throw FEHLER();
    this.i++;
    const args: Expr[] = [];
    this.skip();
    if (this.peek() === ')') {
      this.i++;
      return args;
    }
    for (;;) {
      args.push(this.parseComparison());
      this.skip();
      if (this.peek() === ';' || this.peek() === ',') {
        this.i++;
        continue;
      }
      if (this.peek() === ')') {
        this.i++;
        break;
      }
      throw FEHLER();
    }
    return args;
  }

  private parseIdentOrRef(forcedSheet: string | undefined): Expr {
    this.skip();
    if (forcedSheet === undefined && this.peek() === "'") {
      const sheet = this.readQuotedSheet();
      return this.parseRefAfterSheet(sheet);
    }
    const absCol = this.peek() === '$';
    if (absCol) this.i++;
    if (!/[A-Za-zÄÖÜäöü_]/.test(this.peek())) throw FEHLER();
    const letters = this.readLetters();
    if (this.peek() === '!' && forcedSheet === undefined && !absCol && !COL.test(letters)) {
      this.i++;
      return this.parseRefAfterSheet(letters);
    }
    if (this.peek() === '.' && /[A-Za-zÄÖÜäöü]/.test(this.peek(1))) {
      const ident = letters + this.readDottedTail();
      if (this.peek() === '(') {
        return { type: 'call', name: ident.toUpperCase(), args: this.parseArgList() };
      }
      return { type: 'name', name: ident };
    }
    if (COL.test(letters)) {
      const absRow = this.peek() === '$';
      if (absRow) this.i++;
      if (/\d/.test(this.peek())) {
        const row = Number(this.readDigits()) - 1;
        const col = colToIndex(letters);
        if (row < 0 || col < 0) throw FEHLER();
        const ref: Expr = { type: 'ref', sheet: forcedSheet, row, col, absRow, absCol };
        if (this.peek() === ':') {
          this.i++;
          const other = this.parseIdentOrRef(forcedSheet);
          return { type: 'range', a: ref, b: other };
        }
        if (this.peek() === '#') {
          this.i++;
          return { type: 'spill', ref };
        }
        return ref;
      }
      if (absRow) throw FEHLER();
      if (this.peek() === ':') {
        const c1 = colToIndex(letters);
        this.i++;
        this.skip();
        const abs2 = this.peek() === '$';
        if (abs2) this.i++;
        const ident2 = this.readLetters();
        if (!COL.test(ident2)) throw FEHLER();
        const c2 = colToIndex(ident2);
        return {
          type: 'cols',
          sheet: forcedSheet,
          c1: Math.min(c1, c2),
          c2: Math.max(c1, c2),
          abs1: absCol,
          abs2,
        };
      }
      if (this.peek() === '!' && forcedSheet === undefined && !absCol) {
        this.i++;
        return this.parseRefAfterSheet(letters);
      }
    }
    let ident = letters;
    while (/[A-Za-zÄÖÜäöü0-9_]/.test(this.peek())) {
      ident += this.peek();
      this.i++;
    }
    if (absCol) throw FEHLER();
    if (this.peek() === '!' && forcedSheet === undefined) {
      this.i++;
      return this.parseRefAfterSheet(ident);
    }
    if (this.peek() === '(') {
      return { type: 'call', name: ident.toUpperCase(), args: this.parseArgList() };
    }
    if (this.peek() === '[') return this.parseStruct(ident);
    const upper = ident.toUpperCase();
    if (upper === 'WAHR' || upper === 'TRUE') return { type: 'bool', value: true };
    if (upper === 'FALSCH' || upper === 'FALSE') return { type: 'bool', value: false };
    return { type: 'name', name: ident };
  }

  private parseRefAfterSheet(sheet: string): Expr {
    this.skip();
    return this.parseIdentOrRef(sheet);
  }

  private parseStruct(table: string | undefined): Expr {
    if (this.peek() !== '[') throw FEHLER();
    this.i++;
    this.skip();
    let thisRow = false;
    if (this.peek() === '@') {
      thisRow = true;
      this.i++;
      this.skip();
    }
    if (this.peek() === '[') this.i++;
    const column = this.readBracketName();
    this.skip();
    if (this.peek() === ']') this.i++;
    this.skip();
    if (this.peek() === ']') this.i++;
    return { type: 'struct', table, column, thisRow };
  }

  private readBracketName(): string {
    this.skip();
    if (this.peek() === '"') return this.readString();
    let s = '';
    while (this.i < this.s.length && this.peek() !== ']' && this.peek() !== '[') {
      s += this.peek();
      this.i++;
    }
    s = s.trim();
    if (!s) throw FEHLER();
    return s;
  }

  private readQuotedSheet(): string {
    if (this.peek() !== "'") throw FEHLER();
    this.i++;
    let s = '';
    while (this.i < this.s.length) {
      if (this.peek() === "'") {
        if (this.peek(1) === "'") {
          s += "'";
          this.i += 2;
          continue;
        }
        this.i++;
        break;
      }
      s += this.peek();
      this.i++;
    }
    this.skip();
    if (this.peek() !== '!') throw FEHLER();
    this.i++;
    return s;
  }

  private readLetters(): string {
    let s = '';
    while (/[A-Za-zÄÖÜäöü_]/.test(this.peek())) {
      s += this.peek();
      this.i++;
    }
    if (!s) throw FEHLER();
    return s;
  }

  private readDottedTail(): string {
    let s = '';
    while (this.peek() === '.' && /[A-Za-zÄÖÜäöü]/.test(this.peek(1))) {
      s += this.peek();
      this.i++;
      s += this.readLetters();
    }
    return s;
  }

  private readString(): string {
    if (this.peek() !== '"') throw FEHLER();
    this.i++;
    let s = '';
    while (this.i < this.s.length) {
      if (this.peek() === '"') {
        if (this.peek(1) === '"') {
          s += '"';
          this.i += 2;
          continue;
        }
        this.i++;
        return s;
      }
      s += this.peek();
      this.i++;
    }
    throw FEHLER();
  }

  private readErrorToken(): string {
    const m = /^(#(?:DIV\/0!|WERT!|BEZUG!|NAME\?|NV|ZAHL!|ÜBERLAUF!|BERECH!|FEHLER!|NULL!|N\/A))/i.exec(this.s.slice(this.i));
    if (!m) throw FEHLER();
    this.i += m[1].length;
    return m[1].toUpperCase().replace('#N/A', '#NV');
  }

  private readDigits(): string {
    let s = '';
    while (/\d/.test(this.peek())) {
      s += this.peek();
      this.i++;
    }
    return s;
  }

  private readRawInt(): { text: string } | null {
    if (!/\d/.test(this.peek())) return null;
    return { text: this.readDigits() };
  }

  private readNumber(): number | null {
    const start = this.i;
    if (!/\d/.test(this.peek())) return null;
    let s = this.readDigits();
    if ((this.peek() === ',' || this.peek() === '.') && /\d/.test(this.peek(1))) {
      const sep = this.peek();
      const fracStart = this.i + 1;
      let k = fracStart;
      while (/\d/.test(this.s[k] ?? '')) k++;
      const fracLen = k - fracStart;
      const after = this.s[k] ?? '';
      const thousands =
        sep === '.' &&
        fracLen === 3 &&
        (after === '.' || after === ',') &&
        /\d/.test(this.s[k + 1] ?? '');
      if (thousands) {
        while (this.peek() === '.' && /\d{3}/.test(this.s.slice(this.i + 1, this.i + 4))) {
          this.i++;
          s += this.readDigits();
        }
        if (this.peek() === ',' && /\d/.test(this.peek(1))) {
          this.i++;
          s += '.' + this.readDigits();
        }
      } else if (sep === '.' && fracLen === 3 && (after === '' || /[+\-*/^&%<>=);,\s\\]/.test(after) || after === '}')) {
        this.i++;
        const frac = this.readDigits();
        if (/^\d{1,3}(\.\d{3})+$/.test(`${s}.${frac}`) && frac.length === 3 && !this.s.slice(start, this.i).includes(',')) {
          const whole = this.s.slice(start, this.i);
          if (/^\d{1,3}(\.\d{3})+$/.test(whole) && whole.split('.').length > 2) {
            s = whole.replace(/\./g, '');
          } else {
            s += '.' + frac;
          }
        } else {
          s += '.' + frac;
        }
      } else {
        this.i++;
        const frac = this.readDigits();
        s += '.' + frac;
      }
    }
    if ((this.peek() === 'e' || this.peek() === 'E') && /[\d+\-]/.test(this.peek(1))) {
      s += this.peek();
      this.i++;
      if (this.peek() === '+' || this.peek() === '-') {
        s += this.peek();
        this.i++;
      }
      s += this.readDigits();
    }
    const n = Number(s);
    if (!Number.isFinite(n)) {
      this.i = start;
      return null;
    }
    return n;
  }

  private matchOp(ops: string[]): string | null {
    this.skip();
    for (const op of ops) {
      if (this.s.startsWith(op, this.i)) {
        const prev = this.s[this.i - 1] ?? '';
        if ((op === '+' || op === '-') && prev === 'E') continue;
        this.i += op.length;
        return op;
      }
    }
    return null;
  }
}

const PREC: Record<string, number> = {
  '^': 5,
  '%': 6,
  '*': 4,
  '/': 4,
  '+': 3,
  '-': 3,
  '&': 2,
  '=': 1,
  '<>': 1,
  '<': 1,
  '>': 1,
  '<=': 1,
  '>=': 1,
};

export function printExpr(e: Expr, parentPrec = 0, side: 'l' | 'r' | 'n' = 'n'): string {
  switch (e.type) {
    case 'num': {
      if (Object.is(e.value, -0)) return '0';
      return String(e.value).replace('.', ',');
    }
    case 'str':
      return `"${e.value.replace(/"/g, '""')}"`;
    case 'bool':
      return e.value ? 'WAHR' : 'FALSCH';
    case 'err':
      return e.code;
    case 'ref':
      return (
        sheetPrefix(e.sheet) +
        (e.absCol ? '$' : '') +
        indexToCol(e.col) +
        (e.absRow ? '$' : '') +
        String(e.row + 1)
      );
    case 'range':
      return `${printExpr(e.a)}:${printExpr(e.b)}`;
    case 'cols':
      return sheetPrefix(e.sheet) + (e.abs1 ? '$' : '') + indexToCol(e.c1) + ':' + (e.abs2 ? '$' : '') + indexToCol(e.c2);
    case 'rows':
      return sheetPrefix(e.sheet) + String(e.r1 + 1) + ':' + String(e.r2 + 1);
    case 'name':
      return e.name;
    case 'unary': {
      const inner = printExpr(e.expr, 6, 'r');
      const s = e.op === '%' ? `${inner}%` : `${e.op}${inner}`;
      return parentPrec > 6 ? `(${s})` : s;
    }
    case 'binary': {
      const p = PREC[e.op] ?? 0;
      const l = printExpr(e.left, p, 'l');
      const r = printExpr(e.right, p, 'r');
      const s = `${l}${e.op}${r}`;
      if (p < parentPrec) return `(${s})`;
      if (p === parentPrec && side === 'r' && e.op !== '^') return `(${s})`;
      if (p === parentPrec && side === 'l' && e.op === '^') return `(${s})`;
      return s;
    }
    case 'call':
      return `${e.name}(${e.args.map((a) => printExpr(a)).join(';')})`;
    case 'invoke':
      return `${printExpr(e.fn)}(${e.args.map((a) => printExpr(a)).join(';')})`;
    case 'struct': {
      const body = `${e.thisRow ? '@' : ''}${e.column}`;
      return `${e.table ?? ''}[${body}]`;
    }
    case 'array':
      return `{${e.rows.map((r) => r.map((c) => printExpr(c)).join('\\')).join(';')}}`;
    case 'spill':
      return `${printExpr(e.ref)}#`;
    default:
      return '';
  }
}

function sheetPrefix(sheet?: string): string {
  if (!sheet) return '';
  if (/[^A-Za-z0-9_]/.test(sheet)) return `'${sheet.replace(/'/g, "''")}'!`;
  return sheet + '!';
}

export function walk(e: Expr, fn: (e: Expr) => void): void {
  fn(e);
  switch (e.type) {
    case 'range':
      walk(e.a, fn);
      walk(e.b, fn);
      break;
    case 'unary':
      walk(e.expr, fn);
      break;
    case 'binary':
      walk(e.left, fn);
      walk(e.right, fn);
      break;
    case 'call':
    case 'invoke':
      if (e.type === 'invoke') walk(e.fn, fn);
      for (const a of e.args) walk(a, fn);
      break;
    case 'array':
      for (const r of e.rows) for (const c of r) walk(c, fn);
      break;
    case 'spill':
      walk(e.ref, fn);
      break;
    default:
      break;
  }
}

/** Ersetzt einen Knoten komplett, wenn fn eine andere Referenz liefert. Kinder nur bei unverändertem Knoten. */
export function mapExpr(e: Expr, fn: (e: Expr) => Expr): Expr {
  const replaced = fn(e);
  if (replaced !== e) return replaced;
  switch (e.type) {
    case 'range': {
      const a = mapExpr(e.a, fn);
      const b = mapExpr(e.b, fn);
      return a === e.a && b === e.b ? e : { ...e, a, b };
    }
    case 'unary': {
      const expr = mapExpr(e.expr, fn);
      return expr === e.expr ? e : { ...e, expr };
    }
    case 'binary': {
      const left = mapExpr(e.left, fn);
      const right = mapExpr(e.right, fn);
      return left === e.left && right === e.right ? e : { ...e, left, right };
    }
    case 'call': {
      const args = e.args.map((a) => mapExpr(a, fn));
      return args.every((a, i) => a === e.args[i]) ? e : { ...e, args };
    }
    case 'invoke': {
      const f = mapExpr(e.fn, fn);
      const args = e.args.map((a) => mapExpr(a, fn));
      return f === e.fn && args.every((a, i) => a === e.args[i]) ? e : { ...e, fn: f, args };
    }
    case 'array': {
      const rows = e.rows.map((r) => r.map((c) => mapExpr(c, fn)));
      return { ...e, rows };
    }
    case 'spill': {
      const ref = mapExpr(e.ref, fn);
      return ref === e.ref ? e : { ...e, ref };
    }
    default:
      return e;
  }
}
