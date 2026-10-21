import { useRef, type ReactNode, type SyntheticEvent } from 'react';
import type { NumFmt } from '../formula/format';
import { saveCsv, saveRggrid, workbookToOds, workbookToXls, workbookToXlsx } from '../io/files';
import type { GridController, RibbonTab } from '../model/controller';
import type { ChartType, Style } from '../model/types';
import { useGrid } from './useGrid';

const TABS: { id: RibbonTab; label: string }[] = [
  { id: 'datei', label: 'Datei' },
  { id: 'start', label: 'Start' },
  { id: 'einfuegen', label: 'Einfügen' },
  { id: 'layout', label: 'Layout' },
  { id: 'formeln', label: 'Formeln' },
  { id: 'daten', label: 'Daten' },
  { id: 'ueberpruefen', label: 'Überprüfen' },
  { id: 'ansicht', label: 'Ansicht' },
];

const COLORS = ['#ffffff', '#e6e6e6', '#1b1b1b', '#f4c7c3', '#fce8b2', '#d9ead3', '#cfe2f3', '#d9d2e9', '#5c2b2b', '#14532d', '#0c4a8c', '#e0a12f', '#3d9b4f', '#2f7fe0', '#d4544a', '#8b6ad6'];
const FONTS = ['Segoe UI', 'Arial', 'Calibri', 'Georgia', 'Consolas'];
const FMTS: { id: NumFmt; label: string }[] = [
  { id: 'g', label: 'Standard' },
  { id: 'n2', label: 'Zahl' },
  { id: 'c2', label: 'Währung' },
  { id: 'p0', label: 'Prozent' },
  { id: 'd', label: 'Datum' },
  { id: 't', label: 'Uhrzeit' },
  { id: 'e', label: 'Wissenschaft' },
  { id: '@', label: 'Text' },
];
const CHARTS: { id: ChartType; label: string }[] = [
  { id: 'column', label: 'Säule' },
  { id: 'bar', label: 'Balken' },
  { id: 'line', label: 'Linie' },
  { id: 'area', label: 'Fläche' },
  { id: 'pie', label: 'Kreis' },
  { id: 'doughnut', label: 'Ring' },
  { id: 'scatter', label: 'Punkt' },
  { id: 'radar', label: 'Netz' },
  { id: 'waterfall', label: 'Wasserfall' },
  { id: 'funnel', label: 'Trichter' },
  { id: 'treemap', label: 'Treemap' },
  { id: 'sunburst', label: 'Sunburst' },
  { id: 'pareto', label: 'Pareto' },
  { id: 'boxplot', label: 'Boxplot' },
];

export function TabBar({ ctl }: { ctl: GridController }) {
  useGrid(ctl);
  return (
    <nav className="tabs">
      {TABS.map((tab) => (
        <button key={tab.id} type="button" className={ctl.view.tab === tab.id ? 'on' : ''} onClick={() => ctl.setTab(tab.id)}>
          {tab.label}
        </button>
      ))}
    </nav>
  );
}

export function Ribbon({ ctl, onOpen }: { ctl: GridController; onOpen: () => void }) {
  useGrid(ctl);
  const tab = ctl.view.tab;
  const style = ctl.sheet().cells[`${ctl.view.focus.r},${ctl.view.focus.c}`]?.style;
  const font = FONTS.includes(style?.font ?? '') ? style?.font ?? 'Segoe UI' : 'Segoe UI';
  const size = style?.size ?? 12;
  const sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28].includes(size)
    ? [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28]
    : [size, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28].sort((a, b) => a - b);
  const fmt = FMTS.some((item) => item.id === style?.numFmt) ? style?.numFmt ?? 'g' : 'g';
  return (
    <div className="ribbon" role="toolbar" aria-label={tab}>
      {tab === 'datei' && (
        <Group label="Datei">
          <Btn tall label="Neu" onClick={() => ctl.openDialog('templates')} />
          <Btn tall label="Öffnen" onClick={onOpen} />
          <Btn tall label="Speichern" onClick={() => saveRggrid(ctl.wb)} />
          <Btn label="XLSX" onClick={() => workbookToXlsx(ctl.wb, ctl.computed)} />
          <Btn label="CSV" onClick={() => saveCsv(ctl.sheet(), ctl.computed, false)} />
          <Btn label="Werte" onClick={() => saveCsv(ctl.sheet(), ctl.computed, true)} />
          <Btn label="ODS" onClick={() => workbookToOds(ctl.wb, ctl.computed)} />
          <Btn label="XLS" onClick={() => workbookToXls(ctl.wb, ctl.computed)} />
          <Btn label="PDF" onClick={() => window.print()} />
          <Btn label="AES" onClick={() => ctl.openDialog('seal')} />
        </Group>
      )}
      {tab === 'start' && (
        <>
          <Group label="Zwischenablage">
            <Btn tall label="Einfügen" icon="paste" onClick={() => ctl.paste()} />
            <Btn label="Ausschneiden" icon="cut" onClick={() => ctl.copy(true)} />
            <Btn label="Kopieren" icon="copy" onClick={() => ctl.copy(false)} />
            <Btn label="Format übertragen" icon="brush" onClick={() => ctl.pickPainter()} />
          </Group>
          <Group label="Schriftart" wide>
            <select className="field" aria-label="Schriftart" value={font} onChange={(event) => ctl.patchStyle({ font: event.target.value })}>
              {FONTS.map((name) => <option key={name}>{name}</option>)}
            </select>
            <select className="field" aria-label="Schriftgrad" value={size} onChange={(event) => ctl.patchStyle({ size: Number(event.target.value) })}>
              {sizes.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <Btn label="Fett" icon="bold" on={!!style?.bold} onClick={() => ctl.toggleStyle('bold')} />
            <Btn label="Kursiv" icon="italic" on={!!style?.italic} onClick={() => ctl.toggleStyle('italic')} />
            <Btn label="Unterstrichen" icon="underline" on={!!style?.underline} onClick={() => ctl.toggleStyle('underline')} />
            <Btn label="Durchgestrichen" icon="strike" on={!!style?.strike} onClick={() => ctl.toggleStyle('strike')} />
            <Palette title="Schriftfarbe" onPick={(color) => ctl.patchStyle({ color })} />
            <Palette title="Füllfarbe" onPick={(fill) => ctl.patchStyle({ fill })} />
          </Group>
          <Group label="Ausrichtung" wide>
            <Btn label="Linksbündig" icon="left" on={style?.align === 'left'} onClick={() => ctl.patchStyle({ align: 'left' })} />
            <Btn label="Zentriert" icon="center" on={style?.align === 'center'} onClick={() => ctl.patchStyle({ align: 'center' })} />
            <Btn label="Rechtsbündig" icon="right" on={style?.align === 'right'} onClick={() => ctl.patchStyle({ align: 'right' })} />
            <Btn label="Oben" icon="top" on={style?.valign === 'top'} onClick={() => ctl.patchStyle({ valign: 'top' })} />
            <Btn label="Mittig" icon="middle" on={style?.valign === 'middle'} onClick={() => ctl.patchStyle({ valign: 'middle' })} />
            <Btn label="Unten" icon="bottom" on={style?.valign === 'bottom'} onClick={() => ctl.patchStyle({ valign: 'bottom' })} />
            <Btn label="Zeilenumbruch" icon="wrap" on={!!style?.wrap} onClick={() => ctl.patchStyle({ wrap: !style?.wrap })} />
            <Btn label="Verbinden" icon="merge" onClick={() => ctl.toggleMerge()} />
          </Group>
          <Group label="Zahl">
            <select className="field" aria-label="Zahlenformat" value={fmt} onChange={(event) => ctl.setNumFmt(event.target.value as NumFmt)}>
              {FMTS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
            </select>
            <Btn label="Währung" icon="euro" onClick={() => ctl.setNumFmt('c2')} />
            <Btn label="Prozent" icon="percent" onClick={() => ctl.setNumFmt('p0')} />
            <Btn label="Dezimalstelle hinzufügen" onClick={() => ctl.bumpDecimals(1)} />
            <Btn label="Dezimalstelle entfernen" onClick={() => ctl.bumpDecimals(-1)} />
          </Group>
          <Group label="Format">
            <BorderMenu onPick={(border) => ctl.patchStyle({ border })} />
            <Btn label="Bedingte Formatierung" onClick={() => ctl.openDialog('cond')} />
          </Group>
          <Group label="Zellen">
            <Btn label="Zeile einfügen" onClick={() => ctl.insertRows()} />
            <Btn label="Zeile löschen" onClick={() => ctl.deleteRows()} />
            <Btn label="Spalte einfügen" onClick={() => ctl.insertCols()} />
            <Btn label="Spalte löschen" onClick={() => ctl.deleteCols()} />
          </Group>
          <Group label="Bearbeiten">
            <Btn tall label="Summe" icon="sum" onClick={() => ctl.autosum()} />
            <Btn label="Löschen" icon="clear" onClick={() => ctl.clear('values')} />
            <Btn label="Sortieren" icon="sort" onClick={() => ctl.sortBy(ctl.view.focus.c, true)} />
            <Btn label="Filtern" icon="filter" onClick={() => ctl.toggleFilter()} />
            <Btn label="Suchen" icon="find" onClick={() => ctl.openDialog('find')} />
          </Group>
        </>
      )}
      {tab === 'einfuegen' && (
        <>
          <Group label="Tabellen">
            <Btn tall label="Tabelle" onClick={() => ctl.createTable()} />
            <Btn label="Ergebniszeile" onClick={() => ctl.toggleTotals()} />
            <Btn label="Pivot" onClick={() => ctl.openDialog('pivot')} />
            <Btn label="Slicer" onClick={() => ctl.addSlicer()} />
          </Group>
          <Group label="Diagramme">
            {CHARTS.map((chart) => (
              <Btn key={chart.id} label={chart.label} onClick={() => ctl.addChart(chart.id)} />
            ))}
          </Group>
          <Group label="Zusätze">
            <Btn label="Funktion" onClick={() => ctl.openDialog('fn')} />
            <Btn label="Miniatur" onClick={() => ctl.insertFormula(`=MINIATUR(${ctl.focusAddr()};"linie")`)} />
            <Btn label="Kommentar" onClick={() => ctl.openDialog('comment')} />
            <Btn label="Link" onClick={() => ctl.openDialog('link')} />
            <Btn label="Bild" onClick={() => ctl.openDialog('image')} />
            <Btn label="Formular" onClick={() => ctl.openDialog('form')} />
          </Group>
        </>
      )}
      {tab === 'layout' && (
        <Group label="Blatt">
          <Btn label="Zeilenhöhe" onClick={() => ctl.openDialog('size', { axis: 'row' })} />
          <Btn label="Spaltenbreite" onClick={() => ctl.openDialog('size', { axis: 'col' })} />
          <Btn label="Anpassen" onClick={() => ctl.autoFit()} />
          <Btn label="Zeile +" onClick={() => ctl.insertRows()} />
          <Btn label="Zeile −" onClick={() => ctl.deleteRows()} />
          <Btn label="Spalte +" onClick={() => ctl.insertCols()} />
          <Btn label="Spalte −" onClick={() => ctl.deleteCols()} />
          <Btn label="Fixieren" onClick={() => ctl.freeze()} />
          <Btn label="Lösen" onClick={() => ctl.unfreeze()} />
          <Btn label="Gitternetz" onClick={() => ctl.toggleGrid()} />
          <Btn label="Gruppieren" onClick={() => ctl.groupRows()} />
          <Btn label="Drucken" onClick={() => window.print()} />
        </Group>
      )}
      {tab === 'formeln' && (
        <Group label="Formeln">
          <Btn tall label="Assistent" onClick={() => ctl.openDialog('assist')} />
          <Btn label="Bibliothek" onClick={() => ctl.openDialog('fn')} />
          <Btn label="Namen" onClick={() => ctl.openDialog('names')} />
          <Btn label="Summe" onClick={() => ctl.autosum()} />
          <Btn label="Vorgänger" onClick={() => ctl.tracePrecedents()} />
          <Btn label="Nachfolger" onClick={() => ctl.traceDependents()} />
          <Btn label="Spur aus" onClick={() => ctl.clearTrace()} />
          <Btn label="Auswerten" onClick={() => ctl.openDialog('evaluate')} />
          <Btn label="Berechnen" onClick={() => ctl.refresh()} />
          <Btn label={ctl.wb.calc === 'auto' ? 'Auto' : 'Manuell'} onClick={() => ctl.toggleCalc()} />
        </Group>
      )}
      {tab === 'daten' && (
        <>
          <Group label="Sortieren und Filtern">
            <Btn label="A→Z" onClick={() => ctl.sortBy(ctl.view.focus.c, true)} />
            <Btn label="Z→A" onClick={() => ctl.sortBy(ctl.view.focus.c, false)} />
            <Btn label="Dialog" onClick={() => ctl.openDialog('sort')} />
            <Btn label="Filter" onClick={() => ctl.toggleFilter()} />
            <Btn label="Spalten" onClick={() => ctl.openDialog('split')} />
            <Btn label="Duplikate" onClick={() => ctl.removeDuplicates()} />
            <Btn label="Blitz" onClick={() => ctl.flashFill()} />
            <Btn label="Gültigkeit" onClick={() => ctl.openDialog('validation')} />
          </Group>
          <Group label="Daten holen">
            <Btn label="Web / JSON" onClick={() => ctl.openDialog('url')} />
            <Btn label="Abfrage" onClick={() => ctl.openDialog('query')} />
            <Btn label="Karte" onClick={() => ctl.openDialog('map')} />
            <Btn label="Kurse" onClick={() => ctl.openDialog('quote')} />
          </Group>
          <Group label="Was-wäre-wenn">
            <Btn label="Zielwert" onClick={() => ctl.openDialog('goal')} />
            <Btn label="Szenario" onClick={() => ctl.openDialog('scenario')} />
            <Btn label="Solver" onClick={() => ctl.openDialog('solver')} />
            <Btn label="Einblicke" onClick={() => ctl.openDialog('insights')} />
            <Btn label="Bedingung" onClick={() => ctl.openDialog('cond')} />
          </Group>
        </>
      )}
      {tab === 'ueberpruefen' && (
        <Group label="Schutz">
          <Btn label="Kommentar" onClick={() => ctl.openDialog('comment')} />
          <Btn label="Schutz" onClick={() => ctl.openDialog('protect')} />
          <Btn label="Struktur" onClick={() => ctl.toggleStructure()} />
          <Btn label="Sperren" onClick={() => ctl.toggleLock()} />
          <Btn label="DLP" onClick={() => ctl.openDialog('dlp')} />
          <Btn label="Barrierefreiheit" onClick={() => ctl.openDialog('a11y')} />
          <Btn label="Versionen" onClick={() => ctl.openDialog('versions')} />
          <Btn label="Vorlesen" onClick={() => ctl.speak()} />
          <Btn label="Ansichten" onClick={() => ctl.openDialog('views')} />
        </Group>
      )}
      {tab === 'ansicht' && (
        <Group label="Ansicht">
          <Btn label="−" onClick={() => ctl.setZoom(ctl.view.zoom - 0.1)} />
          <Btn label={`${Math.round(ctl.view.zoom * 100)} %`} onClick={() => ctl.setZoom(1)} />
          <Btn label="+" onClick={() => ctl.setZoom(ctl.view.zoom + 0.1)} />
          <Btn label={ctl.view.theme === 'dark' ? 'Hell' : 'Dunkel'} onClick={() => ctl.toggleTheme()} />
          <Btn label="Formeln" onClick={() => ctl.toggleFormulas()} />
          <Btn label={ctl.view.collab ? 'Live an' : 'Live'} onClick={() => ctl.toggleCollab()} />
          <Btn label={ctl.view.recording ? 'Stopp' : 'Makro'} onClick={() => ctl.toggleRecord()} />
          <Btn label="Makros" onClick={() => ctl.openDialog('macro')} />
          <Btn label="Skript" onClick={() => ctl.openDialog('script')} />
          <Btn label="Webhook" onClick={() => ctl.openDialog('webhook')} />
          <Btn label="Info" onClick={() => ctl.openDialog('about')} />
        </Group>
      )}
    </div>
  );
}

function Group({ label, children, wide }: { label: string; children: ReactNode; wide?: boolean }) {
  return (
    <section className="group">
      <div className={`group-body${wide ? ' stack' : ''}`}>{children}</div>
      <div className="group-label">{label}</div>
    </section>
  );
}

function Btn({ label, onClick, tall, on, icon }: { label: string; onClick: () => void; tall?: boolean; on?: boolean; icon?: IconName }) {
  return (
    <button type="button" className={`${tall ? 'rb tall' : 'rb'}${on ? ' on' : ''}`} title={label} aria-label={label} aria-pressed={on} onClick={onClick}>
      {icon ? <Ico name={icon} /> : null}
      {tall || !icon ? <span>{label}</span> : null}
    </button>
  );
}

function placeMenu(event: SyntheticEvent<HTMLDetailsElement>): void {
  const menu = event.currentTarget;
  if (!menu.open) return;
  const pop = menu.querySelector('.menu-pop');
  if (!(pop instanceof HTMLElement)) return;
  const rect = menu.getBoundingClientRect();
  const width = Math.max(pop.offsetWidth, 160);
  pop.style.top = `${rect.bottom + 2}px`;
  pop.style.left = `${Math.max(8, Math.min(rect.left, window.innerWidth - width - 8))}px`;
}

function BorderMenu({ onPick }: { onPick: (border: NonNullable<Style['border']>) => void }) {
  const ref = useRef<HTMLDetailsElement>(null);
  const items: { id: NonNullable<Style['border']>; label: string }[] = [
    { id: 'all', label: 'Alle Rahmen' },
    { id: 'outer', label: 'Rahmen außen' },
    { id: 'bottom', label: 'Rahmen unten' },
    { id: 'thick', label: 'Dicker Rahmen' },
    { id: 'none', label: 'Kein Rahmen' },
  ];
  return (
    <details ref={ref} className="rb-menu border-menu" onToggle={placeMenu}>
      <summary title="Umrandung"><Ico name="border" /> Umrandung</summary>
      <div className="menu-pop">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => {
              onPick(item.id);
              if (ref.current) ref.current.open = false;
            }}
          >
            {item.label}
          </button>
        ))}
      </div>
    </details>
  );
}

type IconName = 'paste' | 'cut' | 'copy' | 'brush' | 'bold' | 'italic' | 'underline' | 'strike' | 'left' | 'center' | 'right' | 'top' | 'middle' | 'bottom' | 'wrap' | 'merge' | 'euro' | 'percent' | 'sum' | 'clear' | 'sort' | 'filter' | 'find' | 'border';

function Ico({ name }: { name: IconName }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden>
      {name === 'paste' && <path fill="currentColor" d="M5 1.5h6V3h2v11H3V3h2V1.5zm1 1v1.5h4V2.5H6zM4.5 4.5v8h7v-8h-7z" />}
      {name === 'cut' && <path fill="currentColor" d="M4.2 3.2a1.6 1.6 0 1 0 0 3.2 1.6 1.6 0 0 0 0-3.2zm0 6.4a1.6 1.6 0 1 0 0 3.2 1.6 1.6 0 0 0 0-3.2zM6.4 5.4 13 11.2l-.8.9L5.6 6.3l.8-.9zm-.8 5.3L13 4.8l-.8-.9-7.4 6.9.8.9z" />}
      {name === 'copy' && <path fill="currentColor" d="M5 2h8v9H5V2zm1 1v7h6V3H6zM3 5h1v8h7v1H3V5z" />}
      {name === 'brush' && <path fill="currentColor" d="M3 2h8l1 3-3 1v2H6V6L3 5V2zm2 8h3v4H5v-4z" />}
      {name === 'bold' && <text x="3" y="13" fontSize="13" fontWeight="700" fill="currentColor">F</text>}
      {name === 'italic' && <text x="5" y="13" fontSize="13" fontStyle="italic" fill="currentColor">K</text>}
      {name === 'underline' && <><text x="3" y="12" fontSize="12" fill="currentColor">U</text><path d="M3 14h10" stroke="currentColor" /></>}
      {name === 'strike' && <><text x="3" y="12" fontSize="12" fill="currentColor">S</text><path d="M2 8h12" stroke="currentColor" /></>}
      {name === 'left' && <path stroke="currentColor" d="M2 3h12M2 7h8M2 11h10" />}
      {name === 'center' && <path stroke="currentColor" d="M2 3h12M4 7h8M3 11h10" />}
      {name === 'right' && <path stroke="currentColor" d="M2 3h12M6 7h8M4 11h10" />}
      {name === 'top' && <path stroke="currentColor" d="M3 2h10M5 5h6M4 8h8" />}
      {name === 'middle' && <path stroke="currentColor" d="M4 4h8M3 8h10M5 12h6" />}
      {name === 'bottom' && <path stroke="currentColor" d="M4 6h8M5 9h6M3 13h10" />}
      {name === 'wrap' && <path fill="none" stroke="currentColor" d="M2 3h12M2 7h8a3 3 0 0 1 0 6H7M7 11l-2 2 2 2" />}
      {name === 'merge' && <path fill="none" stroke="currentColor" d="M2 3h12v10H2zM6 3v10M10 3v10" />}
      {name === 'euro' && <text x="2" y="13" fontSize="13" fill="currentColor">€</text>}
      {name === 'percent' && <text x="1" y="13" fontSize="13" fill="currentColor">%</text>}
      {name === 'sum' && <text x="2" y="13" fontSize="14" fill="currentColor">Σ</text>}
      {name === 'clear' && <path fill="currentColor" d="M6 2h4l1 2h3v1H2V4h3l1-2zm-2 4h8l-1 8H5L4 6z" />}
      {name === 'sort' && <path fill="currentColor" d="M3 3h6v1H3zm0 3h4v1H3zm0 3h2v1H3zm8-6 2 3H9l2-3zm0 9-2-3h4l-2 3z" />}
      {name === 'filter' && <path fill="currentColor" d="M2 2h12l-4.5 6v5l-3 1V8L2 2z" />}
      {name === 'find' && <><circle cx="7" cy="7" r="4" fill="none" stroke="currentColor" /><path stroke="currentColor" d="M10 10l3 3" /></>}
      {name === 'border' && <path fill="none" stroke="currentColor" d="M2 2h12v12H2zM2 8h12M8 2v12" />}
    </svg>
  );
}

function Palette({ title, onPick }: { title: string; onPick: (color: string) => void }) {
  const ref = useRef<HTMLDetailsElement>(null);
  return (
    <details ref={ref} className="rb-menu" onToggle={placeMenu}>
      <summary>{title}</summary>
      <div className="menu-pop swatches">
        {COLORS.map((color) => (
          <button
            key={color}
            type="button"
            className="swatch"
            style={{ background: color }}
            onClick={() => {
              onPick(color);
              if (ref.current) ref.current.open = false;
            }}
          />
        ))}
      </div>
    </details>
  );
}
