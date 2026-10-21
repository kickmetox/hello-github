import { parseDateStrict, parseDateTimeStrict, parseNumberDe } from './format';
import type { Scalar } from './value';

function coerceRhs(raw: string): Scalar {
  const t = raw.trim();
  if (t === '') return '';
  if (/^(wahr|true)$/i.test(t)) return true;
  if (/^(falsch|false)$/i.test(t)) return false;
  const dt = parseDateTimeStrict(t) ?? parseDateStrict(t);
  if (dt !== null && /^\d{1,2}\.\d{1,2}\.\d{2,4}/.test(t)) return dt;
  const n = parseNumberDe(t);
  if (n !== null) return n;
  return t;
}

function wildcardToRegExp(pat: string): RegExp {
  let out = '^';
  for (let i = 0; i < pat.length; i++) {
    const c = pat[i];
    if (c === '~' && i + 1 < pat.length) {
      out += pat[++i].replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    } else if (c === '*') out += '.*';
    else if (c === '?') out += '.';
    else out += c.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
  return new RegExp(out + '$', 'i');
}

function asNumber(v: Scalar): number | null {
  if (typeof v === 'number') return v;
  if (typeof v === 'boolean') return v ? 1 : 0;
  if (typeof v === 'string') return parseNumberDe(v);
  return null;
}

function equalLoose(value: Scalar, rhs: Scalar): boolean {
  if (typeof rhs === 'number') {
    if (value === null || value === '') return false;
    const n = asNumber(value);
    return n !== null && Math.abs(n - rhs) <= 1e-9 * Math.max(1, Math.abs(rhs));
  }
  if (typeof rhs === 'boolean') return value === rhs;
  if (rhs === null || rhs === '') return value === null || value === '';
  if (typeof rhs === 'string') {
    if (value === null) return rhs === '';
    return String(value).toLocaleLowerCase('de-DE') === rhs.toLocaleLowerCase('de-DE');
  }
  return false;
}

function compare(value: Scalar, rhs: Scalar): number {
  if (typeof value === 'number' && typeof rhs === 'number') return value === rhs ? 0 : value < rhs ? -1 : 1;
  const vn = value === null || value === '' ? null : asNumber(value);
  const rn = rhs === null || rhs === '' ? null : asNumber(rhs);
  if (vn !== null && rn !== null && typeof rhs !== 'boolean' && typeof value !== 'boolean') {
    return vn === rn ? 0 : vn < rn ? -1 : 1;
  }
  const a = value === null ? '' : String(value).toLocaleLowerCase('de-DE');
  const b = rhs === null ? '' : String(rhs).toLocaleLowerCase('de-DE');
  return a < b ? -1 : a > b ? 1 : 0;
}

/** Excel-ähnlicher Kriterienvergleich für SUMMEWENN, ZÄHLENWENN und D-Funktionen. */
export function matchCriteria(value: Scalar, criteria: Scalar): boolean {
  if (criteria === null || criteria === '') return value === null || value === '';
  if (typeof criteria === 'number' || typeof criteria === 'boolean') return equalLoose(value, criteria);
  if (typeof criteria !== 'string') return false;
  const op = /^(<=|>=|<>|=|<|>)([\s\S]*)$/.exec(criteria.trim());
  if (op) {
    const rhs = coerceRhs(op[2]);
    if (value === null || value === '') {
      if (op[1] === '=') return rhs === '' || rhs === null;
      if (op[1] === '<>') return !(rhs === '' || rhs === null);
      return false;
    }
    const c = compare(value, rhs);
    switch (op[1]) {
      case '=':
        return c === 0;
      case '<>':
        return c !== 0;
      case '<':
        return c < 0;
      case '>':
        return c > 0;
      case '<=':
        return c <= 0;
      case '>=':
        return c >= 0;
      default:
        return false;
    }
  }
  if (/[*?]/.test(criteria)) return wildcardToRegExp(criteria).test(value === null ? '' : String(value));
  return equalLoose(value, coerceRhs(criteria));
}
