import { cellKey } from './addr';
import { emptySheet, emptyWorkbook, type Cell, type Sheet, type Workbook } from './types';

function put(sheet: Sheet, r: number, c: number, raw: string, style?: Cell['style']): void {
  sheet.cells[cellKey(r, c)] = { raw, style, rev: 1 };
}

const head = { bold: true, color: '#ffffff', fill: '#0d4f9a', align: 'left' as const };
const input = { fill: '#12304d', color: '#d6ecff' };
const money = { numFmt: 'c2' as const };
const moneyIn = { numFmt: 'c2' as const, fill: '#12304d', color: '#d6ecff' };
const title = { bold: true, size: 16, color: '#ffffff', fill: '#0c4a8c' };
const section = { bold: true, color: '#9fd0ff', fill: '#16324f' };
const kpi = { bold: true, numFmt: 'c2' as const, fill: '#14532d', color: '#d1fae5' };

export function umsatzTemplate(): Workbook {
  const wb = emptyWorkbook('Umsatzdatenbank');
  const s = wb.sheets[0];
  s.name = 'Umsatz';
  s.freezeRows = 4;
  s.colWidths = { 0: 110, 1: 120, 2: 80, 3: 120, 4: 90, 6: 150, 7: 130 };
  put(s, 0, 0, 'ReckonGrid Umsatzdatenbank', title);
  s.merges.push({ r1: 0, c1: 0, r2: 0, c2: 4 });
  put(s, 1, 0, 'Andreas Meyer  ·  ame@sellerbach.de', { color: '#9ec7ef', italic: true });
  put(s, 3, 0, 'Region', head);
  put(s, 3, 1, 'Produkt', head);
  put(s, 3, 2, 'Jahr', head);
  put(s, 3, 3, 'Umsatz', head);
  put(s, 3, 4, 'Menge', head);
  const rows: [string, string, number, number, number][] = [
    ['Nord', 'Stuhl', 2025, 12000, 30],
    ['Nord', 'Tisch', 2026, 18500, 20],
    ['Süd', 'Stuhl', 2026, 9600, 24],
    ['Süd', 'Lampe', 2025, 4200, 40],
    ['Ost', 'Tisch', 2026, 15000, 15],
    ['West', 'Lampe', 2026, 6100, 50],
    ['Nord', 'Lampe', 2026, 7300, 35],
    ['Ost', 'Stuhl', 2025, 8100, 22],
    ['West', 'Tisch', 2025, 13400, 12],
    ['Süd', 'Tisch', 2026, 11200, 11],
    ['Nord', 'Stuhl', 2026, 5400, 14],
    ['Ost', 'Lampe', 2026, 3900, 18],
  ];
  rows.forEach((row, i) => {
    put(s, 4 + i, 0, row[0]);
    put(s, 4 + i, 1, row[1]);
    put(s, 4 + i, 2, String(row[2]), { align: 'center' });
    put(s, 4 + i, 3, String(row[3]), money);
    put(s, 4 + i, 4, String(row[4]), { align: 'right' });
  });
  const last = 4 + rows.length - 1;
  s.tables.push({ name: 'Umsatz', sheet: 'Umsatz', r1: 3, c1: 0, r2: last, c2: 4, banded: true });
  s.filter = { r1: 3, c1: 0, r2: last, c2: 4, selected: {} };
  s.rules.push({ id: 'bar1', r1: 4, c1: 3, r2: last, c2: 3, kind: 'bar', fill: '#3d9b4f' });
  s.rules.push({ id: 'low', r1: 4, c1: 4, r2: last, c2: 4, kind: 'lt', value: '15', fill: '#5c2b2b', color: '#fecaca' });

  put(s, 3, 6, 'Suchkriterien', section);
  put(s, 4, 6, 'Region', head);
  put(s, 4, 7, 'Jahr', head);
  put(s, 5, 6, 'Nord', input);
  put(s, 5, 7, '>2025', input);
  put(s, 7, 6, 'Kennzahl', section);
  put(s, 7, 7, 'Wert', section);
  const kpis: [string, string][] = [
    ['Summe Nord ab 2026', '=DSUMME(A4:E16;D4;G5:H6)'],
    ['Anzahl', '=DANZAHL(A4:E16;"Umsatz";G5:H6)'],
    ['Maximum', '=DMAX(A4:E16;"Umsatz";G5:H6)'],
    ['Minimum', '=DMIN(A4:E16;"Umsatz";G5:H6)'],
    ['Mittelwert', '=DMITTELWERT(A4:E16;"Umsatz";G5:H6)'],
    ['Gesamt (Tabelle)', '=SUMME(Umsatz[Umsatz])'],
    ['Gefiltert', '=TEILERGEBNIS(9;D5:D16)'],
  ];
  kpis.forEach((k, i) => {
    put(s, 8 + i, 6, k[0]);
    put(s, 8 + i, 7, k[1], i === 1 ? { bold: true, align: 'right' } : kpi);
  });
  put(s, 16, 6, 'Regionen', section);
  put(s, 17, 6, '=SORTIEREN(EINDEUTIG(A5:A16))');
  put(s, 16, 7, 'Trend Menge', section);
  put(s, 17, 7, '=MINIATUR(E5:E16;"linie")');
  s.charts.push({
    id: 'c1',
    type: 'column',
    r1: 8,
    c1: 6,
    r2: 12,
    c2: 7,
    title: 'Kennzahlen',
    x: 980,
    y: 40,
    w: 420,
    h: 260,
    hasHeader: true,
  });
  wb.names.push({ name: 'Datenbank', sheet: 'Umsatz', r1: 3, c1: 0, r2: last, c2: 4 });
  wb.names.push({
    name: 'Verdoppeln',
    formula: '=LAMBDA(x;x*2)',
  });

  const kredit = emptySheet('Kredit');
  kredit.colWidths = { 0: 220, 1: 160 };
  put(kredit, 0, 0, 'Kreditrechner', title);
  kredit.merges.push({ r1: 0, c1: 0, r2: 0, c2: 1 });
  put(kredit, 2, 0, 'Darlehen', section);
  put(kredit, 2, 1, '250000', moneyIn);
  put(kredit, 3, 0, 'Jahreszins', section);
  put(kredit, 3, 1, '3,5%', { ...input, numFmt: 'p2' });
  put(kredit, 4, 0, 'Jahre', section);
  put(kredit, 4, 1, '30', input);
  put(kredit, 6, 0, 'Monatliche Rate', section);
  put(kredit, 6, 1, '=RMZ(B4/12;B5*12;B3)', kpi);
  put(kredit, 7, 0, 'Zinsen gesamt', section);
  put(kredit, 7, 1, '=B7*B5*12-B3', { numFmt: 'c2', color: '#fecaca' });
  put(kredit, 8, 0, 'Rate bei 2,5 %', section);
  put(kredit, 8, 1, '=RMZ(2,5%/12;B5*12;B3)', money);
  put(kredit, 10, 0, 'Zielwertsuche: Rate auf 1.000 € drücken über den Zinssatz in B4.', { italic: true, color: '#9ec7ef' });
  wb.sheets.push(kredit);

  const fn = emptySheet('Funktionen');
  fn.colWidths = { 0: 280, 1: 320, 2: 180 };
  put(fn, 0, 0, 'Formel', head);
  put(fn, 0, 1, 'Beispiel', head);
  put(fn, 0, 2, 'Ergebnis', head);
  const samples: [string, string][] = [
    ['Summe', '=SUMME(1;2;3;4)'],
    ['Wenn', '=WENN(2>1;"ja";"nein")'],
    ['Text', '=TEXTKETTE("Reckon";"Grid")'],
    ['Datum', '=TEXT(DATUM(2026;10;20);"TT.MM.JJJJ")'],
    ['Runden', '=RUNDEN(1,256;2)'],
    ['XVERWEIS lebt auf Umsatz', "=XVERWEIS(\"Tisch\";Umsatz!B5:B16;Umsatz!D5:D16)"],
    ['Sequenz', '=SEQUENZ(1;5;2;2)'],
    ['Lambda-Name', '=Verdoppeln(21)'],
    ['Umwandeln km', '=UMWANDELN(1;"mi";"km")'],
    ['Komplex', '=IMABS("3+4i")'],
  ];
  samples.forEach((row, i) => {
    put(fn, 1 + i, 0, row[0]);
    put(fn, 1 + i, 1, row[1], { color: '#9fd0ff' });
    put(fn, 1 + i, 2, `=B${2 + i}`);
  });
  wb.sheets.push(fn);
  wb.active = 0;
  return wb;
}

export function haushaltTemplate(): Workbook {
  const wb = emptyWorkbook('Haushaltsbuch');
  const s = wb.sheets[0];
  s.name = 'Haushalt';
  put(s, 0, 0, 'Haushaltsbuch', title);
  s.merges.push({ r1: 0, c1: 0, r2: 0, c2: 4 });
  ['Datum', 'Kategorie', 'Beschreibung', 'Einnahme', 'Ausgabe'].forEach((h, c) => put(s, 2, c, h, head));
  const lines: [string, string, string, string, string][] = [
    ['01.10.2026', 'Gehalt', 'Oktober', '4200', ''],
    ['02.10.2026', 'Miete', 'Wohnung', '', '1450'],
    ['03.10.2026', 'Lebensmittel', 'Woche 40', '', '186,40'],
    ['05.10.2026', 'Mobilität', 'Bahn', '', '49'],
    ['08.10.2026', 'Nebenjob', 'Workshop', '350', ''],
  ];
  lines.forEach((row, i) => row.forEach((v, c) => put(s, 3 + i, c, v, c >= 3 ? money : c === 0 ? { numFmt: 'd' } : undefined)));
  put(s, 9, 2, 'Saldo', section);
  put(s, 9, 3, '=SUMME(D4:D8)-SUMME(E4:E8)', kpi);
  put(s, 10, 2, 'Ausgaben Lebensmittel', section);
  put(s, 10, 3, '=SUMMEWENN(B4:B8;"Lebensmittel";E4:E8)', money);
  s.colWidths = { 0: 120, 1: 140, 2: 200, 3: 130, 4: 130 };
  return wb;
}

export function lagerTemplate(): Workbook {
  const wb = emptyWorkbook('Lager');
  const s = wb.sheets[0];
  s.name = 'Lager';
  put(s, 0, 0, 'Lagerbestand', title);
  ['Artikel', 'Lieferant', 'Bestand', 'Mindest', 'Preis', 'Wert'].forEach((h, c) => put(s, 2, c, h, head));
  const rows = [
    ['Eiche Platte', 'Nordholz', 12, 8, 84, '=C4*E4'],
    ['Stahlrohr', 'Ostmetall', 4, 10, 16.5, '=C5*E5'],
    ['Lack weiß', 'Südcolor', 30, 12, 9.9, '=C6*E6'],
    ['Schraube M8', 'Ostmetall', 400, 200, 0.12, '=C7*E7'],
  ];
  rows.forEach((row, i) => row.forEach((v, c) => put(s, 3 + i, c, String(v), c === 4 || c === 5 ? money : undefined)));
  s.rules.push({ id: 'min', r1: 3, c1: 2, r2: 6, c2: 2, kind: 'lt', value: '10', fill: '#5c2b2b', color: '#fecaca' });
  put(s, 2, 7, 'Lieferant', head);
  put(s, 3, 7, 'Ostmetall', input);
  put(s, 5, 6, 'Wert Lieferant', section);
  put(s, 5, 7, '=DSUMME(A3:F7;"Wert";H3:H4)', kpi);
  s.colWidths = { 0: 140, 1: 120, 5: 110, 6: 140, 7: 130 };
  return wb;
}

export function projektTemplate(): Workbook {
  const wb = emptyWorkbook('Projektplan');
  const s = wb.sheets[0];
  put(s, 0, 0, 'Projektplan', title);
  ['Aufgabe', 'Start', 'Ende', 'Dauer (Tage)', 'Status', 'Fortschritt'].forEach((h, c) => put(s, 2, c, h, head));
  const rows: [string, string, string, string, string, string][] = [
    ['Kickoff', '01.10.2026', '01.10.2026', '=NETTOARBEITSTAGE(B4;C4)', 'fertig', '1'],
    ['Datenmodell', '02.10.2026', '10.10.2026', '=NETTOARBEITSTAGE(B5;C5)', 'aktiv', '0,7'],
    ['Oberfläche', '06.10.2026', '24.10.2026', '=NETTOARBEITSTAGE(B6;C6)', 'aktiv', '0,4'],
    ['Abnahme', '27.10.2026', '31.10.2026', '=NETTOARBEITSTAGE(B7;C7)', 'offen', '0'],
  ];
  rows.forEach((row, i) =>
    row.forEach((v, c) =>
      put(s, 3 + i, c, v, c === 1 || c === 2 ? { numFmt: 'd' } : c === 5 ? { numFmt: 'p0' } : undefined),
    ),
  );
  s.rules.push({ id: 'prog', r1: 3, c1: 5, r2: 6, c2: 5, kind: 'bar', fill: '#2f7fe0' });
  s.colWidths = { 0: 160, 1: 120, 2: 120, 3: 130, 4: 100, 5: 120 };
  return wb;
}

export function blankTemplate(): Workbook {
  return emptyWorkbook('Unbenannt 1');
}

export const TEMPLATES: { id: string; name: string; hint: string; build: () => Workbook }[] = [
  { id: 'blank', name: 'Leere Arbeitsmappe', hint: 'Wie das leere PlanMaker-Raster', build: blankTemplate },
  { id: 'umsatz', name: 'Umsatzdatenbank', hint: 'D-Funktionen, Filter, Diagramm, LAMBDA', build: umsatzTemplate },
  { id: 'haushalt', name: 'Haushaltsbuch', hint: 'Einnahmen, Ausgaben, SUMMEWENN', build: haushaltTemplate },
  { id: 'lager', name: 'Lagerbestand', hint: 'Mindestbestand und DSUMME', build: lagerTemplate },
  { id: 'projekt', name: 'Projektplan', hint: 'Arbeitstage und Datenbalken', build: projektTemplate },
];
