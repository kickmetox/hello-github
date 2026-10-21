import { FError, isErr, type Scalar } from './value';

const EPOCH = Date.UTC(1899, 11, 30);

export function dateToSerial(y: number, m: number, d: number): number {
  const ms = Date.UTC(y, m - 1, d) - EPOCH;
  return Math.round(ms / 86400000);
}

export function serialToParts(serial: number): { y: number; m: number; d: number; wd: number } {
  const dt = new Date(EPOCH + Math.round(serial) * 86400000);
  return {
    y: dt.getUTCFullYear(),
    m: dt.getUTCMonth() + 1,
    d: dt.getUTCDate(),
    wd: dt.getUTCDay(),
  };
}

export function formatGeneral(n: number): string {
  if (!Number.isFinite(n)) return '#ZAHL!';
  if (Object.is(n, -0) || n === 0) return '0';
  const abs = Math.abs(n);
  if (abs >= 1e12 || (abs > 0 && abs < 1e-9)) {
    return n.toExponential(2).replace('.', ',');
  }
  const rounded = Math.round(n * 1e10) / 1e10;
  const neg = rounded < 0;
  const [a, b] = Math.abs(rounded).toString().split('.');
  const int = a;
  return (neg ? '-' : '') + int + (b ? ',' + b : '');
}

export function formatNumber(n: number, digits: number, group = true): string {
  if (!Number.isFinite(n)) return '#ZAHL!';
  const v = Math.round(n * 10 ** digits) / 10 ** digits;
  const sign = v < 0 ? '-' : '';
  const [a, b = ''] = Math.abs(v).toFixed(digits).split('.');
  const grouped = group ? a.replace(/\B(?=(\d{3})+(?!\d))/g, '.') : a;
  return sign + grouped + (digits > 0 ? ',' + b : '');
}

export function formatDate(serial: number): string {
  const p = serialToParts(serial);
  const dd = String(p.d).padStart(2, '0');
  const mm = String(p.m).padStart(2, '0');
  return `${dd}.${mm}.${p.y}`;
}

export function formatTime(serial: number): string {
  let secs = Math.round((((serial % 1) + 1) % 1) * 86400);
  if (secs === 86400) secs = 0;
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

/** Akzeptiert 1.234,56 / 1,234.56 / 1234.56 / 1234,56 / 1.5 / (1.234,56). */
export function parseNumberDe(input: string): number | null {
  let s = input.trim().replace(/\s|\u00a0/g, '');
  if (!s) return null;
  let neg = false;
  if (s.startsWith('(') && s.endsWith(')')) {
    neg = true;
    s = s.slice(1, -1);
  }
  if (s.startsWith('+')) s = s.slice(1);
  else if (s.startsWith('-')) {
    neg = !neg;
    s = s.slice(1);
  }
  if (/^\d{1,3}(\.\d{3})+(,\d+)?$/.test(s)) s = s.replace(/\./g, '').replace(',', '.');
  else if (/^\d{1,3}(,\d{3})+(\.\d+)?$/.test(s)) s = s.replace(/,/g, '');
  else if (/^\d+(,\d+)?$/.test(s)) s = s.replace(',', '.');
  else if (/^\d+(\.\d+)?$/.test(s)) {
    /* english decimal */
  } else if (/^\d+([.,]\d+)?[eE][+-]?\d+$/.test(s)) s = s.replace(',', '.');
  else return null;
  const n = Number(s);
  if (!Number.isFinite(n)) return null;
  return neg ? -n : n;
}

export function parseDateStrict(input: string): number | null {
  const m = /^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$/.exec(input.trim());
  if (!m) return null;
  let y = Number(m[3]);
  const month = Number(m[2]);
  const d = Number(m[1]);
  if (y < 100) y += y >= 50 ? 1900 : 2000;
  if (month < 1 || month > 12 || d < 1 || d > 31) return null;
  const serial = dateToSerial(y, month, d);
  const back = serialToParts(serial);
  if (back.y !== y || back.m !== month || back.d !== d) return null;
  return serial;
}

export function parseTimeStrict(input: string): number | null {
  const m = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(input.trim());
  if (!m) return null;
  const h = Number(m[1]);
  const min = Number(m[2]);
  const s = m[3] ? Number(m[3]) : 0;
  if (h > 23 || min > 59 || s > 59) return null;
  return (h * 3600 + min * 60 + s) / 86400;
}

export function parseDateTimeStrict(input: string): number | null {
  const m = /^(\d{1,2}\.\d{1,2}\.\d{2,4})\s+(\d{1,2}:\d{2}(?::\d{2})?)$/.exec(input.trim());
  if (!m) return null;
  const d = parseDateStrict(m[1]);
  const t = parseTimeStrict(m[2]);
  if (d === null || t === null) return null;
  return d + t;
}

export function parseLiteral(raw: string): Scalar {
  const t = raw.trim();
  if (t === '') return null;
  if (/^(wahr|true)$/i.test(t)) return true;
  if (/^(falsch|false)$/i.test(t)) return false;
  if (t.endsWith('%')) {
    const n = parseNumberDe(t.slice(0, -1));
    if (n !== null) return n / 100;
  }
  if (/€\s*$/.test(t) || /^\s*€/.test(t)) {
    const n = parseNumberDe(t.replace(/€/g, ''));
    if (n !== null) return n;
  }
  const dt = parseDateTimeStrict(t);
  if (dt !== null) return dt;
  if (/^\d{1,2}\.\d{1,2}\.\d{2,4}$/.test(t)) {
    const d = parseDateStrict(t);
    if (d !== null) return d;
  }
  if (/^\d{1,2}:\d{2}(:\d{2})?$/.test(t)) {
    const tm = parseTimeStrict(t);
    if (tm !== null) return tm;
  }
  const n = parseNumberDe(t);
  if (n !== null) return n;
  return t;
}

export type NumFmt =
  | 'g'
  | 'n0'
  | 'n1'
  | 'n2'
  | 'n3'
  | 'n4'
  | 'c0'
  | 'c2'
  | 'p0'
  | 'p1'
  | 'p2'
  | 'd'
  | 't'
  | 'dt'
  | 'e'
  | '@';

export function formatByCode(value: Scalar, fmt: NumFmt | undefined, raw?: string): string {
  if (value === null || value === '') return '';
  if (typeof value === 'boolean') return value ? 'WAHR' : 'FALSCH';
  if (typeof value === 'string') return value;
  if (isErr(value)) return (value as FError).code;
  const f = fmt && fmt !== 'g' ? fmt : undefined;
  if (!f) {
    if (raw && /^\d{1,2}\.\d{1,2}\.\d{2,4}/.test(raw.trim()) && value > 20000 && value < 80000) return formatDate(value);
    if (raw && /^\d{1,2}:\d{2}/.test(raw.trim()) && value >= 0 && value < 2 && !Number.isInteger(value)) return formatTime(value);
    return formatGeneral(value);
  }
  if (f === '@') return raw ?? formatGeneral(value);
  if (f === 'd') return formatDate(value);
  if (f === 't') return formatTime(value);
  if (f === 'dt') return `${formatDate(value)} ${formatTime(value)}`;
  if (f === 'e') return value.toExponential(2).replace('.', ',');
  if (f.startsWith('p')) {
    const d = Number(f.slice(1));
    return formatNumber(value * 100, d, false) + ' %';
  }
  if (f.startsWith('c')) {
    const d = Number(f.slice(1));
    return formatNumber(value, d, true) + ' €';
  }
  if (f.startsWith('n')) {
    const d = Number(f.slice(1));
    return formatNumber(value, d, true);
  }
  return formatGeneral(value);
}

export function bumpDecimals(fmt: NumFmt | undefined, dir: 1 | -1): NumFmt {
  const f = fmt ?? 'n0';
  const m = /^([ncp])(\d)$/.exec(f);
  if (!m) return dir > 0 ? 'n2' : 'n0';
  const d = Math.max(0, Math.min(4, Number(m[2]) + dir));
  return `${m[1]}${d}` as NumFmt;
}

export function isoWeek(serial: number): number {
  const p = serialToParts(serial);
  const date = new Date(Date.UTC(p.y, p.m - 1, p.d));
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  return Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

export function addMonths(serial: number, months: number): number {
  const p = serialToParts(serial);
  const total = p.m - 1 + months;
  const y = p.y + Math.floor(total / 12);
  const m = ((total % 12) + 12) % 12;
  const dim = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
  const d = Math.min(p.d, dim);
  return dateToSerial(y, m + 1, d);
}

export function endOfMonth(serial: number, months: number): number {
  const shifted = addMonths(serial, months);
  const p = serialToParts(shifted);
  const dim = new Date(Date.UTC(p.y, p.m, 0)).getUTCDate();
  return dateToSerial(p.y, p.m, dim);
}
