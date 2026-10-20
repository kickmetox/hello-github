import * as XLSX from 'xlsx';
import { translateFormula } from '../formula/translate';
import { formatByCode, parseLiteral } from '../formula/format';
import { colName } from '../model/addr';
import { emptySheet, emptyWorkbook, normalizeWorkbook, type Cell, type Sheet, type Workbook } from '../model/types';
import type { Computed } from '../formula/engine';

function download(name: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export function saveRggrid(wb: Workbook, passwordJson?: string): void {
  const body = passwordJson ?? JSON.stringify(wb);
  download(`${safeName(wb.title)}.rggrid`, new Blob([body], { type: 'application/json' }));
}

export function saveCsv(sheet: Sheet, computed: Map<string, Computed>, valuesOnly: boolean): void {
  const lines: string[] = [];
  const used = usedBounds(sheet);
  for (let r = 0; r <= used.r2; r++) {
    const cols: string[] = [];
    for (let c = 0; c <= used.c2; c++) {
      const cell = sheet.cells[`${r},${c}`];
      const comp = computed.get(`${sheet.name}!${r},${c}`);
      let text = '';
      if (!valuesOnly && cell?.raw?.startsWith('=')) text = cell.raw;
      else if (comp && !comp.error && !comp.spark) text = formatByCode(comp.value, cell?.style?.numFmt, cell?.raw);
      else text = cell?.raw ?? '';
      cols.push(csvEscape(text));
    }
    lines.push(cols.join(';'));
  }
  const bom = '\ufeff';
  download(`${safeName(sheet.name)}.csv`, new Blob([bom + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' }));
}

export function workbookToXlsx(wb: Workbook, computed: Map<string, Computed>): void {
  const book = XLSX.utils.book_new();
  for (const sheet of wb.sheets) {
    const used = usedBounds(sheet);
    const rows: XLSX.CellObject[][] = [];
    for (let r = 0; r <= used.r2; r++) {
      const row: XLSX.CellObject[] = [];
      for (let c = 0; c <= used.c2; c++) {
        row.push(cellToXlsx(sheet, r, c, computed));
      }
      rows.push(row);
    }
    const ws = XLSX.utils.aoa_to_sheet(rows.map((row) => row.map((cell) => cell.v ?? null)));
    for (let r = 0; r <= used.r2; r++) {
      for (let c = 0; c <= used.c2; c++) {
        const addr = XLSX.utils.encode_cell({ r, c });
        const src = rows[r][c];
        if (src.f || src.t) ws[addr] = src;
      }
    }
    ws['!ref'] = XLSX.utils.encode_range({ s: { r: 0, c: 0 }, e: { r: used.r2, c: used.c2 } });
    const cols = [];
    for (let c = 0; c <= used.c2; c++) cols.push({ wpx: sheet.colWidths[c] ?? 96 });
    ws['!cols'] = cols;
    XLSX.utils.book_append_sheet(book, ws, sheet.name.slice(0, 31) || 'Tabelle');
  }
  XLSX.writeFile(book, `${safeName(wb.title)}.xlsx`);
}

export function workbookToXls(wb: Workbook, computed: Map<string, Computed>): void {
  const book = buildBook(wb, computed);
  XLSX.writeFile(book, `${safeName(wb.title)}.xls`, { bookType: 'biff8' });
}

export function workbookToOds(wb: Workbook, computed: Map<string, Computed>): void {
  const book = buildBook(wb, computed);
  XLSX.writeFile(book, `${safeName(wb.title)}.ods`, { bookType: 'ods' });
}

function buildBook(wb: Workbook, computed: Map<string, Computed>): XLSX.WorkBook {
  const book = XLSX.utils.book_new();
  for (const sheet of wb.sheets) {
    const used = usedBounds(sheet);
    const aoa: (string | number | boolean | null)[][] = [];
    for (let r = 0; r <= used.r2; r++) {
      const row: (string | number | boolean | null)[] = [];
      for (let c = 0; c <= used.c2; c++) {
        const cell = cellToXlsx(sheet, r, c, computed);
        row.push((cell.v as string | number | boolean | null) ?? null);
      }
      aoa.push(row);
    }
    const ws = XLSX.utils.aoa_to_sheet(aoa);
    for (let r = 0; r <= used.r2; r++) {
      for (let c = 0; c <= used.c2; c++) {
        const packed = cellToXlsx(sheet, r, c, computed);
        if (packed.f) ws[XLSX.utils.encode_cell({ r, c })] = packed;
      }
    }
    XLSX.utils.book_append_sheet(book, ws, sheet.name.slice(0, 31) || 'Tabelle');
  }
  return book;
}

function cellToXlsx(sheet: Sheet, r: number, c: number, computed: Map<string, Computed>): XLSX.CellObject {
  const cell = sheet.cells[`${r},${c}`];
  const comp = computed.get(`${sheet.name}!${r},${c}`);
  if (cell?.raw?.startsWith('=')) {
    const en = translateFormula(cell.raw, 'de-en');
    const v = comp && !comp.error && (typeof comp.value === 'number' || typeof comp.value === 'string' || typeof comp.value === 'boolean') ? comp.value : undefined;
    const out: XLSX.CellObject = { t: typeof v === 'number' ? 'n' : 's', f: en.slice(1) };
    if (v !== undefined && v !== null) out.v = v;
    return out;
  }
  const raw = cell?.raw ?? '';
  if (!raw) return { t: 's', v: '' };
  const lit = parseLiteral(raw);
  if (typeof lit === 'number') return { t: 'n', v: lit };
  if (typeof lit === 'boolean') return { t: 'b', v: lit };
  return { t: 's', v: raw };
}

export function parseWorkbookFile(name: string, data: ArrayBuffer | string): Workbook | 'sealed' {
  const lower = name.toLowerCase();
  if (typeof data === 'string' || lower.endsWith('.rggrid') || lower.endsWith('.json')) {
    const text = typeof data === 'string' ? data : new TextDecoder().decode(data);
    if (text.includes('"format":"reckongrid-aes"') || text.includes('"reckongrid-aes"')) return 'sealed';
    if (lower.endsWith('.rggrid') || text.includes('"sheets"')) {
      return normalizeWorkbook(JSON.parse(text) as Workbook);
    }
  }
  if (typeof data === 'string' || lower.endsWith('.csv') || lower.endsWith('.txt') || lower.endsWith('.tsv')) {
    const text = typeof data === 'string' ? data : new TextDecoder().decode(data);
    return csvWorkbook(text, name.replace(/\.[^.]+$/, '') || 'Import');
  }
  const book = XLSX.read(data, { type: 'array', cellDates: true, cellFormula: true });
  const wb = emptyWorkbook(name.replace(/\.[^.]+$/, '') || 'Import');
  wb.sheets = book.SheetNames.map((sheetName) => sheetFromXlsx(sheetName, book.Sheets[sheetName]));
  wb.active = 0;
  return normalizeWorkbook(wb);
}

export function csvWorkbook(text: string, title: string): Workbook {
  const wb = emptyWorkbook(title || 'Import');
  const sheet = wb.sheets[0];
  sheet.name = 'Import';
  const rows = parseCsv(text);
  rows.forEach((row, r) => {
    row.forEach((value, c) => {
      if (value === '') return;
      const cell: Cell = { raw: coerceRaw(value), rev: 1 };
      sheet.cells[`${r},${c}`] = cell;
    });
  });
  sheet.rows = Math.max(200, rows.length + 20);
  sheet.cols = Math.max(26, rows.reduce((m, row) => Math.max(m, row.length), 0) + 2);
  return wb;
}

export function parseCsv(text: string): string[][] {
  const src = text.replace(/^\ufeff/, '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const sample = src.slice(0, 2000);
  const semi = (sample.match(/;/g) ?? []).length;
  const comma = (sample.match(/,/g) ?? []).length;
  const tab = (sample.match(/\t/g) ?? []).length;
  const delim = tab > semi && tab > comma ? '\t' : semi >= comma ? ';' : ',';
  const rows: string[][] = [];
  let row: string[] = [];
  let cur = '';
  let q = false;
  for (let i = 0; i < src.length; i++) {
    const ch = src[i];
    if (q) {
      if (ch === '"') {
        if (src[i + 1] === '"') {
          cur += '"';
          i++;
        } else q = false;
      } else cur += ch;
    } else if (ch === '"') q = true;
    else if (ch === delim) {
      row.push(cur);
      cur = '';
    } else if (ch === '\n') {
      row.push(cur);
      rows.push(row);
      row = [];
      cur = '';
    } else cur += ch;
  }
  if (cur.length || row.length) {
    row.push(cur);
    rows.push(row);
  }
  return rows.filter((r) => r.some((c) => c !== ''));
}

export function htmlTable(html: string): string[][] {
  const table = /<table[\s\S]*?<\/table>/i.exec(html)?.[0] ?? html;
  const rows: string[][] = [];
  for (const rm of table.matchAll(/<tr[\s\S]*?<\/tr>/gi)) {
    const cols: string[] = [];
    for (const cm of rm[0].matchAll(/<t[dh][^>]*>([\s\S]*?)<\/t[dh]>/gi)) {
      cols.push(cm[1].replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').trim());
    }
    if (cols.length) rows.push(cols);
  }
  return rows;
}

export function jsonTable(text: string): string[][] {
  const data = JSON.parse(text) as unknown;
  const list = Array.isArray(data) ? data : Array.isArray((data as { data?: unknown }).data) ? (data as { data: unknown[] }).data : null;
  if (!list) throw new Error('JSON enthält keine Liste von Datensätzen.');
  const objects = list.filter((x) => x && typeof x === 'object' && !Array.isArray(x)) as Record<string, unknown>[];
  if (!objects.length) {
    if (list.every((x) => Array.isArray(x))) return (list as unknown[][]).map((row) => row.map((v) => String(v ?? '')));
    throw new Error('JSON-Liste ist leer.');
  }
  const headers: string[] = [];
  for (const obj of objects) for (const k of Object.keys(obj)) if (!headers.includes(k)) headers.push(k);
  return [headers, ...objects.map((obj) => headers.map((h) => String(obj[h] ?? '')))];
}

function sheetFromXlsx(name: string, ws: XLSX.WorkSheet): Sheet {
  const sheet = emptySheet(name);
  const ref = ws['!ref'];
  if (!ref) return sheet;
  const range = XLSX.utils.decode_range(ref);
  for (let r = range.s.r; r <= range.e.r; r++) {
    for (let c = range.s.c; c <= range.e.c; c++) {
      const cell = ws[XLSX.utils.encode_cell({ r, c })] as XLSX.CellObject | undefined;
      if (!cell) continue;
      const raw = xlsxRaw(cell);
      if (!raw) continue;
      sheet.cells[`${r},${c}`] = { raw, rev: 1 };
    }
  }
  sheet.rows = Math.max(200, range.e.r + 30);
  sheet.cols = Math.max(26, range.e.c + 4);
  const cols = ws['!cols'] as { wpx?: number; wch?: number }[] | undefined;
  cols?.forEach((col, i) => {
    if (col?.wpx) sheet.colWidths[i] = col.wpx;
    else if (col?.wch) sheet.colWidths[i] = Math.round(col.wch * 8);
  });
  return sheet;
}

function xlsxRaw(cell: XLSX.CellObject): string {
  if (cell.f) {
    const formula = cell.f.startsWith('=') ? cell.f : `=${cell.f}`;
    return translateFormula(formula, 'en-de');
  }
  if (cell.v instanceof Date) {
    const d = cell.v;
    const dd = String(d.getUTCDate()).padStart(2, '0');
    const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
    return `${dd}.${mm}.${d.getUTCFullYear()}`;
  }
  if (typeof cell.v === 'number') return String(cell.v);
  if (typeof cell.v === 'boolean') return cell.v ? 'WAHR' : 'FALSCH';
  return cell.v == null ? '' : String(cell.v);
}

function coerceRaw(value: string): string {
  const t = value.trim();
  if (t.startsWith('=') && /[A-Za-z]+\(/.test(t) && t.includes(',') && !t.includes(';')) return translateFormula(t, 'en-de');
  return t;
}

function csvEscape(value: string): string {
  if (/[";\n]/.test(value)) return `"${value.replace(/"/g, '""')}"`;
  return value;
}

function usedBounds(sheet: Sheet): { r2: number; c2: number } {
  let r2 = 0;
  let c2 = 0;
  for (const key of Object.keys(sheet.cells)) {
    const [r, c] = key.split(',').map(Number);
    if (sheet.cells[key]?.raw) {
      r2 = Math.max(r2, r);
      c2 = Math.max(c2, c);
    }
  }
  return { r2, c2 };
}

function safeName(name: string): string {
  return (name || 'ReckonGrid').replace(/[\\/:*?"<>|]+/g, '_').slice(0, 80);
}

export function addrLabel(r: number, c: number): string {
  return `${colName(c)}${r + 1}`;
}
