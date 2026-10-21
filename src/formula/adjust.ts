import { type Expr, mapExpr, parseFormula, printExpr } from './parser';
import { FError } from './value';

function clampRef(e: Expr): Expr {
  if (e.type === 'ref' && (e.row < 0 || e.col < 0 || e.row > 1048575 || e.col > 16383)) {
    return { type: 'err', code: '#BEZUG!' };
  }
  return e;
}

/** Relative Bezüge beim Kopieren / Auto-Ausfüllen verschieben. */
export function adjustFormulaCopy(formula: string, dRow: number, dCol: number): string {
  if (!formula.startsWith('=')) return formula;
  let ast: Expr;
  try {
    ast = parseFormula(formula.slice(1));
  } catch {
    return formula;
  }
  const next = mapExpr(ast, (e) => {
    if (e.type === 'ref') {
      return clampRef({
        ...e,
        row: e.absRow ? e.row : e.row + dRow,
        col: e.absCol ? e.col : e.col + dCol,
      });
    }
    if (e.type === 'cols' && dCol) {
      return {
        ...e,
        c1: e.abs1 ? e.c1 : e.c1 + dCol,
        c2: e.abs2 ? e.c2 : e.c2 + dCol,
      };
    }
    if (e.type === 'rows' && dRow) {
      return { ...e, r1: e.r1 + dRow, r2: e.r2 + dRow };
    }
    return e;
  });
  try {
    return '=' + printExpr(next);
  } catch {
    return formula;
  }
}

function shiftIndex(index: number, at: number, count: number): number | null {
  if (count >= 0) return index >= at ? index + count : index;
  const n = -count;
  const end = at + n;
  if (index >= at && index < end) return null;
  if (index >= end) return index - n;
  return index;
}

function shiftRangeEnds(a: number, b: number, at: number, count: number): [number, number] | null {
  if (count >= 0) {
    const na = a >= at ? a + count : a;
    const nb = b >= at ? b + count : b;
    return [na, nb];
  }
  const n = -count;
  const end = at + n;
  const inside = (x: number) => x >= at && x < end;
  if (a >= end) return [a - n, b - n];
  if (b < at) return [a, b];
  if (inside(a) && inside(b)) return null;
  const na = inside(a) ? at : a > end ? a - n : a;
  let nb = inside(b) ? at - 1 : b >= end ? b - n : b;
  if (a < at && inside(b)) nb = at - 1;
  if (na > nb) return null;
  return [na, nb];
}

/**
 * Zeilen/Spalten einfügen (count>0) oder löschen (count<0).
 * Nur Bezüge auf `editedSheet` werden verändert. `homeSheet` ist das Blatt der Formel.
 */
export function adjustFormulaStructure(
  formula: string,
  homeSheet: string,
  editedSheet: string,
  axis: 'row' | 'col',
  at: number,
  count: number,
): string {
  if (!formula.startsWith('=')) return formula;
  let ast: Expr;
  try {
    ast = parseFormula(formula.slice(1));
  } catch {
    return formula;
  }
  const hit = (sheet?: string) => (sheet ?? homeSheet).toLowerCase() === editedSheet.toLowerCase();
  let broken = false;
  const next = mapExpr(ast, (e) => {
    if (e.type === 'ref' && hit(e.sheet)) {
      if (axis === 'row') {
        const row = shiftIndex(e.row, at, count);
        if (row === null) {
          broken = true;
          return { type: 'err', code: '#BEZUG!' };
        }
        return { ...e, row };
      }
      const col = shiftIndex(e.col, at, count);
      if (col === null) {
        broken = true;
        return { type: 'err', code: '#BEZUG!' };
      }
      return { ...e, col };
    }
    if (e.type === 'rows' && axis === 'row' && hit(e.sheet)) {
      const span = shiftRangeEnds(e.r1, e.r2, at, count);
      if (!span) {
        broken = true;
        return { type: 'err', code: '#BEZUG!' };
      }
      return { ...e, r1: span[0], r2: span[1] };
    }
    if (e.type === 'cols' && axis === 'col' && hit(e.sheet)) {
      const span = shiftRangeEnds(e.c1, e.c2, at, count);
      if (!span) {
        broken = true;
        return { type: 'err', code: '#BEZUG!' };
      }
      return { ...e, c1: span[0], c2: span[1] };
    }
    if (e.type === 'range' && e.a.type === 'ref' && e.b.type === 'ref' && hit(e.a.sheet) && hit(e.b.sheet) && (e.a.sheet ?? '') === (e.b.sheet ?? '')) {
      if (axis === 'row') {
        const span = shiftRangeEnds(Math.min(e.a.row, e.b.row), Math.max(e.a.row, e.b.row), at, count);
        if (!span) {
          broken = true;
          return { type: 'err', code: '#BEZUG!' };
        }
        const top = e.a.row <= e.b.row ? e.a : e.b;
        const bot = e.a.row <= e.b.row ? e.b : e.a;
        const a = { ...top, row: span[0] };
        const b = { ...bot, row: span[1] };
        return { type: 'range', a, b };
      }
      const span = shiftRangeEnds(Math.min(e.a.col, e.b.col), Math.max(e.a.col, e.b.col), at, count);
      if (!span) {
        broken = true;
        return { type: 'err', code: '#BEZUG!' };
      }
      const left = e.a.col <= e.b.col ? e.a : e.b;
      const right = e.a.col <= e.b.col ? e.b : e.a;
      return { type: 'range', a: { ...left, col: span[0] }, b: { ...right, col: span[1] } };
    }
    return e;
  });
  if (broken && next.type === 'err') return '=' + next.code;
  try {
    return '=' + printExpr(next);
  } catch (e) {
    if (e instanceof FError) return '=' + e.code;
    return formula;
  }
}
