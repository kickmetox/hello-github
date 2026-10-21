export function colName(c: number): string {
  let n = c + 1;
  let s = '';
  while (n > 0) {
    const m = (n - 1) % 26;
    s = String.fromCharCode(65 + m) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
}

export function parseAddr(addr: string): { r: number; c: number } | null {
  const m = /^\$?([A-Za-z]{1,3})\$?(\d+)$/.exec(addr.trim());
  if (!m) return null;
  let n = 0;
  for (const ch of m[1].toUpperCase()) n = n * 26 + (ch.charCodeAt(0) - 64);
  const r = Number(m[2]) - 1;
  if (r < 0 || n < 1) return null;
  return { r, c: n - 1 };
}

export function cellKey(r: number, c: number): string {
  return `${r},${c}`;
}

export function shiftCoord(index: number, at: number, delta: number): number | null {
  if (delta >= 0) return index >= at ? index + delta : index;
  const n = -delta;
  if (index >= at && index < at + n) return null;
  if (index >= at + n) return index - n;
  return index;
}

export function shiftSpan(a: number, b: number, at: number, delta: number): [number, number] | null {
  const lo = Math.min(a, b);
  const hi = Math.max(a, b);
  if (delta >= 0) {
    const na = lo >= at ? lo + delta : lo;
    const nb = hi >= at ? hi + delta : hi;
    return [na, nb];
  }
  const n = -delta;
  const end = at + n;
  if (hi < at) return [lo, hi];
  if (lo >= end) return [lo - n, hi - n];
  if (lo >= at && hi < end) return null;
  const na = lo < at ? lo : at;
  const nb = hi >= end ? hi - n : at - 1;
  if (na > nb) return null;
  return [na, nb];
}
