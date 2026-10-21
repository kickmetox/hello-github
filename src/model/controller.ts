import { calculate, type Computed } from '../formula/engine';
import { adjustFormulaCopy, adjustFormulaStructure } from '../formula/adjust';
import { tryParseFormula, walk } from '../formula/parser';
import { formatByCode, formatNumber, parseLiteral, type NumFmt } from '../formula/format';
import { cellKey, colName, parseAddr, shiftCoord, shiftSpan } from './addr';
import {
  emptySheet,
  normalizeWorkbook,
  type Cell,
  type ChartType,
  type CondRule,
  type Macro,
  type Sheet,
  type Style,
  type Validation,
  type Workbook,
} from './types';
import { TEMPLATES } from './templates';
import { sha256 } from '../io/crypto';
import { htmlTable, jsonTable, parseCsv } from '../io/files';
import { runJavaScript, runPython, runVba, type ScriptApi } from '../script/runners';

export type RibbonTab = 'datei' | 'start' | 'einfuegen' | 'layout' | 'formeln' | 'daten' | 'ueberpruefen' | 'ansicht';

export interface CellPos {
  r: number;
  c: number;
}

export interface Bounds {
  r1: number;
  c1: number;
  r2: number;
  c2: number;
}

export interface Paint {
  fill?: string;
  color?: string;
  bar?: number;
}

export interface GridView {
  tab: RibbonTab;
  theme: 'dark' | 'light';
  zoom: number;
  dialog: { type: string; [key: string]: unknown } | null;
  status: string;
  editing: boolean;
  editValue: string;
  editAt: CellPos | null;
  pointing: { r: number; c: number; base: string } | null;
  anchor: CellPos;
  focus: CellPos;
  showFormulas: boolean;
  recording: boolean;
  macroLines: string[];
  collab: boolean;
  peers: { id: string; name: string; color: string; sheet: string; r: number; c: number }[];
  selfId: string;
  trace: CellPos[];
  painter: Style | null;
  menu: { x: number; y: number } | null;
  log: string[];
  dirty: boolean;
}

interface PutOpt {
  undo?: boolean;
  recalc?: boolean;
  record?: boolean;
  emit?: boolean;
  validation?: boolean;
}

interface ClipCell {
  dr: number;
  dc: number;
  cell: Cell;
}

const STORE = 'reckongrid-v1';

function defaultView(): GridView {
  return {
    tab: 'start',
    theme: 'dark',
    zoom: 1,
    dialog: null,
    status: 'Bereit',
    editing: false,
    editValue: '',
    editAt: null,
    pointing: null,
    anchor: { r: 0, c: 0 },
    focus: { r: 0, c: 0 },
    showFormulas: false,
    recording: false,
    macroLines: [],
    collab: false,
    peers: [],
    selfId: `p${Math.random().toString(36).slice(2, 8)}`,
    trace: [],
    painter: null,
    menu: null,
    log: [],
    dirty: false,
  };
}

let seq = 1;
const uid = () => `g${Date.now().toString(36)}${seq++}`;

export class GridController {
  wb: Workbook;
  view: GridView;
  computed: Map<string, Computed> = new Map();
  paint: Map<string, Paint> = new Map();
  private ver = 0;
  private history: string[] = [];
  private future: string[] = [];
  private listeners = new Set<() => void>();
  private clip: { cut: boolean; sheet: string; r: number; c: number; cells: ClipCell[] } | null = null;
  private lastTsv = '';
  private channel: BroadcastChannel | null = null;
  private remote = false;
  private persistTimer = 0;

  constructor(wb: Workbook) {
    this.wb = normalizeWorkbook(wb);
    this.view = defaultView();
    this.recalc(true);
  }

  subscribe = (fn: () => void): (() => void) => {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  };

  getSnapshot = (): number => this.ver;

  sheet(): Sheet {
    return this.wb.sheets[this.wb.active] ?? this.wb.sheets[0];
  }

  bounds(): Bounds {
    const a = this.view.anchor;
    const f = this.view.focus;
    return { r1: Math.min(a.r, f.r), c1: Math.min(a.c, f.c), r2: Math.max(a.r, f.r), c2: Math.max(a.c, f.c) };
  }

  focusAddr(): string {
    const f = this.view.focus;
    return `${colName(f.c)}${f.r + 1}`;
  }

  comp(r: number, c: number, sheet = this.sheet()): Computed | undefined {
    return this.computed.get(`${sheet.name}!${r},${c}`);
  }

  display(r: number, c: number, sheet = this.sheet()): string {
    const cell = sheet.cells[cellKey(r, c)];
    const computed = this.comp(r, c, sheet);
    if (this.view.showFormulas && cell?.raw.startsWith('=')) return cell.raw;
    if (!computed) return cell?.raw ?? '';
    if (computed.error) return computed.error;
    if (computed.spark) return '';
    if (computed.href) return computed.label || computed.href;
    return formatByCode(computed.value, cell?.style?.numFmt, cell?.raw);
  }

  numAt(r: number, c: number, sheet = this.sheet()): number | null {
    const computed = this.comp(r, c, sheet);
    if (!computed || computed.error || typeof computed.value !== 'number' || !Number.isFinite(computed.value)) return null;
    return computed.value;
  }

  hiddenRows(sheet = this.sheet()): Set<number> {
    const hidden = new Set<number>();
    for (const [key, height] of Object.entries(sheet.rowHeights)) if (height === 0) hidden.add(Number(key));
    if (sheet.filter) {
      const filter = sheet.filter;
      for (let r = filter.r1 + 1; r <= filter.r2; r++) {
        for (const [col, allowed] of Object.entries(filter.selected)) {
          if (!allowed) continue;
          const text = this.filterText(sheet, r, Number(col));
          if (!allowed.includes(text)) {
            hidden.add(r);
            break;
          }
        }
      }
    }
    for (const group of sheet.groups) {
      if (!group.collapsed) continue;
      for (let r = group.start; r <= group.end; r++) hidden.add(r);
    }
    return hidden;
  }

  usedBounds(sheet = this.sheet()): Bounds {
    let r1 = Infinity;
    let c1 = Infinity;
    let r2 = 0;
    let c2 = 0;
    let any = false;
    for (const [key, cell] of Object.entries(sheet.cells)) {
      if (!cell?.raw && !cell?.comment) continue;
      const [r, c] = key.split(',').map(Number);
      any = true;
      r1 = Math.min(r1, r);
      c1 = Math.min(c1, c);
      r2 = Math.max(r2, r);
      c2 = Math.max(c2, c);
    }
    return any ? { r1, c1, r2, c2 } : { r1: 0, c1: 0, r2: 0, c2: 0 };
  }

  stats(): { count: number; nums: number; sum: number } {
    const b = this.bounds();
    let count = 0;
    let nums = 0;
    let sum = 0;
    for (let r = b.r1; r <= b.r2; r++) {
      for (let c = b.c1; c <= b.c2; c++) {
        if (this.display(r, c)) count++;
        const n = this.numAt(r, c);
        if (n !== null) {
          nums++;
          sum += n;
        }
      }
    }
    return { count, nums, sum };
  }

  mergeAt(r: number, c: number): { r1: number; c1: number; r2: number; c2: number; origin: boolean } | null {
    const merge = this.sheet().merges.find((item) => r >= item.r1 && r <= item.r2 && c >= item.c1 && c <= item.c2);
    if (!merge) return null;
    return { ...merge, origin: merge.r1 === r && merge.c1 === c };
  }

  setTab(tab: RibbonTab): void {
    this.view.tab = tab;
    this.view.menu = null;
    this.emit();
  }

  setZoom(zoom: number): void {
    this.view.zoom = Math.max(0.5, Math.min(2, zoom));
    this.emit();
  }

  toggleTheme(): void {
    this.view.theme = this.view.theme === 'dark' ? 'light' : 'dark';
    this.emit();
  }

  toggleFormulas(): void {
    this.view.showFormulas = !this.view.showFormulas;
    this.emit();
  }

  toggleCalc(): void {
    this.wb.calc = this.wb.calc === 'auto' ? 'manual' : 'auto';
    if (this.wb.calc === 'auto') this.recalc(true);
    this.view.status = this.wb.calc === 'auto' ? 'Automatische Berechnung' : 'Manuelle Berechnung';
    this.emit();
  }

  openDialog(type: string, extra: Record<string, unknown> = {}): void {
    this.view.dialog = { type, ...extra };
    this.view.menu = null;
    this.emit();
  }

  closeDialog(): void {
    this.view.dialog = null;
    this.emit();
  }

  openMenu(x: number, y: number): void {
    this.view.menu = { x, y };
    this.emit();
  }

  closeMenu(): void {
    if (!this.view.menu) return;
    this.view.menu = null;
    this.emit();
  }

  select(r: number, c: number, extend = false): void {
    if (this.view.editing) this.commitEdit();
    const sheet = this.sheet();
    const pos = { r: clamp(r, 0, sheet.rows - 1), c: clamp(c, 0, sheet.cols - 1) };
    this.view.focus = pos;
    if (!extend) this.view.anchor = pos;
    if (this.view.painter && !extend) this.applyPainter(pos);
    this.broadcastCursor();
    this.emit();
  }

  move(dr: number, dc: number, extend = false): void {
    const sheet = this.sheet();
    if (this.view.focus.r + dr >= sheet.rows) sheet.rows = Math.min(5000, sheet.rows + 40);
    if (this.view.focus.c + dc >= sheet.cols) sheet.cols = Math.min(256, sheet.cols + 6);
    const r = clamp(this.view.focus.r + dr, 0, sheet.rows - 1);
    const c = clamp(this.view.focus.c + dc, 0, sheet.cols - 1);
    this.view.focus = { r, c };
    if (!extend) this.view.anchor = { r, c };
    this.broadcastCursor();
    this.emit();
  }

  selectArea(r1: number, c1: number, r2: number, c2: number): void {
    if (this.view.editing) this.commitEdit();
    const sheet = this.sheet();
    this.view.anchor = { r: clamp(r1, 0, sheet.rows - 1), c: clamp(c1, 0, sheet.cols - 1) };
    this.view.focus = { r: clamp(r2, 0, sheet.rows - 1), c: clamp(c2, 0, sheet.cols - 1) };
    this.broadcastCursor();
    this.emit();
  }

  selectAll(): void {
    const used = this.usedBounds();
    this.view.anchor = { r: used.r1, c: used.c1 };
    this.view.focus = { r: used.r2, c: used.c2 };
    this.emit();
  }

  goTo(addr: string): void {
    const range = parseRange(addr);
    if (!range) {
      this.view.status = 'Adresse nicht erkannt.';
      this.emit();
      return;
    }
    this.view.anchor = { r: range.r1, c: range.c1 };
    this.view.focus = { r: range.r2, c: range.c2 };
    this.view.status = addr.toUpperCase();
    this.emit();
  }

  beginEdit(seed?: string): void {
    const sheet = this.sheet();
    const { r, c } = this.view.focus;
    const prev = sheet.cells[cellKey(r, c)];
    if (sheet.protected && prev?.locked !== false) {
      this.view.status = 'Diese Zelle ist auf dem geschützten Blatt gesperrt.';
      this.emit();
      return;
    }
    this.view.editing = true;
    this.view.editAt = { r, c };
    this.view.pointing = null;
    this.view.editValue = seed !== undefined ? seed : (prev?.raw ?? '');
    this.emit();
  }

  setEditValue(value: string): void {
    this.view.editValue = value;
    this.view.pointing = null;
    this.emit();
  }

  cancelEdit(): void {
    this.view.editing = false;
    this.view.pointing = null;
    this.view.editAt = null;
    this.view.anchor = { ...this.view.focus };
    this.emit();
  }

  commitEdit(move?: { dr: number; dc: number; fill?: boolean }): void {
    if (!this.view.editing || !this.view.editAt) return;
    const { r, c } = this.view.editAt;
    const raw = this.view.editValue;
    const ok = this.setCell(r, c, raw, { emit: false });
    this.view.editing = false;
    this.view.pointing = null;
    this.view.editAt = null;
    if (!ok) {
      this.view.focus = { r, c };
      this.view.anchor = { r, c };
      this.emit();
      return;
    }
    this.noteLiteral(r, c, raw);
    if (move?.fill) {
      const b = this.bounds();
      const sheet = this.sheet();
      for (let rr = b.r1; rr <= b.r2; rr++) {
        for (let cc = b.c1; cc <= b.c2; cc++) {
          if (rr === r && cc === c) continue;
          const next = raw.startsWith('=') ? adjustFormulaCopy(raw, rr - r, cc - c) : raw;
          this.put(sheet, rr, cc, next);
        }
      }
      this.recalc(true);
    }
    const dr = move?.dr ?? 0;
    const dc = move?.dc ?? 0;
    if (dr || dc) {
      this.view.focus = {
        r: clamp(r + dr, 0, this.sheet().rows - 1),
        c: clamp(c + dc, 0, this.sheet().cols - 1),
      };
      this.view.anchor = { ...this.view.focus };
    } else {
      this.view.focus = { r, c };
      this.view.anchor = { r, c };
    }
    this.emit();
  }

  nudgePoint(dr: number, dc: number): void {
    const value = this.view.editValue;
    if (!value.startsWith('=')) {
      this.commitEdit({ dr, dc });
      return;
    }
    if (!this.view.pointing) {
      const match = /^(.*?)(\$?[A-Za-z]{1,3}\$?\d+)$/.exec(value);
      const tailOk = !!match && /[+\-*/:(;,]/.test(match[1].slice(-1));
      if (tailOk && match) {
        const pos = parseAddr(match[2].replace(/\$/g, ''));
        this.view.pointing = { r: pos?.r ?? this.view.focus.r, c: pos?.c ?? this.view.focus.c, base: match[1] };
      } else if (/[+\-*/:(;,]$/.test(value)) {
        this.view.pointing = { r: this.view.focus.r, c: this.view.focus.c, base: value };
      } else {
        this.commitEdit({ dr, dc });
        return;
      }
    }
    const point = this.view.pointing;
    if (!point) return;
    point.r = Math.max(0, point.r + dr);
    point.c = Math.max(0, point.c + dc);
    this.view.editValue = point.base + colName(point.c) + (point.r + 1);
    this.view.anchor = { r: point.r, c: point.c };
    this.view.focus = { r: point.r, c: point.c };
    this.emit();
  }

  cycleAbs(): void {
    if (!this.view.editing) return;
    const value = this.view.editValue;
    const match = /^(.*?)(\$?)([A-Za-z]{1,3})(\$?)(\d+)$/.exec(value);
    if (!match) return;
    const absCol = match[2] === '$';
    const absRow = match[4] === '$';
    let col = '$';
    let row = '$';
    if (absCol && absRow) {
      col = '';
      row = '$';
    } else if (!absCol && absRow) {
      col = '$';
      row = '';
    } else if (absCol && !absRow) {
      col = '';
      row = '';
    }
    this.view.editValue = match[1] + col + match[3] + row + match[5];
    this.emit();
  }

  setCell(r: number, c: number, raw: string, opt: PutOpt = {}): boolean {
    const undo = opt.undo !== false;
    const recalc = opt.recalc !== false;
    const record = opt.record !== false;
    const emit = opt.emit !== false;
    const validation = opt.validation !== false;
    const sheet = this.sheet();
    const key = cellKey(r, c);
    const prev = sheet.cells[key];
    if (sheet.protected && prev?.locked !== false) {
      this.view.status = 'Diese Zelle ist auf dem geschützten Blatt gesperrt.';
      if (emit) this.emit();
      return false;
    }
    if (validation && raw && !raw.startsWith('=')) {
      const message = prev?.validation ? invalid(prev.validation, raw) : null;
      if (message) {
        this.view.status = message;
        if (emit) this.emit();
        return false;
      }
    }
    if (undo) this.pushUndo();
    this.put(sheet, r, c, raw);
    this.growTable(sheet, r, c);
    if (record) this.record(`rg.set(${JSON.stringify(`${colName(c)}${r + 1}`)}, ${JSON.stringify(raw)});`);
    const rev = sheet.cells[key]?.rev ?? 1;
    if (!this.remote && this.view.collab) {
      this.channel?.postMessage({ kind: 'cell', sheet: sheet.name, r, c, raw, rev, peer: this.view.selfId });
    }
    if (recalc) this.recalc(this.wb.calc === 'auto');
    this.view.status = 'Bereit';
    if (emit) this.emit();
    return true;
  }

  undo(): void {
    const prev = this.history.pop();
    if (!prev) return;
    this.future.push(this.capture());
    this.restore(prev);
  }

  redo(): void {
    const next = this.future.pop();
    if (!next) return;
    this.history.push(this.capture());
    this.restore(next);
  }

  copy(cut = false): string {
    const b = this.bounds();
    const sheet = this.sheet();
    const cells: ClipCell[] = [];
    const lines: string[] = [];
    for (let r = b.r1; r <= b.r2; r++) {
      const cols: string[] = [];
      for (let c = b.c1; c <= b.c2; c++) {
        const cell = sheet.cells[cellKey(r, c)];
        cols.push(cell?.raw ?? '');
        if (cell) cells.push({ dr: r - b.r1, dc: c - b.c1, cell: cloneCell(cell) });
      }
      lines.push(cols.join('\t'));
    }
    this.clip = { cut, sheet: sheet.name, r: b.r1, c: b.c1, cells };
    this.lastTsv = lines.join('\n');
    if (cut) this.view.status = 'Ausschneiden';
    this.emit();
    return this.lastTsv;
  }

  paste(text?: string): void {
    const sheet = this.sheet();
    if (sheet.protected) {
      this.view.status = 'Blatt ist geschützt.';
      this.emit();
      return;
    }
    const external = text !== undefined && text !== this.lastTsv;
    if (!external && this.clip) {
      this.pushUndo();
      const { r, c } = this.view.focus;
      const source = this.clip;
      if (source.cut) {
        const src = this.wb.sheets.find((item) => item.name === source.sheet);
        if (src) for (const item of source.cells) delete src.cells[cellKey(source.r + item.dr, source.c + item.dc)];
      }
      for (const item of source.cells) {
        const raw = item.cell.raw.startsWith('=') ? adjustFormulaCopy(item.cell.raw, r - source.r, c - source.c) : item.cell.raw;
        this.put(sheet, r + item.dr, c + item.dc, raw);
        const dest = sheet.cells[cellKey(r + item.dr, c + item.dc)];
        if (!dest) continue;
        dest.style = item.cell.style ? { ...item.cell.style } : undefined;
        dest.comment = item.cell.comment;
        dest.validation = item.cell.validation
          ? { ...item.cell.validation, list: item.cell.validation.list ? [...item.cell.validation.list] : undefined }
          : undefined;
      }
      if (source.cut) this.clip = null;
      this.recalc(true);
      this.view.status = 'Eingefügt';
      this.emit();
      return;
    }
    if (!text) return;
    this.pushUndo();
    const rows = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
    const { r, c } = this.view.focus;
    rows.forEach((line, rr) => {
      line.split('\t').forEach((value, cc) => {
        if (value !== '' || rows.length > 1) this.put(sheet, r + rr, c + cc, value);
      });
    });
    this.recalc(true);
    this.view.status = 'Eingefügt';
    this.emit();
  }

  fillTo(tr: number, tc: number): void {
    const b = this.bounds();
    const r2 = Math.max(b.r2, tr);
    const c2 = Math.max(b.c2, tc);
    if (r2 === b.r2 && c2 === b.c2) return;
    const sheet = this.sheet();
    if (sheet.protected) {
      this.view.status = 'Blatt ist geschützt.';
      this.emit();
      return;
    }
    this.pushUndo();
    const height = b.r2 - b.r1 + 1;
    const width = b.c2 - b.c1 + 1;
    const steps = new Map<number, number>();
    if (r2 > b.r2) {
      for (let c = b.c1; c <= b.c2; c++) {
        const nums: number[] = [];
        let ok = true;
        for (let r = b.r1; r <= b.r2; r++) {
          const raw = sheet.cells[cellKey(r, c)]?.raw ?? '';
          if (!raw || raw.startsWith('=')) {
            ok = false;
            break;
          }
          const lit = parseLiteral(raw);
          if (typeof lit !== 'number') {
            ok = false;
            break;
          }
          nums.push(lit);
        }
        if (ok && nums.length >= 2) steps.set(c, nums[nums.length - 1] - nums[nums.length - 2]);
      }
    }
    for (let r = b.r1; r <= r2; r++) {
      for (let c = b.c1; c <= c2; c++) {
        if (r <= b.r2 && c <= b.c2) continue;
        const sr = b.r1 + ((r - b.r1) % height);
        const sc = b.c1 + ((c - b.c1) % width);
        const src = sheet.cells[cellKey(sr, sc)];
        if (r > b.r2 && c <= b.c2 && steps.has(c)) {
          const last = parseLiteral(sheet.cells[cellKey(b.r2, c)]?.raw ?? '');
          const n = (typeof last === 'number' ? last : 0) + (steps.get(c) ?? 0) * (r - b.r2);
          this.put(sheet, r, c, String(Math.round(n * 1e10) / 1e10));
        } else if (src) {
          const raw = src.raw.startsWith('=') ? adjustFormulaCopy(src.raw, r - sr, c - sc) : stepText(src.raw, r - sr);
          this.put(sheet, r, c, raw);
        }
        const dest = sheet.cells[cellKey(r, c)];
        if (dest && src?.style) dest.style = { ...src.style };
      }
    }
    this.recalc(true);
    this.view.status = 'Ausgefüllt';
    this.emit();
  }

  patchStyle(patch: Partial<Style>): void {
    const sheet = this.sheet();
    if (sheet.protected) {
      this.view.status = 'Blatt ist geschützt.';
      this.emit();
      return;
    }
    this.pushUndo();
    const b = this.bounds();
    for (let r = b.r1; r <= b.r2; r++) {
      for (let c = b.c1; c <= b.c2; c++) {
        const cell = this.ensure(sheet, r, c);
        cell.style = { ...cell.style, ...patch };
      }
    }
    this.record(`rg.style(${JSON.stringify(this.focusAddr())}, ${JSON.stringify(patch)});`);
    this.rebuildPaint();
    this.emit();
  }

  toggleStyle(key: 'bold' | 'italic' | 'underline' | 'strike'): void {
    const current = !!this.sheet().cells[cellKey(this.view.focus.r, this.view.focus.c)]?.style?.[key];
    this.patchStyle({ [key]: !current });
  }

  setNumFmt(fmt: NumFmt): void {
    this.patchStyle({ numFmt: fmt });
  }

  bumpDecimals(dir: 1 | -1): void {
    const current = this.sheet().cells[cellKey(this.view.focus.r, this.view.focus.c)]?.style?.numFmt;
    const base = current && /^[ncp]\d$/.test(current) ? current : 'n0';
    const digits = clamp(Number(base.slice(1)) + dir, 0, 4);
    this.patchStyle({ numFmt: `${base[0]}${digits}` as NumFmt });
  }

  toggleMerge(): void {
    this.pushUndo();
    const b = this.bounds();
    const sheet = this.sheet();
    const index = sheet.merges.findIndex((m) => m.r1 === b.r1 && m.c1 === b.c1 && m.r2 === b.r2 && m.c2 === b.c2);
    if (index >= 0) sheet.merges.splice(index, 1);
    else if (b.r1 !== b.r2 || b.c1 !== b.c2) sheet.merges.push({ ...b });
    this.emit();
  }

  clear(mode: 'all' | 'values' | 'formats' | 'comments'): void {
    const sheet = this.sheet();
    if (sheet.protected && mode !== 'comments') {
      this.view.status = 'Blatt ist geschützt.';
      this.emit();
      return;
    }
    this.pushUndo();
    const b = this.bounds();
    for (let r = b.r1; r <= b.r2; r++) {
      for (let c = b.c1; c <= b.c2; c++) {
        const key = cellKey(r, c);
        const cell = sheet.cells[key];
        if (!cell) continue;
        if (mode === 'all') delete sheet.cells[key];
        if (mode === 'values') cell.raw = '';
        if (mode === 'formats') cell.style = undefined;
        if (mode === 'comments' || mode === 'all') cell.comment = undefined;
      }
    }
    this.recalc(true);
    this.emit();
  }

  insertRows(): void {
    const b = this.bounds();
    this.shift('row', b.r1, b.r2 - b.r1 + 1);
  }

  deleteRows(): void {
    const b = this.bounds();
    this.shift('row', b.r1, -(b.r2 - b.r1 + 1));
  }

  insertCols(): void {
    const b = this.bounds();
    this.shift('col', b.c1, b.c2 - b.c1 + 1);
  }

  deleteCols(): void {
    const b = this.bounds();
    this.shift('col', b.c1, -(b.c2 - b.c1 + 1));
  }

  setRowHeight(px: number): void {
    this.pushUndo();
    const b = this.bounds();
    for (let r = b.r1; r <= b.r2; r++) this.sheet().rowHeights[r] = px;
    this.emit();
  }

  setColWidth(px: number): void {
    this.pushUndo();
    const b = this.bounds();
    for (let c = b.c1; c <= b.c2; c++) this.sheet().colWidths[c] = px;
    this.emit();
  }

  resizeCol(col: number, px: number): void {
    this.sheet().colWidths[col] = Math.max(24, Math.round(px));
    this.emit();
  }

  autoFit(): void {
    this.pushUndo();
    const b = this.bounds();
    const sheet = this.sheet();
    for (let c = b.c1; c <= b.c2; c++) {
      let width = 56;
      for (let r = 0; r < Math.min(sheet.rows, 300); r++) width = Math.max(width, Math.min(340, this.display(r, c).length * 8 + 18));
      sheet.colWidths[c] = width;
    }
    this.emit();
  }

  freeze(): void {
    this.pushUndo();
    const sheet = this.sheet();
    sheet.freezeRows = this.view.focus.r;
    sheet.freezeCols = this.view.focus.c;
    this.view.status = 'Fenster fixiert';
    this.emit();
  }

  unfreeze(): void {
    this.pushUndo();
    this.sheet().freezeRows = 0;
    this.sheet().freezeCols = 0;
    this.emit();
  }

  toggleGrid(): void {
    this.sheet().showGrid = !this.sheet().showGrid;
    this.emit();
  }

  toggleLock(): void {
    this.pushUndo();
    const b = this.bounds();
    const sheet = this.sheet();
    const unlock = sheet.cells[cellKey(this.view.focus.r, this.view.focus.c)]?.locked !== false;
    for (let r = b.r1; r <= b.r2; r++) {
      for (let c = b.c1; c <= b.c2; c++) this.ensure(sheet, r, c).locked = !unlock;
    }
    this.view.status = unlock ? 'Zellen entsperrt' : 'Zellen gesperrt';
    this.emit();
  }

  async protect(password: string): Promise<void> {
    this.pushUndo();
    const sheet = this.sheet();
    sheet.protected = true;
    if (password) sheet.passwordHash = await sha256(password);
    else delete sheet.passwordHash;
    this.view.status = 'Blatt geschützt';
    this.closeDialog();
  }

  async unprotect(password: string): Promise<void> {
    const sheet = this.sheet();
    if (sheet.passwordHash && (await sha256(password)) !== sheet.passwordHash) {
      this.view.status = 'Passwort stimmt nicht.';
      this.emit();
      return;
    }
    this.pushUndo();
    sheet.protected = false;
    delete sheet.passwordHash;
    this.view.status = 'Blattschutz aufgehoben';
    this.closeDialog();
  }

  toggleStructure(): void {
    this.pushUndo();
    this.wb.structureLocked = !this.wb.structureLocked;
    this.view.status = this.wb.structureLocked ? 'Struktur geschützt' : 'Struktur entsperrt';
    this.emit();
  }

  sortBy(col: number, asc: boolean, header = true): void {
    const sheet = this.sheet();
    const range = sheet.filter ?? this.bounds();
    const r1 = header ? range.r1 + 1 : range.r1;
    this.pushUndo();
    this.sortBlock(sheet, r1, range.c1, range.r2, range.c2, [{ col, asc }]);
    this.recalc(true);
    this.view.status = asc ? 'Aufsteigend sortiert' : 'Absteigend sortiert';
    this.emit();
  }

  sortKeys(keys: { col: number; asc: boolean }[], header: boolean): void {
    const sheet = this.sheet();
    const range = sheet.filter ?? this.bounds();
    const r1 = header ? range.r1 + 1 : range.r1;
    this.pushUndo();
    this.sortBlock(sheet, r1, range.c1, range.r2, range.c2, keys);
    this.recalc(true);
    this.emit();
  }

  toggleFilter(): void {
    this.pushUndo();
    const sheet = this.sheet();
    if (sheet.filter) sheet.filter = null;
    else {
      const b = this.bounds();
      const used = this.usedBounds();
      const wide = b.r2 > b.r1 || b.c2 > b.c1;
      sheet.filter = {
        r1: wide ? b.r1 : used.r1,
        c1: wide ? b.c1 : used.c1,
        r2: wide ? b.r2 : used.r2,
        c2: wide ? b.c2 : used.c2,
        selected: {},
      };
    }
    this.recalc(true);
    this.emit();
  }

  setFilter(col: number, values: string[] | null): void {
    const sheet = this.sheet();
    if (!sheet.filter) this.toggleFilter();
    const filter = this.sheet().filter;
    if (!filter) return;
    this.pushUndo();
    if (values === null) delete filter.selected[col];
    else filter.selected[col] = values;
    this.recalc(true);
    this.emit();
  }

  uniqueValues(col: number): string[] {
    const sheet = this.sheet();
    const filter = sheet.filter;
    const r1 = (filter?.r1 ?? 0) + 1;
    const r2 = filter?.r2 ?? this.usedBounds().r2;
    const values = new Set<string>();
    for (let r = r1; r <= r2; r++) {
      const text = this.filterText(sheet, r, col);
      if (text) values.add(text);
    }
    return [...values].sort((a, b) => a.localeCompare(b, 'de'));
  }

  createTable(): void {
    const b = this.bounds();
    if (b.r2 <= b.r1) {
      this.view.status = 'Markiere Kopfzeile und mindestens eine Datenzeile.';
      this.emit();
      return;
    }
    this.pushUndo();
    const sheet = this.sheet();
    let n = sheet.tables.length + 1;
    let name = `Tabelle${n}`;
    while (this.wb.sheets.some((sh) => sh.tables.some((table) => table.name.toLowerCase() === name.toLowerCase()))) {
      n += 1;
      name = `Tabelle${n}`;
    }
    sheet.tables.push({ name, sheet: sheet.name, r1: b.r1, c1: b.c1, r2: b.r2, c2: b.c2, banded: true });
    sheet.filter = { r1: b.r1, c1: b.c1, r2: b.r2, c2: b.c2, selected: {} };
    for (let c = b.c1; c <= b.c2; c++) {
      const cell = this.ensure(sheet, b.r1, c);
      cell.style = { ...(cell.style ?? {}), bold: true, color: '#ffffff', fill: '#0d4f9a' };
    }
    this.recalc(true);
    this.view.status = `Tabelle ${name}`;
    this.emit();
  }

  toggleTotals(): void {
    const sheet = this.sheet();
    const table =
      sheet.tables.find((item) => this.view.focus.r >= item.r1 && this.view.focus.r <= item.r2 + 1 && this.view.focus.c >= item.c1 && this.view.focus.c <= item.c2) ??
      sheet.tables[0];
    if (!table) {
      this.view.status = 'Keine Tabelle im Blatt.';
      this.emit();
      return;
    }
    this.pushUndo();
    if (table.totalsRow) {
      table.totalsRow = false;
      table.r2 -= 1;
    } else {
      table.r2 += 1;
      table.totalsRow = true;
      for (let c = table.c1; c <= table.c2; c++) {
        const header = sheet.cells[cellKey(table.r1, c)]?.raw ?? `Spalte${c + 1}`;
        const sample = this.numAt(table.r1 + 1, c);
        if (c === table.c1 && sample === null) this.put(sheet, table.r2, c, 'Ergebnis');
        else this.put(sheet, table.r2, c, `=TEILERGEBNIS(9;${table.name}[${header}])`);
      }
    }
    if (sheet.filter && sheet.filter.r1 === table.r1) sheet.filter.r2 = table.r2;
    this.recalc(true);
    this.emit();
  }

  addChart(type: ChartType): void {
    this.pushUndo();
    const b = this.bounds();
    this.sheet().charts.push({
      id: uid(),
      type,
      r1: b.r1,
      c1: b.c1,
      r2: Math.max(b.r1, b.r2),
      c2: Math.max(b.c1, b.c2),
      title: 'Diagramm',
      x: 460,
      y: 48,
      w: 480,
      h: 280,
      hasHeader: b.r2 > b.r1,
    });
    this.view.status = 'Diagramm eingefügt';
    this.emit();
  }

  moveChart(id: string, x: number, y: number): void {
    const chart = this.sheet().charts.find((item) => item.id === id);
    if (!chart) return;
    chart.x = Math.max(0, x);
    chart.y = Math.max(0, y);
    this.emit();
  }

  removeChart(id: string): void {
    this.pushUndo();
    this.sheet().charts = this.sheet().charts.filter((item) => item.id !== id);
    this.emit();
  }

  addSlicer(): void {
    this.pushUndo();
    const sheet = this.sheet();
    if (!sheet.filter) {
      const used = this.usedBounds();
      sheet.filter = { r1: used.r1, c1: used.c1, r2: used.r2, c2: used.c2, selected: {} };
    }
    const col = this.view.focus.c;
    const title = sheet.cells[cellKey(sheet.filter.r1, col)]?.raw || colName(col);
    sheet.slicers.push({ id: uid(), col, title, x: 24 + sheet.slicers.length * 170, y: 320 });
    this.recalc(true);
    this.emit();
  }

  addRule(partial: Omit<CondRule, 'id' | 'r1' | 'c1' | 'r2' | 'c2'>): void {
    this.pushUndo();
    const b = this.bounds();
    this.sheet().rules.push({ id: uid(), ...b, ...partial });
    this.rebuildPaint();
    this.emit();
  }

  clearRules(): void {
    this.pushUndo();
    this.sheet().rules = [];
    this.rebuildPaint();
    this.emit();
  }

  setComment(text: string): void {
    this.pushUndo();
    const { r, c } = this.view.focus;
    const cell = this.ensure(this.sheet(), r, c);
    cell.comment = text.trim() || undefined;
    this.closeDialog();
  }

  setValidation(validation: Validation | null): void {
    this.pushUndo();
    const b = this.bounds();
    const sheet = this.sheet();
    for (let r = b.r1; r <= b.r2; r++) {
      for (let c = b.c1; c <= b.c2; c++) {
        const cell = this.ensure(sheet, r, c);
        cell.validation = validation
          ? { ...validation, list: validation.list ? [...validation.list] : undefined }
          : undefined;
      }
    }
    this.view.status = validation ? 'Gültigkeit festgelegt' : 'Gültigkeit entfernt';
    this.closeDialog();
  }

  addName(name: string, refers: string): void {
    const clean = name.trim();
    if (!/^[A-Za-zÄÖÜäöü_][\w.]*$/.test(clean)) {
      this.view.status = 'Name muss mit einem Buchstaben beginnen.';
      this.emit();
      return;
    }
    this.pushUndo();
    const range = refers.startsWith('=') ? null : parseRange(refers);
    const entry = range
      ? { name: clean, sheet: this.sheet().name, ...range }
      : { name: clean, formula: refers.startsWith('=') ? refers : `=${refers}` };
    const index = this.wb.names.findIndex((item) => item.name.toLowerCase() === clean.toLowerCase());
    if (index >= 0) this.wb.names[index] = entry;
    else this.wb.names.push(entry);
    this.recalc(true);
    this.view.status = `Name ${clean}`;
    this.emit();
  }

  removeName(name: string): void {
    this.pushUndo();
    this.wb.names = this.wb.names.filter((item) => item.name !== name);
    this.recalc(true);
    this.emit();
  }

  autosum(): void {
    const b = this.bounds();
    const sheet = this.sheet();
    this.pushUndo();
    if (b.r1 === b.r2 && b.c1 === b.c2) {
      let r = b.r1 - 1;
      while (r >= 0 && this.numAt(r, b.c1) !== null) r--;
      if (r + 1 <= b.r1 - 1) this.put(sheet, b.r1, b.c1, `=SUMME(${colName(b.c1)}${r + 2}:${colName(b.c1)}${b.r1})`);
    } else {
      for (let c = b.c1; c <= b.c2; c++) this.put(sheet, b.r2 + 1, c, `=SUMME(${colName(c)}${b.r1 + 1}:${colName(c)}${b.r2 + 1})`);
    }
    this.recalc(true);
    this.emit();
  }

  textToColumns(delim: string): void {
    this.pushUndo();
    const b = this.bounds();
    const sheet = this.sheet();
    const splitter = delim === '\\t' ? '\t' : delim || ';';
    for (let r = b.r1; r <= b.r2; r++) {
      const raw = sheet.cells[cellKey(r, b.c1)]?.raw ?? '';
      if (!raw || raw.startsWith('=')) continue;
      raw.split(splitter).forEach((part, i) => this.put(sheet, r, b.c1 + i, part.trim()));
    }
    this.recalc(true);
    this.view.status = 'Text in Spalten';
    this.closeDialog();
  }

  removeDuplicates(): void {
    this.pushUndo();
    const b = this.bounds();
    const sheet = this.sheet();
    const seen = new Set<string>();
    const kept: { cells: { c: number; cell: Cell }[] }[] = [];
    for (let r = b.r1; r <= b.r2; r++) {
      const cells: { c: number; cell: Cell }[] = [];
      const keyParts: string[] = [];
      for (let c = b.c1; c <= b.c2; c++) {
        const cell = sheet.cells[cellKey(r, c)];
        keyParts.push(cell?.raw ?? '');
        if (cell) cells.push({ c, cell: cloneCell(cell) });
      }
      const key = keyParts.join('\0');
      if (seen.has(key)) continue;
      seen.add(key);
      kept.push({ cells });
    }
    for (let r = b.r1; r <= b.r2; r++) for (let c = b.c1; c <= b.c2; c++) delete sheet.cells[cellKey(r, c)];
    kept.forEach((row, i) => {
      for (const entry of row.cells) sheet.cells[cellKey(b.r1 + i, entry.c)] = entry.cell;
    });
    this.recalc(true);
    this.view.status = `${b.r2 - b.r1 + 1 - kept.length} Duplikate entfernt`;
    this.emit();
  }

  flashFill(): void {
    const b = this.bounds();
    if (b.c1 === 0) {
      this.view.status = 'Blitzvorschau braucht eine Beispielspalte links daneben.';
      this.emit();
      return;
    }
    const sheet = this.sheet();
    const col = b.c1;
    let sampleR = -1;
    for (let r = b.r1; r <= b.r2; r++) {
      if (sheet.cells[cellKey(r, col)]?.raw) {
        sampleR = r;
        break;
      }
    }
    if (sampleR < 0) {
      this.view.status = 'Schreibe zuerst ein Beispiel in die Zielspalte.';
      this.emit();
      return;
    }
    const sampleSrc = sheet.cells[cellKey(sampleR, col - 1)]?.raw ?? '';
    const sample = sheet.cells[cellKey(sampleR, col)]?.raw ?? '';
    const transform = detectFill(sampleSrc, sample);
    if (!transform) {
      this.view.status = 'Kein Muster erkannt.';
      this.emit();
      return;
    }
    this.pushUndo();
    let n = 0;
    for (let r = b.r1; r <= b.r2; r++) {
      if (r === sampleR) continue;
      const src = sheet.cells[cellKey(r, col - 1)]?.raw ?? '';
      if (!src) continue;
      this.put(sheet, r, col, transform(src));
      n++;
    }
    this.recalc(true);
    this.view.status = `Blitzvorschau: ${n} Zellen`;
    this.emit();
  }

  groupRows(): void {
    const b = this.bounds();
    if (b.r2 <= b.r1) return;
    this.pushUndo();
    this.sheet().groups.push({ start: b.r1, end: b.r2, collapsed: false });
    this.emit();
  }

  toggleGroup(index: number): void {
    const group = this.sheet().groups[index];
    if (!group) return;
    group.collapsed = !group.collapsed;
    this.recalc(true);
    this.emit();
  }

  goalSeek(inR: number, inC: number, outR: number, outC: number, target: number): string {
    this.pushUndo();
    const sheet = this.sheet();
    let x = this.numAt(inR, inC) ?? 1;
    let message = 'Zielwertsuche ohne Konvergenz.';
    for (let i = 0; i < 40; i++) {
      this.put(sheet, inR, inC, numRaw(x));
      this.recalc(true);
      const y = this.numAt(outR, outC);
      if (y === null) {
        message = 'Die Zielzelle liefert keine Zahl.';
        break;
      }
      if (Math.abs(y - target) <= Math.max(1e-6, Math.abs(target) * 1e-5)) {
        message = `Ziel erreicht bei ${numRaw(x)} → ${formatNumber(y, 4, false)}`;
        break;
      }
      const dx = Math.max(1e-5, Math.abs(x) * 1e-4);
      this.put(sheet, inR, inC, numRaw(x + dx));
      this.recalc(true);
      const y2 = this.numAt(outR, outC);
      if (y2 === null) break;
      const slope = (y2 - y) / dx;
      if (!Number.isFinite(slope) || Math.abs(slope) < 1e-12) break;
      x -= (y - target) / slope;
      if (!Number.isFinite(x)) break;
      x = Math.max(-1e9, Math.min(1e9, x));
    }
    this.put(sheet, inR, inC, numRaw(x));
    this.recalc(true);
    this.view.status = message;
    this.emit();
    return message;
  }

  saveScenario(name: string): void {
    const b = this.bounds();
    const sheet = this.sheet();
    const cells: { sheet: string; r: number; c: number; raw: string }[] = [];
    for (let r = b.r1; r <= b.r2; r++) {
      for (let c = b.c1; c <= b.c2; c++) cells.push({ sheet: sheet.name, r, c, raw: sheet.cells[cellKey(r, c)]?.raw ?? '' });
    }
    this.wb.scenarios = this.wb.scenarios.filter((item) => item.name !== name);
    this.wb.scenarios.push({ name, cells });
    this.view.status = `Szenario ${name}`;
    this.emit();
  }

  applyScenario(name: string): void {
    const scenario = this.wb.scenarios.find((item) => item.name === name);
    if (!scenario) return;
    this.pushUndo();
    for (const item of scenario.cells) {
      const sheet = this.wb.sheets.find((sh) => sh.name === item.sheet) ?? this.sheet();
      this.put(sheet, item.r, item.c, item.raw);
    }
    this.recalc(true);
    this.emit();
  }

  solve(dir: 'max' | 'min'): string {
    const b = this.bounds();
    const sheet = this.sheet();
    const vars: CellPos[] = [];
    for (let r = b.r1; r <= b.r2; r++) {
      for (let c = b.c1; c <= b.c2; c++) {
        const raw = sheet.cells[cellKey(r, c)]?.raw ?? '';
        if (raw && !raw.startsWith('=') && this.numAt(r, c) !== null) vars.push({ r, c });
      }
    }
    if (!vars.length) return 'Markiere veränderbare Zahlzellen.';
    const outR = Math.min(sheet.rows - 1, b.r2 + 1);
    const outC = b.c1;
    if (this.numAt(outR, outC) === null) return 'Unter der Markierung braucht es eine Formelzelle als Ziel.';
    this.pushUndo();
    const xs = vars.map((pos) => this.numAt(pos.r, pos.c) ?? 0);
    let best = this.numAt(outR, outC) ?? 0;
    let step = 1;
    for (let iter = 0; iter < 24; iter++) {
      let improved = false;
      for (let i = 0; i < vars.length; i++) {
        for (const sign of [1, -1]) {
          const trial = xs[i] + sign * step;
          this.put(sheet, vars[i].r, vars[i].c, numRaw(trial));
          this.recalc(true);
          const score = this.numAt(outR, outC);
          if (score !== null && (dir === 'max' ? score > best + 1e-9 : score < best - 1e-9)) {
            best = score;
            xs[i] = trial;
            improved = true;
          } else this.put(sheet, vars[i].r, vars[i].c, numRaw(xs[i]));
        }
      }
      if (!improved) step /= 2;
      if (step < 1e-3) break;
    }
    vars.forEach((pos, i) => this.put(sheet, pos.r, pos.c, numRaw(xs[i])));
    this.recalc(true);
    const message = `Solver (${dir === 'max' ? 'Maximum' : 'Minimum'}): ${formatNumber(best, 4, false)}`;
    this.view.status = message;
    this.emit();
    return message;
  }

  insights(): string[] {
    const sheet = this.sheet();
    const used = this.usedBounds();
    const lines: string[] = [];
    for (let c = used.c1; c <= used.c2; c++) {
      const nums: number[] = [];
      for (let r = used.r1; r <= used.r2; r++) {
        const n = this.numAt(r, c, sheet);
        if (n !== null) nums.push(n);
      }
      if (nums.length < 3) continue;
      const header = sheet.cells[cellKey(used.r1, c)]?.raw || colName(c);
      const sum = nums.reduce((a, b) => a + b, 0);
      const avg = sum / nums.length;
      const min = Math.min(...nums);
      const max = Math.max(...nums);
      const variance = nums.reduce((a, b) => a + (b - avg) ** 2, 0) / (nums.length - 1);
      const sd = Math.sqrt(variance);
      const trend = nums[nums.length - 1] - nums[0];
      lines.push(
        `${header}: n=${nums.length}, Summe ${formatNumber(sum, 2)}, Mittel ${formatNumber(avg, 2)}, Min ${formatNumber(min, 2)}, Max ${formatNumber(max, 2)}, Stabw ${formatNumber(sd, 2)}.`,
      );
      if (Math.abs(trend) > sd) lines.push(`${header}: Der letzte Wert liegt ${trend > 0 ? 'über' : 'unter'} dem ersten, Abstand ${formatNumber(trend, 2)}.`);
      nums.forEach((n, i) => {
        if (sd > 0 && Math.abs(n - avg) > 2 * sd) lines.push(`${header}, Wert ${i + 1}: Ausreißer ${formatNumber(n, 2)} (mehr als 2 Stabw vom Mittel).`);
      });
    }
    if (!lines.length) lines.push('Zu wenige numerische Spalten für eine automatische Einordnung.');
    return lines;
  }

  dlp(): { sheet: string; addr: string; kind: string; sample: string }[] {
    const found: { sheet: string; addr: string; kind: string; sample: string }[] = [];
    for (const sheet of this.wb.sheets) {
      for (const [key, cell] of Object.entries(sheet.cells)) {
        const raw = cell.raw;
        if (!raw || raw.startsWith('=')) continue;
        const [r, c] = key.split(',').map(Number);
        const addr = `${colName(c)}${r + 1}`;
        const email = /[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/.exec(raw);
        if (email) found.push({ sheet: sheet.name, addr, kind: 'E-Mail', sample: email[0] });
        const iban = /\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b/.exec(raw.replace(/\s/g, ''));
        if (iban) found.push({ sheet: sheet.name, addr, kind: 'IBAN', sample: iban[0] });
        const digits = raw.replace(/[ -]/g, '');
        if (/^\d{13,19}$/.test(digits) && luhn(digits)) found.push({ sheet: sheet.name, addr, kind: 'Kartennummer', sample: `${digits.slice(0, 4)}…${digits.slice(-4)}` });
      }
    }
    return found;
  }

  a11y(): string[] {
    const notes: string[] = [];
    const sheet = this.sheet();
    if (sheet.merges.length) notes.push(`${sheet.merges.length} verbundene Zellen erschweren die Navigation mit Screenreadern.`);
    for (const table of sheet.tables) {
      for (let c = table.c1; c <= table.c2; c++) {
        if (!sheet.cells[cellKey(table.r1, c)]?.raw) notes.push(`Tabelle ${table.name}: leere Überschrift in Spalte ${colName(c)}.`);
      }
    }
    for (const [key, cell] of Object.entries(sheet.cells)) {
      const [r, c] = key.split(',').map(Number);
      if (!cell.style?.color && !cell.style?.fill) continue;
      const fg = cell.style.color ?? (this.view.theme === 'dark' ? '#e6e6e6' : '#1b1b1b');
      const bg = cell.style.fill ?? (this.view.theme === 'dark' ? '#1e1e1e' : '#ffffff');
      const ratio = contrast(fg, bg);
      if (ratio < 4.5) notes.push(`${colName(c)}${r + 1}: Kontrast ${ratio.toFixed(2)} : 1, unter 4,5 : 1.`);
    }
    if (!notes.length) notes.push('Keine offensichtlichen Hürden im aktiven Blatt.');
    return notes;
  }

  saveVersion(label: string): void {
    const { versions, ...rest } = this.wb;
    void versions;
    this.wb.versions.unshift({ id: uid(), at: Date.now(), label: label || 'Stand', json: JSON.stringify(rest) });
    this.wb.versions = this.wb.versions.slice(0, 12);
    this.view.status = 'Version gespeichert';
    this.emit();
  }

  restoreVersion(id: string): void {
    const snap = this.wb.versions.find((item) => item.id === id);
    if (!snap) return;
    const keep = this.wb.versions;
    this.pushUndo();
    const next = normalizeWorkbook(JSON.parse(snap.json) as Workbook);
    next.versions = keep;
    this.wb = next;
    this.recalc(true);
    this.view.status = `Wiederhergestellt: ${snap.label}`;
    this.emit();
  }

  saveView(name: string): void {
    const sheet = this.sheet();
    this.wb.views = this.wb.views.filter((item) => !(item.name === name && item.sheet === sheet.name));
    this.wb.views.push({
      name,
      sheet: sheet.name,
      filter: sheet.filter ? (JSON.parse(JSON.stringify(sheet.filter)) as Sheet['filter']) : null,
      groups: JSON.parse(JSON.stringify(sheet.groups)) as Sheet['groups'],
    });
    this.view.status = `Blattansicht ${name}`;
    this.emit();
  }

  applyView(name: string): void {
    const sheet = this.sheet();
    const view = this.wb.views.find((item) => item.name === name && item.sheet === sheet.name);
    if (!view) return;
    this.pushUndo();
    sheet.filter = view.filter ? (JSON.parse(JSON.stringify(view.filter)) as Sheet['filter']) : null;
    sheet.groups = JSON.parse(JSON.stringify(view.groups)) as Sheet['groups'];
    this.recalc(true);
    this.emit();
  }

  findNext(query: string, formulas: boolean): boolean {
    if (!query) return false;
    const sheet = this.sheet();
    const start = this.view.focus.r * sheet.cols + this.view.focus.c + 1;
    const total = sheet.rows * sheet.cols;
    const needle = query.toLocaleLowerCase('de-DE');
    for (let i = 0; i < total; i++) {
      const idx = (start + i) % total;
      const r = Math.floor(idx / sheet.cols);
      const c = idx % sheet.cols;
      const cell = sheet.cells[cellKey(r, c)];
      const hay = (formulas ? cell?.raw : this.display(r, c)) ?? '';
      if (hay.toLocaleLowerCase('de-DE').includes(needle)) {
        this.view.focus = { r, c };
        this.view.anchor = { r, c };
        this.view.status = `Gefunden: ${colName(c)}${r + 1}`;
        this.emit();
        return true;
      }
    }
    this.view.status = 'Nichts gefunden';
    this.emit();
    return false;
  }

  replaceAll(query: string, repl: string): number {
    if (!query) return 0;
    this.pushUndo();
    let n = 0;
    const sheet = this.sheet();
    for (const cell of Object.values(sheet.cells)) {
      if (!cell.raw.includes(query)) continue;
      cell.raw = cell.raw.split(query).join(repl);
      n++;
    }
    this.recalc(true);
    this.view.status = `${n} Ersetzungen`;
    this.emit();
    return n;
  }

  tracePrecedents(): void {
    const { r, c } = this.view.focus;
    const raw = this.sheet().cells[cellKey(r, c)]?.raw ?? '';
    this.view.trace = [];
    if (raw.startsWith('=')) {
      const expr = tryParseFormula(raw.slice(1));
      walk(expr, (node) => {
        if (node.type === 'ref' && !node.sheet) this.view.trace.push({ r: node.row, c: node.col });
      });
    }
    this.view.status = `${this.view.trace.length} Vorgänger`;
    this.emit();
  }

  traceDependents(): void {
    const { r, c } = this.view.focus;
    const sheet = this.sheet();
    this.view.trace = [];
    for (const [key, cell] of Object.entries(sheet.cells)) {
      if (!cell.raw.startsWith('=')) continue;
      const [rr, cc] = key.split(',').map(Number);
      const expr = tryParseFormula(cell.raw.slice(1));
      let hit = false;
      walk(expr, (node) => {
        if (node.type === 'ref' && !node.sheet && node.row === r && node.col === c) hit = true;
        if (node.type === 'range' && node.a.type === 'ref' && node.b.type === 'ref') {
          const r1 = Math.min(node.a.row, node.b.row);
          const r2 = Math.max(node.a.row, node.b.row);
          const c1 = Math.min(node.a.col, node.b.col);
          const c2 = Math.max(node.a.col, node.b.col);
          if (r >= r1 && r <= r2 && c >= c1 && c <= c2) hit = true;
        }
      });
      if (hit) this.view.trace.push({ r: rr, c: cc });
    }
    this.view.status = `${this.view.trace.length} Nachfolger`;
    this.emit();
  }

  clearTrace(): void {
    this.view.trace = [];
    this.emit();
  }

  evaluateText(): string {
    const { r, c } = this.view.focus;
    const raw = this.sheet().cells[cellKey(r, c)]?.raw ?? '';
    const shown = this.display(r, c);
    const refs: string[] = [];
    if (raw.startsWith('=')) {
      walk(tryParseFormula(raw.slice(1)), (node) => {
        if (node.type === 'ref' && !node.sheet) refs.push(`${colName(node.col)}${node.row + 1}=${this.display(node.row, node.col) || 'leer'}`);
      });
    }
    return [`Zelle ${colName(c)}${r + 1}`, raw || '(leer)', `Ergebnis: ${shown || 'leer'}`, refs.length ? `Vorgänger: ${refs.join(', ')}` : 'Keine direkten Bezüge.'].join('\n');
  }

  pivot(rowCol: number, valueCol: number, agg: 'sum' | 'count' | 'avg'): void {
    const sheet = this.sheet();
    const range = sheet.filter ?? this.usedBounds();
    const groups = new Map<string, number[]>();
    for (let r = range.r1 + 1; r <= range.r2; r++) {
      const key = this.filterText(sheet, r, rowCol) || '(leer)';
      const n = agg === 'count' ? 1 : (this.numAt(r, valueCol) ?? 0);
      const list = groups.get(key) ?? [];
      list.push(n);
      groups.set(key, list);
    }
    this.pushUndo();
    const pivot = emptySheet('Pivot');
    const existing = this.wb.sheets.find((item) => item.name === 'Pivot');
    const target = existing ?? pivot;
    if (!existing) this.wb.sheets.push(pivot);
    const header = sheet.cells[cellKey(range.r1, rowCol)]?.raw || 'Gruppe';
    const valueHeader = sheet.cells[cellKey(range.r1, valueCol)]?.raw || 'Wert';
    this.put(target, 0, 0, header, { bold: true, color: '#ffffff', fill: '#0d4f9a' });
    this.put(target, 0, 1, valueHeader, { bold: true, color: '#ffffff', fill: '#0d4f9a' });
    let row = 1;
    for (const [key, list] of groups) {
      const sum = list.reduce((a, b) => a + b, 0);
      const value = agg === 'avg' ? sum / list.length : sum;
      this.put(target, row, 0, key);
      this.put(target, row, 1, String(Math.round(value * 100) / 100), { numFmt: 'n2' });
      row++;
    }
    this.wb.active = this.wb.sheets.indexOf(target);
    this.view.focus = { r: 0, c: 0 };
    this.view.anchor = { r: 0, c: 0 };
    this.recalc(true);
    this.view.status = 'Pivot erstellt';
    this.emit();
  }

  insertFormula(formula: string): void {
    const { r, c } = this.view.focus;
    this.setCell(r, c, formula.startsWith('=') ? formula : `=${formula}`);
    this.closeDialog();
  }

  insertLink(url: string, label: string): void {
    const safeUrl = url.replace(/"/g, '""');
    const safeLabel = (label || url).replace(/"/g, '""');
    this.setCell(this.view.focus.r, this.view.focus.c, `=HYPERLINK("${safeUrl}";"${safeLabel}")`);
    this.closeDialog();
  }

  insertImage(url: string): void {
    this.setCell(this.view.focus.r, this.view.focus.c, url.trim());
    this.closeDialog();
  }

  appendForm(values: string[]): void {
    this.pushUndo();
    const sheet = this.sheet();
    const table = sheet.tables[0];
    const row = table ? (table.totalsRow ? table.r2 : table.r2 + 1) : this.usedBounds().r2 + 1;
    const c0 = table?.c1 ?? 0;
    values.forEach((value, i) => this.put(sheet, row, c0 + i, value));
    if (table && !table.totalsRow) {
      table.r2 = row;
      if (sheet.filter && sheet.filter.r1 === table.r1) sheet.filter.r2 = row;
    }
    this.recalc(true);
    this.view.status = 'Datensatz angefügt';
    this.closeDialog();
  }

  async importUrl(url: string): Promise<void> {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const text = await response.text();
    const trimmed = text.trim();
    const table = trimmed.startsWith('[') || trimmed.startsWith('{') ? jsonTable(text) : /<table/i.test(text) ? htmlTable(text) : parseCsv(text);
    this.pushUndo();
    const sheet = this.sheet();
    const origin = this.view.focus;
    table.forEach((row, r) => row.forEach((value, c) => value !== '' && this.put(sheet, origin.r + r, origin.c + c, value)));
    this.recalc(true);
    this.view.status = `${table.length} Zeilen von ${url}`;
    this.closeDialog();
  }

  async webhook(url: string): Promise<void> {
    const b = this.bounds();
    const rows: string[][] = [];
    for (let r = b.r1; r <= b.r2; r++) {
      const line: string[] = [];
      for (let c = b.c1; c <= b.c2; c++) line.push(this.display(r, c));
      rows.push(line);
    }
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ app: 'ReckonGrid', workbook: this.wb.title, rows }),
    });
    this.view.status = `Webhook ${response.status}`;
    this.emit();
  }

  queryAt(sql: string): void {
    const text = sql.trim().replace(/"/g, '""');
    this.setCell(this.view.focus.r, this.view.focus.c, `=ABFRAGE("${text}")`);
    this.closeDialog();
  }

  regionSeries(): { name: string; value: number }[] {
    const sheet = this.sheet();
    const used = this.usedBounds();
    const map = new Map<string, number>();
    for (let r = used.r1; r <= used.r2; r++) {
      for (let c = used.c1; c <= used.c2; c++) {
        const label = sheet.cells[cellKey(r, c)]?.raw ?? '';
        if (!/^(Nord|Süd|Ost|West|Deutschland|Österreich|Schweiz)$/i.test(label)) continue;
        const n = this.numAt(r, c + 1) ?? this.numAt(r, c + 3);
        if (n === null) continue;
        map.set(label, (map.get(label) ?? 0) + n);
      }
    }
    return [...map.entries()].map(([name, value]) => ({ name, value }));
  }

  speak(): void {
    if (typeof speechSynthesis === 'undefined') {
      this.view.status = 'Sprachausgabe ist in diesem Browser nicht verfügbar.';
      this.emit();
      return;
    }
    const b = this.bounds();
    const parts: string[] = [];
    for (let r = b.r1; r <= b.r2; r++) for (let c = b.c1; c <= b.c2; c++) {
      const text = this.display(r, c);
      if (text) parts.push(text);
    }
    const utter = new SpeechSynthesisUtterance(parts.join(', ') || 'Leere Auswahl');
    utter.lang = 'de-DE';
    speechSynthesis.cancel();
    speechSynthesis.speak(utter);
  }

  addSheet(): void {
    if (this.wb.structureLocked) return this.lockedStructure();
    this.pushUndo();
    let n = this.wb.sheets.length + 1;
    let name = `Tabelle${n}`;
    while (this.wb.sheets.some((sheet) => sheet.name.toLowerCase() === name.toLowerCase())) {
      n += 1;
      name = `Tabelle${n}`;
    }
    this.wb.sheets.push(emptySheet(name));
    this.activate(this.wb.sheets.length - 1);
  }

  deleteSheet(index = this.wb.active): void {
    if (this.wb.structureLocked) return this.lockedStructure();
    if (this.wb.sheets.length <= 1) return;
    this.pushUndo();
    this.wb.sheets.splice(index, 1);
    this.wb.active = Math.max(0, index - 1);
    this.view.focus = { r: 0, c: 0 };
    this.view.anchor = { r: 0, c: 0 };
    this.recalc(true);
    this.emit();
  }

  renameSheet(name: string): void {
    if (this.wb.structureLocked) return this.lockedStructure();
    const sheet = this.sheet();
    const next = name.trim();
    if (!next || this.wb.sheets.some((item) => item !== sheet && item.name.toLowerCase() === next.toLowerCase())) {
      this.view.status = 'Name ist leer oder bereits vergeben.';
      this.emit();
      return;
    }
    this.pushUndo();
    const old = sheet.name;
    sheet.name = next;
    for (const sh of this.wb.sheets) {
      for (const cell of Object.values(sh.cells)) {
        cell.raw = cell.raw.replaceAll(`'${old}'!`, `'${next}'!`).replaceAll(`${old}!`, `${next}!`);
      }
      for (const table of sh.tables) if (table.sheet === old) table.sheet = next;
    }
    for (const item of this.wb.names) if (item.sheet === old) item.sheet = next;
    for (const item of this.wb.views) if (item.sheet === old) item.sheet = next;
    for (const scenario of this.wb.scenarios) for (const cell of scenario.cells) if (cell.sheet === old) cell.sheet = next;
    this.recalc(true);
    this.emit();
  }

  duplicateSheet(): void {
    if (this.wb.structureLocked) return this.lockedStructure();
    this.pushUndo();
    const copy = JSON.parse(JSON.stringify(this.sheet())) as Sheet;
    copy.name = `${copy.name} Kopie`;
    let n = 2;
    while (this.wb.sheets.some((sheet) => sheet.name.toLowerCase() === copy.name.toLowerCase())) {
      copy.name = `${this.sheet().name} Kopie ${n++}`;
    }
    for (const table of copy.tables) table.sheet = copy.name;
    this.wb.sheets.splice(this.wb.active + 1, 0, copy);
    this.activate(this.wb.active + 1);
  }

  activate(index: number): void {
    this.wb.active = clamp(index, 0, this.wb.sheets.length - 1);
    this.view.focus = { r: 0, c: 0 };
    this.view.anchor = { r: 0, c: 0 };
    this.view.editing = false;
    this.rebuildPaint();
    this.broadcastCursor();
    this.emit();
  }

  loadWorkbook(wb: Workbook): void {
    this.pushUndo();
    this.wb = normalizeWorkbook(wb);
    this.view.focus = { r: 0, c: 0 };
    this.view.anchor = { r: 0, c: 0 };
    this.view.editing = false;
    this.view.dialog = null;
    this.recalc(true);
    this.view.status = wb.title;
    this.emit();
  }

  newFromTemplate(id: string): void {
    const template = TEMPLATES.find((item) => item.id === id) ?? TEMPLATES[1];
    this.loadWorkbook(template.build());
  }

  toggleRecord(): void {
    if (this.view.recording) {
      this.view.recording = false;
      const code = this.view.macroLines.join('\n');
      if (code) {
        const name = `Makro${this.wb.macros.length + 1}`;
        this.wb.macros.push({ name, lang: 'js', code });
        this.view.status = `${name} aufgezeichnet`;
      } else this.view.status = 'Leere Aufzeichnung verworfen';
      this.view.macroLines = [];
    } else {
      this.view.recording = true;
      this.view.macroLines = [];
      this.view.status = 'Makro-Rekorder läuft';
    }
    this.emit();
  }

  playMacro(name: string): void {
    const macro = this.wb.macros.find((item) => item.name === name);
    if (macro) this.runScript(macro.lang, macro.code);
  }

  saveMacro(macro: Macro): void {
    this.wb.macros = this.wb.macros.filter((item) => item.name !== macro.name);
    this.wb.macros.push(macro);
    this.view.status = `${macro.name} gespeichert`;
    this.emit();
  }

  runScript(lang: Macro['lang'], code: string): string {
    this.pushUndo();
    const logs: string[] = [];
    const api = this.scriptApi(logs);
    let out = '';
    try {
      if (lang === 'js') out = runJavaScript(code, api);
      else if (lang === 'py') out = runPython(code, api);
      else out = runVba(code, api);
    } catch (error) {
      out = error instanceof Error ? error.message : String(error);
    }
    this.recalc(true);
    this.view.log = [...logs, out].filter(Boolean).slice(-40);
    this.view.status = out || 'Skript ausgeführt';
    this.emit();
    return out;
  }

  scriptApi(logs: string[] = this.view.log): ScriptApi {
    return {
      get: (addr) => {
        const pos = parseAddr(addr);
        if (!pos) return '';
        return this.sheet().cells[cellKey(pos.r, pos.c)]?.raw ?? '';
      },
      set: (addr, value) => {
        const pos = parseAddr(addr);
        if (!pos) return;
        this.setCell(pos.r, pos.c, value, { undo: false, recalc: false, record: false, emit: false, validation: false });
      },
      formula: (addr) => {
        const pos = parseAddr(addr);
        if (!pos) return '';
        const raw = this.sheet().cells[cellKey(pos.r, pos.c)]?.raw ?? '';
        return raw.startsWith('=') ? raw : '';
      },
      value: (addr) => {
        const pos = parseAddr(addr);
        if (!pos) return '';
        const raw = this.sheet().cells[cellKey(pos.r, pos.c)]?.raw ?? '';
        if (raw && !raw.startsWith('=')) {
          const lit = parseLiteral(raw);
          if (typeof lit === 'number') return String(lit);
          if (typeof lit === 'boolean') return lit ? 'WAHR' : 'FALSCH';
          return raw;
        }
        return this.display(pos.r, pos.c);
      },
      style: (addr, patch) => {
        const pos = parseAddr(addr);
        if (!pos) return;
        const cell = this.ensure(this.sheet(), pos.r, pos.c);
        cell.style = { ...(cell.style ?? {}), ...(patch as Style) };
      },
      sheet: (name) => {
        if (name) {
          const index = this.wb.sheets.findIndex((sheet) => sheet.name.toLowerCase() === name.toLowerCase());
          if (index >= 0) this.wb.active = index;
        }
        return this.sheet().name;
      },
      sheets: () => this.wb.sheets.map((sheet) => sheet.name),
      log: (msg) => logs.push(msg),
    };
  }

  toggleCollab(): void {
    this.view.collab = !this.view.collab;
    if (this.view.collab) this.openChannel();
    else {
      this.channel?.close();
      this.channel = null;
      this.view.peers = [];
    }
    this.view.status = this.view.collab ? 'Zusammenarbeit im Browser aktiv' : 'Zusammenarbeit aus';
    this.emit();
  }

  note(message: string): void {
    this.view.status = message;
    this.emit();
  }

  refresh(): void {
    this.recalc(true);
    this.view.status = 'Berechnet';
    this.emit();
  }

  recalc(force = false): void {
    if (this.wb.calc === 'manual' && !force) {
      this.view.dirty = true;
      return;
    }
    const tables = this.wb.sheets.flatMap((sheet) => sheet.tables.map((table) => ({ ...table, sheet: sheet.name })));
    this.computed = calculate({
      sheets: this.wb.sheets.map((sheet) => ({
        name: sheet.name,
        rows: sheet.rows,
        cols: sheet.cols,
        cells: sheet.cells,
        hiddenRows: [...this.hiddenRows(sheet)],
      })),
      names: this.wb.names,
      tables,
    });
    this.view.dirty = false;
    this.rebuildPaint();
  }

  private emit(): void {
    this.ver++;
    for (const listener of this.listeners) listener();
    this.queuePersist();
  }

  private queuePersist(): void {
    if (typeof localStorage === 'undefined') return;
    window.clearTimeout(this.persistTimer);
    this.persistTimer = window.setTimeout(() => {
      try {
        localStorage.setItem(STORE, JSON.stringify(this.wb));
      } catch {
        /* Speicher voll */
      }
    }, 250);
  }

  pushHistory(): void {
    this.pushUndo();
  }

  private pushUndo(): void {
    this.history.push(this.capture());
    if (this.history.length > 60) this.history.shift();
    this.future = [];
  }

  private capture(): string {
    const { versions, ...rest } = this.wb;
    void versions;
    return JSON.stringify(rest);
  }

  private restore(json: string): void {
    const versions = this.wb.versions;
    const next = normalizeWorkbook(JSON.parse(json) as Workbook);
    next.versions = versions;
    this.wb = next;
    this.view.editing = false;
    this.view.editAt = null;
    this.recalc(true);
    this.emit();
  }

  private put(sheet: Sheet, r: number, c: number, raw: string, style?: Style): void {
    if (r >= sheet.rows) sheet.rows = Math.min(5000, r + 20);
    if (c >= sheet.cols) sheet.cols = Math.min(256, c + 4);
    const key = cellKey(r, c);
    const prev = sheet.cells[key];
    if (!raw && !style && !prev?.style && !prev?.comment && !prev?.validation) {
      delete sheet.cells[key];
      return;
    }
    sheet.cells[key] = {
      raw,
      style: style ?? prev?.style,
      locked: prev?.locked,
      comment: prev?.comment,
      validation: prev?.validation,
      rev: (prev?.rev ?? 0) + 1,
    };
  }

  private ensure(sheet: Sheet, r: number, c: number): Cell {
    const key = cellKey(r, c);
    if (!sheet.cells[key]) sheet.cells[key] = { raw: '', rev: 1 };
    return sheet.cells[key];
  }

  private noteLiteral(r: number, c: number, raw: string): void {
    const cell = this.sheet().cells[cellKey(r, c)];
    if (!cell || cell.style?.numFmt) return;
    if (/^\d{1,2}\.\d{1,2}\.\d{2,4}$/.test(raw.trim())) cell.style = { numFmt: 'd' };
    else if (raw.trim().endsWith('%')) cell.style = { numFmt: 'p2' };
    else if (raw.includes('€')) cell.style = { numFmt: 'c2' };
  }

  private growTable(sheet: Sheet, r: number, c: number): void {
    for (const table of sheet.tables) {
      if (table.totalsRow) continue;
      if (c < table.c1 || c > table.c2 || r !== table.r2 + 1) continue;
      table.r2 = r;
      if (sheet.filter && sheet.filter.r1 === table.r1) sheet.filter.r2 = r;
    }
  }

  private applyPainter(pos: CellPos): void {
    if (!this.view.painter) return;
    this.pushUndo();
    const cell = this.ensure(this.sheet(), pos.r, pos.c);
    cell.style = { ...this.view.painter };
    this.view.painter = null;
  }

  pickPainter(): void {
    const style = this.sheet().cells[cellKey(this.view.focus.r, this.view.focus.c)]?.style;
    this.view.painter = style ? { ...style } : {};
    this.view.status = 'Format übertragen: nächste Zelle anklicken';
    this.emit();
  }

  private filterText(sheet: Sheet, r: number, c: number): string {
    const cell = sheet.cells[cellKey(r, c)];
    if (cell?.raw && !cell.raw.startsWith('=')) return cell.raw;
    const computed = this.comp(r, c, sheet);
    if (computed?.error) return computed.error;
    if (typeof computed?.value === 'number') return String(computed.value);
    if (typeof computed?.value === 'string') return computed.value;
    if (typeof computed?.value === 'boolean') return computed.value ? 'WAHR' : 'FALSCH';
    return cell?.raw ?? '';
  }

  private sortBlock(sheet: Sheet, r1: number, c1: number, r2: number, c2: number, keys: { col: number; asc: boolean }[]): void {
    const rows: { r: number; i: number; cells: { c: number; cell: Cell }[]; keys: (number | string)[] }[] = [];
    for (let r = r1; r <= r2; r++) {
      const cells: { c: number; cell: Cell }[] = [];
      for (let c = c1; c <= c2; c++) {
        const cell = sheet.cells[cellKey(r, c)];
        if (cell) cells.push({ c, cell: cloneCell(cell) });
      }
      const keyVals = keys.map((key) => {
        const n = this.numAt(r, key.col, sheet);
        if (n !== null) return n;
        return (sheet.cells[cellKey(r, key.col)]?.raw ?? '').toLocaleLowerCase('de-DE');
      });
      rows.push({ r, i: rows.length, cells, keys: keyVals });
    }
    rows.sort((a, b) => {
      for (let i = 0; i < keys.length; i++) {
        const va = a.keys[i];
        const vb = b.keys[i];
        let cmp = 0;
        if (typeof va === 'number' && typeof vb === 'number') cmp = va - vb;
        else cmp = String(va).localeCompare(String(vb), 'de');
        if (cmp) return keys[i].asc ? cmp : -cmp;
      }
      return a.i - b.i;
    });
    for (let r = r1; r <= r2; r++) for (let c = c1; c <= c2; c++) delete sheet.cells[cellKey(r, c)];
    rows.forEach((row, index) => {
      const dest = r1 + index;
      for (const entry of row.cells) {
        const raw = entry.cell.raw.startsWith('=') ? adjustFormulaCopy(entry.cell.raw, dest - row.r, 0) : entry.cell.raw;
        sheet.cells[cellKey(dest, entry.c)] = { ...entry.cell, raw };
      }
    });
  }

  private shift(axis: 'row' | 'col', at: number, delta: number): void {
    if (this.wb.structureLocked) return this.lockedStructure();
    const edited = this.sheet();
    this.pushUndo();
    for (const sheet of this.wb.sheets) {
      for (const cell of Object.values(sheet.cells)) {
        if (cell.raw.startsWith('=')) cell.raw = adjustFormulaStructure(cell.raw, sheet.name, edited.name, axis, at, delta);
      }
    }
    for (const name of this.wb.names) {
      if (name.formula) name.formula = adjustFormulaStructure(name.formula, name.sheet ?? edited.name, edited.name, axis, at, delta);
      if (name.sheet === edited.name && name.r1 !== undefined && name.r2 !== undefined && name.c1 !== undefined && name.c2 !== undefined) {
        if (axis === 'row') {
          const span = shiftSpan(name.r1, name.r2, at, delta);
          if (span) {
            name.r1 = span[0];
            name.r2 = span[1];
          }
        } else {
          const span = shiftSpan(name.c1, name.c2, at, delta);
          if (span) {
            name.c1 = span[0];
            name.c2 = span[1];
          }
        }
      }
    }
    edited.cells = remapCells(edited.cells, axis, at, delta);
    if (axis === 'row') {
      edited.rowHeights = remapIndex(edited.rowHeights, at, delta);
      edited.rows = Math.max(1, edited.rows + delta);
      shiftVertical(edited, at, delta);
    } else {
      edited.colWidths = remapIndex(edited.colWidths, at, delta);
      edited.cols = Math.max(1, edited.cols + delta);
      shiftHorizontal(edited, at, delta);
    }
    this.view.focus = { r: clamp(this.view.focus.r, 0, edited.rows - 1), c: clamp(this.view.focus.c, 0, edited.cols - 1) };
    this.view.anchor = { ...this.view.focus };
    this.recalc(true);
    this.emit();
  }

  private rebuildPaint(): void {
    this.paint.clear();
    const sheet = this.sheet();
    for (const table of sheet.tables) {
      if (!table.banded) continue;
      const end = table.totalsRow ? table.r2 - 1 : table.r2;
      for (let r = table.r1 + 1; r <= end; r++) {
        if ((r - table.r1) % 2 === 0) continue;
        for (let c = table.c1; c <= table.c2; c++) {
          if (sheet.cells[cellKey(r, c)]?.style?.fill) continue;
          this.paint.set(`${r},${c}`, { fill: this.view.theme === 'dark' ? '#243044' : '#e8f0f8' });
        }
      }
    }
    for (const rule of sheet.rules) {
      if (rule.kind === 'bar' || rule.kind === 'scale') {
        let min = Infinity;
        let max = -Infinity;
        const nums: { r: number; c: number; n: number }[] = [];
        for (let r = rule.r1; r <= rule.r2; r++) {
          for (let c = rule.c1; c <= rule.c2; c++) {
            const n = this.numAt(r, c, sheet);
            if (n === null) continue;
            min = Math.min(min, n);
            max = Math.max(max, n);
            nums.push({ r, c, n });
          }
        }
        for (const item of nums) {
          const t = max === min ? 1 : (item.n - min) / (max - min);
          if (rule.kind === 'bar') this.paint.set(`${item.r},${item.c}`, { ...(this.paint.get(`${item.r},${item.c}`) ?? {}), bar: max ? Math.max(0, item.n) / max : 0, fill: rule.fill });
          else this.paint.set(`${item.r},${item.c}`, { fill: ramp(t) });
        }
      } else if (rule.kind === 'dup') {
        const counts = new Map<string, { r: number; c: number }[]>();
        for (let r = rule.r1; r <= rule.r2; r++) {
          for (let c = rule.c1; c <= rule.c2; c++) {
            const text = this.filterText(sheet, r, c);
            if (!text) continue;
            const list = counts.get(text) ?? [];
            list.push({ r, c });
            counts.set(text, list);
          }
        }
        for (const list of counts.values()) {
          if (list.length < 2) continue;
          for (const pos of list) this.paint.set(`${pos.r},${pos.c}`, { fill: rule.fill ?? '#5c4b16', color: rule.color ?? '#fde68a' });
        }
      } else {
        for (let r = rule.r1; r <= rule.r2; r++) {
          for (let c = rule.c1; c <= rule.c2; c++) {
            if (!matchRule(rule, this.filterText(sheet, r, c), this.numAt(r, c, sheet))) continue;
            this.paint.set(`${r},${c}`, { fill: rule.fill, color: rule.color });
          }
        }
      }
    }
  }

  private record(line: string): void {
    if (this.view.recording) this.view.macroLines.push(line);
  }

  private lockedStructure(): void {
    this.view.status = 'Die Arbeitsmappenstruktur ist geschützt.';
    this.emit();
  }

  private openChannel(): void {
    if (typeof BroadcastChannel === 'undefined') return;
    this.channel?.close();
    this.channel = new BroadcastChannel('reckongrid-live');
    this.channel.onmessage = (event: MessageEvent<{ kind: string; sheet?: string; r?: number; c?: number; raw?: string; rev?: number; peer?: string; name?: string; color?: string }>) => {
      const msg = event.data;
      if (!msg || msg.peer === this.view.selfId) return;
      if (msg.kind === 'cell' && msg.sheet && msg.r !== undefined && msg.c !== undefined && msg.raw !== undefined) {
        const sheet = this.wb.sheets.find((item) => item.name === msg.sheet);
        if (!sheet) return;
        const key = cellKey(msg.r, msg.c);
        if ((sheet.cells[key]?.rev ?? 0) >= (msg.rev ?? 0)) return;
        this.remote = true;
        const active = this.wb.active;
        this.wb.active = this.wb.sheets.indexOf(sheet);
        this.setCell(msg.r, msg.c, msg.raw, { undo: false, record: false, validation: false });
        this.wb.active = active;
        this.remote = false;
      }
      if (msg.kind === 'cursor' && msg.peer && msg.r !== undefined && msg.c !== undefined && msg.sheet) {
        const color = msg.color ?? '#e0a12f';
        const name = msg.name ?? 'Kollege';
        const others = this.view.peers.filter((peer) => peer.id !== msg.peer);
        others.push({ id: msg.peer, name, color, sheet: msg.sheet, r: msg.r, c: msg.c });
        this.view.peers = others;
        this.emit();
      }
    };
    this.broadcastCursor();
  }

  private broadcastCursor(): void {
    if (!this.view.collab || !this.channel) return;
    this.channel.postMessage({
      kind: 'cursor',
      peer: this.view.selfId,
      name: 'Andreas Meyer',
      color: '#3d9b4f',
      sheet: this.sheet().name,
      r: this.view.focus.r,
      c: this.view.focus.c,
    });
  }
}

export function loadStoredWorkbook(): Workbook | null {
  if (typeof localStorage === 'undefined') return null;
  try {
    const text = localStorage.getItem(STORE);
    if (!text) return null;
    const parsed = JSON.parse(text) as Workbook;
    if (!parsed?.sheets?.length) return null;
    return normalizeWorkbook(parsed);
  } catch {
    return null;
  }
}

function clamp(n: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, n));
}

function cloneCell(cell: Cell): Cell {
  return {
    ...cell,
    style: cell.style ? { ...cell.style } : undefined,
    validation: cell.validation
      ? { ...cell.validation, list: cell.validation.list ? [...cell.validation.list] : undefined }
      : undefined,
  };
}

function parseRange(input: string): Bounds | null {
  const clean = input.trim().replace(/\$/g, '');
  const [a, b] = clean.split(':');
  const p1 = parseAddr(a);
  const p2 = b ? parseAddr(b) : p1;
  if (!p1 || !p2) return null;
  return { r1: Math.min(p1.r, p2.r), c1: Math.min(p1.c, p2.c), r2: Math.max(p1.r, p2.r), c2: Math.max(p1.c, p2.c) };
}

function numRaw(n: number): string {
  if (!Number.isFinite(n)) return '0';
  return String(Math.round(n * 1e10) / 1e10);
}

function invalid(validation: Validation, raw: string): string | null {
  if (!raw.trim()) return null;
  if (validation.type === 'list') {
    if (validation.list && !validation.list.includes(raw)) return validation.message ?? 'Wert steht nicht in der Liste.';
    return null;
  }
  const lit = parseLiteral(raw);
  if (typeof lit !== 'number') return validation.message ?? 'Zahl erwartet.';
  if (validation.type === 'whole' && !Number.isInteger(lit)) return validation.message ?? 'Ganze Zahl erwartet.';
  if (validation.min !== undefined && lit < validation.min) return validation.message ?? `Mindestens ${validation.min}.`;
  if (validation.max !== undefined && lit > validation.max) return validation.message ?? `Höchstens ${validation.max}.`;
  return null;
}

function remapCells(cells: Record<string, Cell>, axis: 'row' | 'col', at: number, delta: number): Record<string, Cell> {
  const out: Record<string, Cell> = {};
  for (const [key, cell] of Object.entries(cells)) {
    const [r, c] = key.split(',').map(Number);
    if (axis === 'row') {
      const nr = shiftCoord(r, at, delta);
      if (nr !== null) out[cellKey(nr, c)] = cell;
    } else {
      const nc = shiftCoord(c, at, delta);
      if (nc !== null) out[cellKey(r, nc)] = cell;
    }
  }
  return out;
}

function remapIndex(map: Record<number, number>, at: number, delta: number): Record<number, number> {
  const out: Record<number, number> = {};
  for (const [key, value] of Object.entries(map)) {
    const next = shiftCoord(Number(key), at, delta);
    if (next !== null) out[next] = value;
  }
  return out;
}

function shiftVertical(sheet: Sheet, at: number, delta: number): void {
  sheet.merges = sheet.merges.flatMap((item) => {
    const span = shiftSpan(item.r1, item.r2, at, delta);
    return span ? [{ ...item, r1: span[0], r2: span[1] }] : [];
  });
  sheet.tables = sheet.tables.flatMap((item) => {
    const span = shiftSpan(item.r1, item.r2, at, delta);
    return span ? [{ ...item, r1: span[0], r2: span[1] }] : [];
  });
  sheet.charts = sheet.charts.flatMap((item) => {
    const span = shiftSpan(item.r1, item.r2, at, delta);
    return span ? [{ ...item, r1: span[0], r2: span[1] }] : [];
  });
  sheet.rules = sheet.rules.flatMap((item) => {
    const span = shiftSpan(item.r1, item.r2, at, delta);
    return span ? [{ ...item, r1: span[0], r2: span[1] }] : [];
  });
  sheet.groups = sheet.groups.flatMap((item) => {
    const span = shiftSpan(item.start, item.end, at, delta);
    return span ? [{ ...item, start: span[0], end: span[1] }] : [];
  });
  if (sheet.filter) {
    const span = shiftSpan(sheet.filter.r1, sheet.filter.r2, at, delta);
    sheet.filter = span ? { ...sheet.filter, r1: span[0], r2: span[1] } : null;
  }
}

function shiftHorizontal(sheet: Sheet, at: number, delta: number): void {
  const move = (c1: number, c2: number) => shiftSpan(c1, c2, at, delta);
  sheet.merges = sheet.merges.flatMap((item) => {
    const span = move(item.c1, item.c2);
    return span ? [{ ...item, c1: span[0], c2: span[1] }] : [];
  });
  sheet.tables = sheet.tables.flatMap((item) => {
    const span = move(item.c1, item.c2);
    return span ? [{ ...item, c1: span[0], c2: span[1] }] : [];
  });
  sheet.charts = sheet.charts.flatMap((item) => {
    const span = move(item.c1, item.c2);
    return span ? [{ ...item, c1: span[0], c2: span[1] }] : [];
  });
  sheet.rules = sheet.rules.flatMap((item) => {
    const span = move(item.c1, item.c2);
    return span ? [{ ...item, c1: span[0], c2: span[1] }] : [];
  });
  sheet.slicers = sheet.slicers.flatMap((item) => {
    const next = shiftCoord(item.col, at, delta);
    return next === null ? [] : [{ ...item, col: next }];
  });
  if (sheet.filter) {
    const span = move(sheet.filter.c1, sheet.filter.c2);
    if (!span) sheet.filter = null;
    else {
      const selected: Record<number, string[] | null> = {};
      for (const [key, value] of Object.entries(sheet.filter.selected)) {
        const next = shiftCoord(Number(key), at, delta);
        if (next !== null) selected[next] = value;
      }
      sheet.filter = { ...sheet.filter, c1: span[0], c2: span[1], selected };
    }
  }
}

function matchRule(rule: CondRule, text: string, num: number | null): boolean {
  if (rule.kind === 'blank') return text === '';
  if (rule.kind === 'contains') return rule.value !== undefined && text.toLocaleLowerCase('de-DE').includes(rule.value.toLocaleLowerCase('de-DE'));
  if (rule.kind === 'eq') return text === rule.value || (num !== null && Number(rule.value) === num);
  if (num === null || rule.value === undefined) return false;
  const a = Number(String(rule.value).replace(',', '.'));
  const b = Number(String(rule.value2 ?? '').replace(',', '.'));
  if (rule.kind === 'gt') return num > a;
  if (rule.kind === 'lt') return num < a;
  if (rule.kind === 'between') return num >= Math.min(a, b) && num <= Math.max(a, b);
  return false;
}

function ramp(t: number): string {
  const x = clamp(t, 0, 1);
  const stops = [
    [212, 84, 74],
    [224, 161, 47],
    [61, 155, 79],
  ];
  const scaled = x * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(scaled));
  const f = scaled - i;
  const mix = stops[i].map((v, k) => Math.round(v + (stops[i + 1][k] - v) * f));
  return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`;
}

function contrast(fg: string, bg: string): number {
  const L1 = luminance(fg);
  const L2 = luminance(bg);
  const light = Math.max(L1, L2);
  const dark = Math.min(L1, L2);
  return (light + 0.05) / (dark + 0.05);
}

function luminance(hex: string): number {
  const rgb = hexToRgb(hex);
  const chan = rgb.map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * chan[0] + 0.7152 * chan[1] + 0.0722 * chan[2];
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  if (h.length === 3) return [parseInt(h[0] + h[0], 16), parseInt(h[1] + h[1], 16), parseInt(h[2] + h[2], 16)];
  return [parseInt(h.slice(0, 2), 16) || 0, parseInt(h.slice(2, 4), 16) || 0, parseInt(h.slice(4, 6), 16) || 0];
}

function luhn(digits: string): boolean {
  let sum = 0;
  let alt = false;
  for (let i = digits.length - 1; i >= 0; i--) {
    let n = digits.charCodeAt(i) - 48;
    if (alt) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
    alt = !alt;
  }
  return sum % 10 === 0;
}

const WEEK = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'];
const MONTHS = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];

function stepText(value: string, delta: number): string {
  const lists = [WEEK, MONTHS];
  for (const list of lists) {
    const index = list.findIndex((item) => item.toLocaleLowerCase('de-DE') === value.toLocaleLowerCase('de-DE'));
    if (index >= 0) return list[(index + delta) % list.length];
  }
  return value;
}

function detectFill(source: string, sample: string): ((value: string) => string) | null {
  if (!source || !sample) return null;
  const parts = source.split(/\s+/);
  if (parts[0] === sample) return (value) => value.split(/\s+/)[0] ?? '';
  if (parts[parts.length - 1] === sample) return (value) => value.split(/\s+/).at(-1) ?? '';
  if (source.toLocaleLowerCase('de-DE') === sample) return (value) => value.toLocaleLowerCase('de-DE');
  if (source.toLocaleUpperCase('de-DE') === sample) return (value) => value.toLocaleUpperCase('de-DE');
  const at = source.indexOf('@');
  if (at > 0 && sample === source.slice(0, at)) return (value) => value.split('@')[0] ?? value;
  return null;
}
