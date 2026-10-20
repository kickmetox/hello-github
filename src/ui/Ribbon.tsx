import { useState, type ReactNode } from 'react';
import type { NumFmt } from '../formula/format';
import { saveCsv, saveRggrid, workbookToOds, workbookToXls, workbookToXlsx } from '../io/files';
import type { GridController, RibbonTab } from '../model/controller';
import type { ChartType } from '../model/types';
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
            <Btn tall label="Einfügen" onClick={() => ctl.paste()} />
            <Btn label="Ausschneiden" onClick={() => ctl.copy(true)} />
            <Btn label="Kopieren" onClick={() => ctl.copy(false)} />
            <Btn label="Format" onClick={() => ctl.pickPainter()} />
          </Group>
          <Group label="Schriftart">
            <select className="field" defaultValue="Segoe UI" onChange={(event) => ctl.patchStyle({ font: event.target.value })}>
              {FONTS.map((font) => <option key={font}>{font}</option>)}
            </select>
            <select className="field" defaultValue="12" onChange={(event) => ctl.patchStyle({ size: Number(event.target.value) })}>
              {[8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28].map((size) => <option key={size}>{size}</option>)}
            </select>
            <Btn label="F" onClick={() => ctl.toggleStyle('bold')} />
            <Btn label="K" onClick={() => ctl.toggleStyle('italic')} />
            <Btn label="U" onClick={() => ctl.toggleStyle('underline')} />
            <Btn label="S" onClick={() => ctl.toggleStyle('strike')} />
            <Palette title="Schriftfarbe" onPick={(color) => ctl.patchStyle({ color })} />
            <Palette title="Füllfarbe" onPick={(fill) => ctl.patchStyle({ fill })} />
          </Group>
          <Group label="Ausrichtung">
            <Btn label="Links" onClick={() => ctl.patchStyle({ align: 'left' })} />
            <Btn label="Mitte" onClick={() => ctl.patchStyle({ align: 'center' })} />
            <Btn label="Rechts" onClick={() => ctl.patchStyle({ align: 'right' })} />
            <Btn label="Verbinden" onClick={() => ctl.toggleMerge()} />
          </Group>
          <Group label="Zahl">
            <select className="field" defaultValue="g" onChange={(event) => ctl.setNumFmt(event.target.value as NumFmt)}>
              {FMTS.map((fmt) => <option key={fmt.id} value={fmt.id}>{fmt.label}</option>)}
            </select>
            <Btn label="%" onClick={() => ctl.setNumFmt('p0')} />
            <Btn label=".0" onClick={() => ctl.bumpDecimals(1)} />
            <Btn label=".00" onClick={() => ctl.bumpDecimals(-1)} />
          </Group>
          <Group label="Bearbeiten">
            <Btn label="Summe" onClick={() => ctl.autosum()} />
            <Btn label="Löschen" onClick={() => ctl.clear('values')} />
            <Btn label="Sortieren" onClick={() => ctl.sortBy(ctl.view.focus.c, true)} />
            <Btn label="Filtern" onClick={() => ctl.toggleFilter()} />
            <Btn label="Suchen" onClick={() => ctl.openDialog('find')} />
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

function Group({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="group">
      <div className="group-body">{children}</div>
      <div className="group-label">{label}</div>
    </section>
  );
}

function Btn({ label, onClick, tall }: { label: string; onClick: () => void; tall?: boolean }) {
  return (
    <button type="button" className={tall ? 'rb tall' : 'rb'} onClick={onClick}>
      {label}
    </button>
  );
}

function Palette({ title, onPick }: { title: string; onPick: (color: string) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <details className="rb-menu" open={open} onToggle={(event) => setOpen((event.target as HTMLDetailsElement).open)}>
      <summary>{title}</summary>
      <div className="menu-pop swatches">
        {COLORS.map((color) => (
          <button key={color} type="button" className="swatch" style={{ background: color }} onClick={() => { onPick(color); setOpen(false); }} />
        ))}
      </div>
    </details>
  );
}
