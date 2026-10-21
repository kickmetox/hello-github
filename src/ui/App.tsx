import { useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import { FUNCTION_LIST } from '../formula/functions';
import { isSealed } from '../io/crypto';
import { parseWorkbookFile } from '../io/files';
import { colName } from '../model/addr';
import { GridController, loadStoredWorkbook } from '../model/controller';
import { AUTHOR } from '../model/types';
import { umsatzTemplate } from '../model/templates';
import { Dialogs } from './Dialogs';
import { Grid } from './Grid';
import { Ribbon, TabBar } from './Ribbon';
import { useGrid } from './useGrid';
import './styles.css';

export function App() {
  const ctl = useMemo(() => new GridController(loadStoredWorkbook() ?? umsatzTemplate()), []);
  return <Shell ctl={ctl} />;
}

function Shell({ ctl }: { ctl: GridController }) {
  useGrid(ctl);
  const file = useRef<HTMLInputElement>(null);
  const [title, setTitle] = useState(ctl.wb.title);
  const [addr, setAddr] = useState(ctl.focusAddr());
  const focusAddr = ctl.focusAddr();
  useEffect(() => setAddr(focusAddr), [focusAddr]);
  useEffect(() => setTitle(ctl.wb.title), [ctl.wb.title]);
  useEffect(() => {
    document.title = `${ctl.wb.title} – ReckonGrid`;
  }, [ctl.wb.title]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const tagged = event as KeyboardEvent & { __rg?: boolean };
      if (tagged.__rg) return;
      tagged.__rg = true;
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName;
      const field = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';
      const gridField = !!target?.classList.contains('cell-editor') || !!target?.classList.contains('formula-input') || !!target?.classList.contains('namebox');
      if (event.key === 'Escape' && ctl.view.dialog) {
        ctl.closeDialog();
        return;
      }
      if (event.key === 'Escape' && ctl.view.menu) ctl.closeMenu();
      if (field && !gridField) return;
      if (gridField) return;
      const ctrl = event.ctrlKey || event.metaKey;
      if (ctl.view.editing) {
        if (event.key === 'Enter') ctl.commitEdit({ dr: event.shiftKey ? -1 : 1, dc: 0 });
        else if (event.key === 'Escape') ctl.cancelEdit();
        else if (event.key === 'Tab') ctl.commitEdit({ dr: 0, dc: event.shiftKey ? -1 : 1 });
        else if (event.key.length === 1 && !ctrl && !event.altKey) {
          event.preventDefault();
          ctl.setEditValue(ctl.view.editValue + event.key);
        }
        return;
      }
      if (ctrl && event.key.toLowerCase() === 'z') {
        event.preventDefault();
        if (event.shiftKey) ctl.redo();
        else ctl.undo();
      } else if (ctrl && event.key.toLowerCase() === 'y') {
        event.preventDefault();
        ctl.redo();
      } else if (ctrl && event.key.toLowerCase() === 'b') {
        event.preventDefault();
        ctl.toggleStyle('bold');
      } else if (ctrl && event.key.toLowerCase() === 'i') {
        event.preventDefault();
        ctl.toggleStyle('italic');
      } else if (ctrl && event.key.toLowerCase() === 'u') {
        event.preventDefault();
        ctl.toggleStyle('underline');
      } else if (ctrl && event.key.toLowerCase() === 'c') {
        event.preventDefault();
        const text = ctl.copy(false);
        navigator.clipboard?.writeText(text).catch(() => undefined);
      } else if (ctrl && event.key.toLowerCase() === 'x') {
        event.preventDefault();
        const text = ctl.copy(true);
        navigator.clipboard?.writeText(text).catch(() => undefined);
      } else if (ctrl && event.key.toLowerCase() === 'a') {
        event.preventDefault();
        ctl.selectAll();
      } else if (ctrl && event.key.toLowerCase() === 'f') {
        event.preventDefault();
        ctl.openDialog('find');
      } else if (ctrl && event.key.toLowerCase() === 's') {
        event.preventDefault();
        ctl.note('Im Browser gespeichert');
      } else if (event.key === 'Delete' || event.key === 'Backspace') {
        ctl.clear('values');
      } else if (event.key === 'F2') {
        ctl.beginEdit();
      } else if (event.key === 'Enter') {
        ctl.move(event.shiftKey ? -1 : 1, 0, false);
      } else if (event.key === 'Tab') {
        event.preventDefault();
        ctl.move(0, event.shiftKey ? -1 : 1, false);
      } else if (event.key === 'ArrowUp') ctl.move(-1, 0, event.shiftKey);
      else if (event.key === 'ArrowDown') ctl.move(1, 0, event.shiftKey);
      else if (event.key === 'ArrowLeft') ctl.move(0, -1, event.shiftKey);
      else if (event.key === 'ArrowRight') ctl.move(0, 1, event.shiftKey);
      else if (event.key === 'Home') ctl.select(event.ctrlKey ? 0 : ctl.view.focus.r, 0, false);
      else if (event.key.length === 1 && !ctrl && !event.altKey) {
        event.preventDefault();
        ctl.beginEdit(event.key);
      }
    };
    const onPaste = (event: ClipboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (ctl.view.editing) return;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') && !target.classList.contains('formula-input')) return;
      ctl.paste(event.clipboardData?.getData('text/plain'));
      event.preventDefault();
    };
    window.addEventListener('keydown', onKey);
    window.addEventListener('paste', onPaste);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('paste', onPaste);
    };
  }, [ctl]);

  const raw = ctl.sheet().cells[`${ctl.view.focus.r},${ctl.view.focus.c}`]?.raw ?? '';
  const formulaValue = ctl.view.editing ? ctl.view.editValue : raw;
  const token = /([A-ZÄÖÜa-zäöü][A-ZÄÖÜa-zäöü0-9.]{0,24})$/.exec(formulaValue)?.[1] ?? '';
  const suggestions = ctl.view.editing && formulaValue.startsWith('=') && token.length > 0
    ? FUNCTION_LIST.filter((fn) => fn.de.toUpperCase().startsWith(token.toUpperCase()) || fn.en.toUpperCase().startsWith(token.toUpperCase())).slice(0, 8)
    : [];
  const stats = ctl.stats();
  const used = ctl.usedBounds();

  return (
    <div className={`app ${ctl.view.theme}`}>
      <header className="titlebar">
        <img src={`${import.meta.env.BASE_URL}icon.png`} alt="ReckonGrid" />
        <span className="brand">ReckonGrid</span>
        <input
          className="doc"
          aria-label="Dateiname"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          onBlur={() => { ctl.wb.title = title || 'Unbenannt 1'; ctl.note(ctl.wb.title); }}
        />
        <span className="meta">{AUTHOR.name} · {AUTHOR.email}{ctl.view.recording ? <b className="recording"> · Aufnahme</b> : null}</span>
      </header>
      <TabBar ctl={ctl} />
      <Ribbon ctl={ctl} onOpen={() => file.current?.click()} />
      <div className="formula-bar">
        <input
          className="namebox"
          aria-label="Namensfeld"
          value={addr}
          onChange={(event) => setAddr(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              ctl.goTo(addr);
            }
          }}
        />
        <button type="button" className="fx" onClick={() => ctl.openDialog('fn')} title="Funktion einfügen">fx</button>
        <input
          className="formula-input"
          aria-label="Bearbeitungsleiste"
          value={formulaValue}
          onFocus={() => { if (!ctl.view.editing) ctl.beginEdit(); }}
          onChange={(event) => {
            if (!ctl.view.editing) ctl.beginEdit(event.target.value);
            else ctl.setEditValue(event.target.value);
          }}
          onKeyDown={(event) => onFormulaKey(event, ctl)}
        />
        {suggestions.length ? (
          <div className="suggest">
            {suggestions.map((fn) => (
              <button
                key={fn.de}
                type="button"
                onMouseDown={(event) => {
                  event.preventDefault();
                  const next = formulaValue.replace(/([A-ZÄÖÜa-zäöü][A-ZÄÖÜa-zäöü0-9.]{0,24})$/, fn.de + '(');
                  ctl.setEditValue(next);
                }}
              >
                {fn.de}<small>{fn.desc}</small>
              </button>
            ))}
          </div>
        ) : null}
      </div>
      <Grid ctl={ctl} />
      <footer className="sheetbar">
        <button type="button" className="rb" onClick={() => ctl.addSheet()} title="Blatt einfügen">+</button>
        <div className="sheet-tabs">
          {ctl.wb.sheets.map((sheet, index) => (
            <button
              key={sheet.name}
              type="button"
              className={index === ctl.wb.active ? 'on' : ''}
              style={{ borderTopColor: sheet.tabColor }}
              onClick={() => ctl.activate(index)}
              onDoubleClick={() => {
                const name = window.prompt('Blattname', sheet.name);
                if (name) ctl.renameSheet(name);
              }}
              onContextMenu={(event) => {
                event.preventDefault();
                if (window.confirm(`Blatt „${sheet.name}“ löschen?`)) ctl.deleteSheet(index);
              }}
            >
              {sheet.name}
            </button>
          ))}
        </div>
        <div className="status">
          <span title="Bereit"><b>{ctl.view.dirty ? 'MANU' : 'ENF'}</b></span>
          <span>{ctl.wb.calc === 'auto' ? 'AUTO' : 'MANUELL'}</span>
          {stats.nums ? <span>Summe {stats.sum.toLocaleString('de-DE')} · Anzahl {stats.nums}</span> : <span>{ctl.view.status}</span>}
          <span>{colName(ctl.view.focus.c)}{ctl.view.focus.r + 1}</span>
          <input aria-label="Zoom" type="range" min={50} max={200} value={Math.round(ctl.view.zoom * 100)} onChange={(event) => ctl.setZoom(Number(event.target.value) / 100)} />
          <span>{Math.round(ctl.view.zoom * 100)}%</span>
        </div>
      </footer>
      <Dialogs ctl={ctl} />
      <input
        ref={file}
        type="file"
        hidden
        accept=".rggrid,.xlsx,.xls,.ods,.csv,.txt,.tsv,.json"
        onChange={(event) => {
          const picked = event.target.files?.[0];
          event.target.value = '';
          if (picked) void openFile(ctl, picked);
        }}
      />
      <section className="print-sheet">
        <h1>{ctl.wb.title}</h1>
        <table>
          <tbody>
            {Array.from({ length: used.r2 - used.r1 + 1 }, (_, ri) => (
              <tr key={ri}>
                {Array.from({ length: used.c2 - used.c1 + 1 }, (_, ci) => (
                  <td key={ci}>{ctl.display(used.r1 + ri, used.c1 + ci)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function onFormulaKey(event: ReactKeyboardEvent, ctl: GridController): void {
  if (event.key === 'Enter') {
    event.preventDefault();
    ctl.commitEdit({ dr: 1, dc: 0 });
  } else if (event.key === 'Escape') {
    event.preventDefault();
    ctl.cancelEdit();
  } else if (event.key === 'F4') {
    event.preventDefault();
    ctl.cycleAbs();
  }
}

async function openFile(ctl: GridController, file: File): Promise<void> {
  const buffer = await file.arrayBuffer();
  const lower = file.name.toLowerCase();
  const text = lower.endsWith('.rggrid') || lower.endsWith('.json') || lower.endsWith('.csv') || lower.endsWith('.txt') || lower.endsWith('.tsv')
    ? new TextDecoder().decode(buffer)
    : '';
  if (text && isSealed(text)) {
    ctl.openDialog('decrypt', { payload: text });
    return;
  }
  try {
    const book = parseWorkbookFile(file.name, text || buffer);
    if (book === 'sealed') ctl.openDialog('decrypt', { payload: text });
    else ctl.loadWorkbook(book);
  } catch (error) {
    ctl.note(error instanceof Error ? error.message : 'Datei nicht lesbar');
  }
}
