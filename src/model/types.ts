import type { NumFmt } from '../formula/format';
import type { NameInput, TableInput } from '../formula/functions';

export type { NumFmt };

export interface Style {
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  strike?: boolean;
  font?: string;
  size?: number;
  color?: string;
  fill?: string;
  align?: 'left' | 'center' | 'right';
  valign?: 'top' | 'middle' | 'bottom';
  wrap?: boolean;
  numFmt?: NumFmt;
  border?: 'all' | 'outer' | 'bottom' | 'thick' | 'none';
}

export interface Validation {
  type: 'list' | 'whole' | 'decimal';
  list?: string[];
  min?: number;
  max?: number;
  message?: string;
}

export interface Cell {
  raw: string;
  style?: Style;
  locked?: boolean;
  comment?: string;
  validation?: Validation;
  rev?: number;
}

export type ChartType = 'column' | 'bar' | 'line' | 'pie' | 'area' | 'scatter' | 'radar' | 'waterfall' | 'funnel' | 'doughnut';

export interface Chart {
  id: string;
  type: ChartType;
  r1: number;
  c1: number;
  r2: number;
  c2: number;
  title: string;
  x: number;
  y: number;
  w: number;
  h: number;
  hasHeader: boolean;
}

export interface CondRule {
  id: string;
  r1: number;
  c1: number;
  r2: number;
  c2: number;
  kind: 'gt' | 'lt' | 'eq' | 'between' | 'contains' | 'dup' | 'scale' | 'bar' | 'blank';
  value?: string;
  value2?: string;
  fill?: string;
  color?: string;
}

export interface AutoFilter {
  r1: number;
  c1: number;
  r2: number;
  c2: number;
  selected: Record<number, string[] | null>;
}

export interface RowGroup {
  start: number;
  end: number;
  collapsed: boolean;
}

export interface Slicer {
  id: string;
  col: number;
  title: string;
  x: number;
  y: number;
}

export interface Sheet {
  name: string;
  cells: Record<string, Cell>;
  rows: number;
  cols: number;
  colWidths: Record<number, number>;
  rowHeights: Record<number, number>;
  freezeRows: number;
  freezeCols: number;
  merges: { r1: number; c1: number; r2: number; c2: number }[];
  tables: (TableInput & { banded?: boolean })[];
  charts: Chart[];
  rules: CondRule[];
  filter: AutoFilter | null;
  groups: RowGroup[];
  slicers: Slicer[];
  protected: boolean;
  passwordHash?: string;
  showGrid: boolean;
  tabColor?: string;
}

export interface Scenario {
  name: string;
  cells: { sheet: string; r: number; c: number; raw: string }[];
}

export interface SheetView {
  name: string;
  sheet: string;
  filter: AutoFilter | null;
  groups: RowGroup[];
}

export interface VersionSnap {
  id: string;
  at: number;
  label: string;
  json: string;
}

export interface Macro {
  name: string;
  lang: 'js' | 'py' | 'vba';
  code: string;
}

export interface Workbook {
  title: string;
  sheets: Sheet[];
  active: number;
  names: NameInput[];
  scenarios: Scenario[];
  views: SheetView[];
  versions: VersionSnap[];
  macros: Macro[];
  calc: 'auto' | 'manual';
  structureLocked?: boolean;
}

export interface DialogState {
  type: string;
  [key: string]: unknown;
}

export const AUTHOR = { name: 'Andreas Meyer', email: 'ame@sellerbach.de', app: 'ReckonGrid', version: '1.0.0' };

export function emptySheet(name: string): Sheet {
  return {
    name,
    cells: {},
    rows: 200,
    cols: 26,
    colWidths: {},
    rowHeights: {},
    freezeRows: 0,
    freezeCols: 0,
    merges: [],
    tables: [],
    charts: [],
    rules: [],
    filter: null,
    groups: [],
    slicers: [],
    protected: false,
    showGrid: true,
  };
}

export function emptyWorkbook(title = 'Unbenannt 1'): Workbook {
  return {
    title,
    sheets: [emptySheet('Tabelle1')],
    active: 0,
    names: [],
    scenarios: [],
    views: [],
    versions: [],
    macros: [],
    calc: 'auto',
  };
}

/** Ergänzt fehlende Felder aus älteren Speicherständen. */
export function normalizeWorkbook(wb: Workbook): Workbook {
  wb.sheets ||= [];
  wb.names ||= [];
  wb.scenarios ||= [];
  wb.views ||= [];
  wb.versions ||= [];
  wb.macros ||= [];
  wb.calc ||= 'auto';
  if (!wb.sheets.length) wb.sheets.push(emptySheet('Tabelle1'));
  wb.active = Math.max(0, Math.min(wb.active ?? 0, wb.sheets.length - 1));
  for (const s of wb.sheets) {
    s.cells ||= {};
    s.colWidths ||= {};
    s.rowHeights ||= {};
    s.merges ||= [];
    s.tables ||= [];
    s.charts ||= [];
    s.rules ||= [];
    s.groups ||= [];
    s.slicers ||= [];
    s.rows = s.rows || 200;
    s.cols = s.cols || 26;
    s.freezeRows ||= 0;
    s.freezeCols ||= 0;
    s.filter ??= null;
    s.showGrid ??= true;
    s.protected ??= false;
  }
  return wb;
}
