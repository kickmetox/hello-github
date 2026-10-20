import { useMemo, useState } from 'react';
import { FUNCTION_LIST } from '../formula/functions';
import { explainFormula, generateFormula, repairFormula } from './assistant';
import { isSealed, openSealed, sealJson } from '../io/crypto';
import { saveRggrid } from '../io/files';
import type { GridController } from '../model/controller';
import { AUTHOR } from '../model/types';
import { TEMPLATES } from '../model/templates';
import { useGrid } from './useGrid';

const QUOTES = [
  { ticker: 'SAP', name: 'SAP SE', price: 198.42, cur: 'EUR' },
  { ticker: 'ALV', name: 'Allianz', price: 292.15, cur: 'EUR' },
  { ticker: 'BMW', name: 'BMW', price: 84.2, cur: 'EUR' },
  { ticker: 'AAPL', name: 'Apple', price: 228.5, cur: 'USD' },
  { ticker: 'MSFT', name: 'Microsoft', price: 418.2, cur: 'USD' },
];

export function Dialogs({ ctl }: { ctl: GridController }) {
  useGrid(ctl);
  const dialog = ctl.view.dialog;
  if (!dialog) return null;
  return (
    <div className="modal-back" onMouseDown={() => ctl.closeDialog()}>
      <div className={`modal${dialog.type === 'fn' || dialog.type === 'templates' ? ' wide' : ''}`} onMouseDown={(event) => event.stopPropagation()}>
        <header>
          <strong>{titleOf(dialog.type)}</strong>
          <button type="button" onClick={() => ctl.closeDialog()} aria-label="Schließen">×</button>
        </header>
        <div className="body">
          <DialogBody ctl={ctl} type={dialog.type} extra={dialog} />
        </div>
      </div>
    </div>
  );
}

function DialogBody({ ctl, type, extra }: { ctl: GridController; type: string; extra: { type: string; [key: string]: unknown } }) {
  if (type === 'templates') return <Templates ctl={ctl} />;
  if (type === 'fn') return <Functions ctl={ctl} />;
  if (type === 'assist') return <Assist ctl={ctl} />;
  if (type === 'find') return <Find ctl={ctl} />;
  if (type === 'comment') return <Comment ctl={ctl} />;
  if (type === 'link') return <Link ctl={ctl} />;
  if (type === 'image') return <ImageUrl ctl={ctl} />;
  if (type === 'form') return <Form ctl={ctl} />;
  if (type === 'size') return <Size ctl={ctl} axis={extra.axis === 'col' ? 'col' : 'row'} />;
  if (type === 'names') return <Names ctl={ctl} />;
  if (type === 'evaluate') return <p className="pre">{ctl.evaluateText()}</p>;
  if (type === 'sort') return <Sort ctl={ctl} />;
  if (type === 'split') return <Split ctl={ctl} />;
  if (type === 'validation') return <Valid ctl={ctl} />;
  if (type === 'url') return <UrlImport ctl={ctl} />;
  if (type === 'query') return <Query ctl={ctl} />;
  if (type === 'map') return <MapView ctl={ctl} />;
  if (type === 'quote') return <Quotes ctl={ctl} />;
  if (type === 'goal') return <Goal ctl={ctl} />;
  if (type === 'scenario') return <Scenarios ctl={ctl} />;
  if (type === 'solver') return <Solver ctl={ctl} />;
  if (type === 'insights') return <List items={ctl.insights()} />;
  if (type === 'cond') return <Cond ctl={ctl} />;
  if (type === 'protect') return <Protect ctl={ctl} />;
  if (type === 'dlp') return <Dlp ctl={ctl} />;
  if (type === 'a11y') return <List items={ctl.a11y()} />;
  if (type === 'versions') return <Versions ctl={ctl} />;
  if (type === 'views') return <Views ctl={ctl} />;
  if (type === 'pivot') return <Pivot ctl={ctl} />;
  if (type === 'macro') return <Macros ctl={ctl} />;
  if (type === 'script') return <Script ctl={ctl} />;
  if (type === 'webhook') return <Webhook ctl={ctl} />;
  if (type === 'seal') return <Seal ctl={ctl} />;
  if (type === 'decrypt') return <Decrypt ctl={ctl} payload={String(extra.payload ?? '')} />;
  if (type === 'about') return <About />;
  return null;
}

function Templates({ ctl }: { ctl: GridController }) {
  return (
    <div className="cards">
      {TEMPLATES.map((template) => (
        <button key={template.id} type="button" className="card" onClick={() => ctl.newFromTemplate(template.id)}>
          <b>{template.name}</b>
          <span>{template.hint}</span>
        </button>
      ))}
    </div>
  );
}

function Functions({ ctl }: { ctl: GridController }) {
  const [q, setQ] = useState('');
  const list = useMemo(() => {
    const needle = q.toLocaleLowerCase('de-DE');
    return FUNCTION_LIST.filter((fn) => !needle || `${fn.de} ${fn.en} ${fn.desc} ${fn.category}`.toLocaleLowerCase('de-DE').includes(needle)).slice(0, 80);
  }, [q]);
  return (
    <>
      <input className="field" placeholder="Funktion suchen" value={q} onChange={(event) => setQ(event.target.value)} />
      <div className="cards">
        {list.map((fn) => (
          <button key={fn.de} type="button" className="card" onClick={() => ctl.insertFormula(`=${fn.de}(`)}>
            <b>{fn.de}</b>
            <span>{fn.category}: {fn.desc}</span>
          </button>
        ))}
      </div>
    </>
  );
}

function Assist({ ctl }: { ctl: GridController }) {
  const raw = ctl.sheet().cells[`${ctl.view.focus.r},${ctl.view.focus.c}`]?.raw ?? '';
  const [prompt, setPrompt] = useState('Summe der markierten Spalte');
  const [out, setOut] = useState(raw.startsWith('=') ? raw : '');
  const [note, setNote] = useState('Der Assistent arbeitet lokal mit Regeln, ohne Cloud-Modell.');
  return (
    <>
      <textarea className="field" rows={3} value={prompt} onChange={(event) => setPrompt(event.target.value)} />
      <div className="row">
        <button type="button" className="rb on" onClick={() => { setOut(generateFormula(prompt, ctl.focusAddr())); setNote('Formel aus der Beschreibung erzeugt.'); }}>Erzeugen</button>
        <button type="button" className="rb" onClick={() => setNote(explainFormula(out || raw))}>Erklären</button>
        <button type="button" className="rb" onClick={() => { const fixed = repairFormula(out || raw, ctl.comp(ctl.view.focus.r, ctl.view.focus.c)?.error ?? null); setOut(fixed.formula); setNote(fixed.note); }}>Reparieren</button>
        <button type="button" className="rb" onClick={() => out && ctl.insertFormula(out)}>Übernehmen</button>
      </div>
      <input className="field" value={out} onChange={(event) => setOut(event.target.value)} />
      <p className="pre">{note}</p>
    </>
  );
}

function Find({ ctl }: { ctl: GridController }) {
  const [q, setQ] = useState('');
  const [repl, setRepl] = useState('');
  const [formulas, setFormulas] = useState(false);
  return (
    <>
      <label>Suchen<input className="field" value={q} onChange={(event) => setQ(event.target.value)} /></label>
      <label>Ersetzen<input className="field" value={repl} onChange={(event) => setRepl(event.target.value)} /></label>
      <label><input type="checkbox" checked={formulas} onChange={(event) => setFormulas(event.target.checked)} /> In Formeln suchen</label>
      <div className="row">
        <button type="button" className="rb on" onClick={() => ctl.findNext(q, formulas)}>Weitersuchen</button>
        <button type="button" className="rb" onClick={() => ctl.replaceAll(q, repl)}>Alle ersetzen</button>
      </div>
    </>
  );
}

function Comment({ ctl }: { ctl: GridController }) {
  const [text, setText] = useState(ctl.sheet().cells[`${ctl.view.focus.r},${ctl.view.focus.c}`]?.comment ?? '');
  return (
    <>
      <textarea className="field" rows={4} value={text} onChange={(event) => setText(event.target.value)} placeholder="@Name für eine Erwähnung" />
      <button type="button" className="rb on" onClick={() => ctl.setComment(text)}>Speichern</button>
    </>
  );
}

function Link({ ctl }: { ctl: GridController }) {
  const [url, setUrl] = useState('https://');
  const [label, setLabel] = useState('');
  return (
    <>
      <label>URL<input className="field" value={url} onChange={(event) => setUrl(event.target.value)} /></label>
      <label>Anzeige<input className="field" value={label} onChange={(event) => setLabel(event.target.value)} /></label>
      <button type="button" className="rb on" onClick={() => ctl.insertLink(url, label)}>Einfügen</button>
    </>
  );
}

function ImageUrl({ ctl }: { ctl: GridController }) {
  const [url, setUrl] = useState('https://');
  return (
    <>
      <p>Eine Bildadresse mit Endung png, jpg, gif, webp oder svg wird in der Zelle gezeichnet.</p>
      <input className="field" value={url} onChange={(event) => setUrl(event.target.value)} />
      <button type="button" className="rb on" onClick={() => ctl.insertImage(url)}>Einfügen</button>
    </>
  );
}

function Form({ ctl }: { ctl: GridController }) {
  const table = ctl.sheet().tables[0];
  const headers = table
    ? Array.from({ length: table.c2 - table.c1 + 1 }, (_, i) => ctl.sheet().cells[`${table.r1},${table.c1 + i}`]?.raw || `Feld ${i + 1}`)
    : ['Feld 1', 'Feld 2', 'Feld 3'];
  const [values, setValues] = useState(headers.map(() => ''));
  return (
    <>
      {headers.map((header, i) => (
        <label key={header}>{header}<input className="field" value={values[i]} onChange={(event) => setValues(values.map((value, idx) => idx === i ? event.target.value : value))} /></label>
      ))}
      <button type="button" className="rb on" onClick={() => ctl.appendForm(values)}>In die Tabelle schreiben</button>
    </>
  );
}

function Size({ ctl, axis }: { ctl: GridController; axis: 'row' | 'col' }) {
  const [px, setPx] = useState(axis === 'row' ? 22 : 96);
  return (
    <>
      <label>Pixel<input className="field" type="number" value={px} onChange={(event) => setPx(Number(event.target.value))} /></label>
      <button type="button" className="rb on" onClick={() => { if (axis === 'row') ctl.setRowHeight(px); else ctl.setColWidth(px); ctl.closeDialog(); }}>Setzen</button>
    </>
  );
}

function Names({ ctl }: { ctl: GridController }) {
  const [name, setName] = useState('Bereich');
  const [ref, setRef] = useState(ctl.focusAddr());
  return (
    <>
      <ul>{ctl.wb.names.map((item) => <li key={item.name}>{item.name} {item.formula ?? ''}<button type="button" onClick={() => ctl.removeName(item.name)}>Entfernen</button></li>)}</ul>
      <label>Name<input className="field" value={name} onChange={(event) => setName(event.target.value)} /></label>
      <label>Bezug oder Formel<input className="field" value={ref} onChange={(event) => setRef(event.target.value)} /></label>
      <button type="button" className="rb on" onClick={() => ctl.addName(name, ref)}>Speichern</button>
    </>
  );
}

function Sort({ ctl }: { ctl: GridController }) {
  const [col, setCol] = useState(ctl.view.focus.c);
  const [asc, setAsc] = useState(true);
  const [header, setHeader] = useState(true);
  return (
    <>
      <label>Spaltenindex ab 0<input className="field" type="number" value={col} onChange={(event) => setCol(Number(event.target.value))} /></label>
      <label><input type="checkbox" checked={asc} onChange={(event) => setAsc(event.target.checked)} /> Aufsteigend</label>
      <label><input type="checkbox" checked={header} onChange={(event) => setHeader(event.target.checked)} /> Kopfzeile</label>
      <button type="button" className="rb on" onClick={() => { ctl.sortBy(col, asc, header); ctl.closeDialog(); }}>Sortieren</button>
    </>
  );
}

function Split({ ctl }: { ctl: GridController }) {
  const [delim, setDelim] = useState(';');
  return (
    <>
      <label>Trennzeichen<input className="field" value={delim} onChange={(event) => setDelim(event.target.value)} /></label>
      <button type="button" className="rb on" onClick={() => ctl.textToColumns(delim)}>Teilen</button>
    </>
  );
}

function Valid({ ctl }: { ctl: GridController }) {
  const [kind, setKind] = useState<'list' | 'whole' | 'decimal'>('whole');
  const [list, setList] = useState('Nord,Süd,Ost,West');
  const [min, setMin] = useState('1');
  const [max, setMax] = useState('100');
  return (
    <>
      <select className="field" value={kind} onChange={(event) => setKind(event.target.value as 'list' | 'whole' | 'decimal')}>
        <option value="list">Liste</option>
        <option value="whole">Ganze Zahl</option>
        <option value="decimal">Dezimalzahl</option>
      </select>
      {kind === 'list' ? <input className="field" value={list} onChange={(event) => setList(event.target.value)} /> : null}
      {kind !== 'list' ? (
        <div className="row">
          <input className="field" value={min} onChange={(event) => setMin(event.target.value)} />
          <input className="field" value={max} onChange={(event) => setMax(event.target.value)} />
        </div>
      ) : null}
      <div className="row">
        <button type="button" className="rb on" onClick={() => ctl.setValidation(kind === 'list' ? { type: 'list', list: list.split(',').map((item) => item.trim()) } : { type: kind, min: Number(min.replace(',', '.')), max: Number(max.replace(',', '.')) })}>Setzen</button>
        <button type="button" className="rb" onClick={() => ctl.setValidation(null)}>Entfernen</button>
      </div>
    </>
  );
}

function UrlImport({ ctl }: { ctl: GridController }) {
  const [url, setUrl] = useState('https://');
  const [error, setError] = useState('');
  return (
    <>
      <p>CSV, JSON-Liste oder HTML-Tabelle werden ab der aktiven Zelle eingefügt.</p>
      <input className="field" value={url} onChange={(event) => setUrl(event.target.value)} />
      {error ? <p>{error}</p> : null}
      <button type="button" className="rb on" onClick={() => ctl.importUrl(url).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)))}>Importieren</button>
    </>
  );
}

function Query({ ctl }: { ctl: GridController }) {
  const [sql, setSql] = useState('SELECT Region, SUMME(Umsatz) FROM A4:E16 GROUP BY Region');
  return (
    <>
      <textarea className="field" rows={4} value={sql} onChange={(event) => setSql(event.target.value)} />
      <button type="button" className="rb on" onClick={() => ctl.queryAt(sql)}>Als ABFRAGE einfügen</button>
    </>
  );
}

function MapView({ ctl }: { ctl: GridController }) {
  const series = ctl.regionSeries();
  const max = Math.max(...series.map((item) => item.value), 1);
  if (!series.length) return <p>Keine Regionen Nord, Süd, Ost, West oder DACH mit einer Zahl rechts daneben gefunden.</p>;
  return (
    <div>
      {series.map((item) => (
        <div key={item.name} style={{ display: 'grid', gridTemplateColumns: '90px 1fr 80px', gap: 8, alignItems: 'center', marginBottom: 6 }}>
          <span>{item.name}</span>
          <i style={{ display: 'block', height: 16, width: `${(item.value / max) * 100}%`, background: '#2f7fe0' }} />
          <span>{item.value}</span>
        </div>
      ))}
    </div>
  );
}

function Quotes({ ctl }: { ctl: GridController }) {
  return (
    <>
      <p>Lokaler Beispielkatalog. Das sind keine Live-Börsenkurse.</p>
      {QUOTES.map((quote) => (
        <button key={quote.ticker} type="button" className="card" onClick={() => { ctl.setCell(ctl.view.focus.r, ctl.view.focus.c, quote.ticker); ctl.setComment(`${quote.name}: ${quote.price} ${quote.cur}`); }}>
          <b>{quote.ticker}</b>
          <span>{quote.name} · {quote.price} {quote.cur}</span>
        </button>
      ))}
    </>
  );
}

function Goal({ ctl }: { ctl: GridController }) {
  const [input, setInput] = useState('B4');
  const [output, setOutput] = useState('B7');
  const [target, setTarget] = useState('-1000');
  const [note, setNote] = useState('');
  return (
    <>
      <label>Veränderbare Zelle<input className="field" value={input} onChange={(event) => setInput(event.target.value)} /></label>
      <label>Formelzelle<input className="field" value={output} onChange={(event) => setOutput(event.target.value)} /></label>
      <label>Zielwert<input className="field" value={target} onChange={(event) => setTarget(event.target.value)} /></label>
      <button type="button" className="rb on" onClick={() => {
        const a = addr(input);
        const b = addr(output);
        if (!a || !b) { setNote('Adressen nicht erkannt.'); return; }
        setNote(ctl.goalSeek(a.r, a.c, b.r, b.c, Number(target.replace(',', '.'))));
      }}>Starten</button>
      {note ? <p>{note}</p> : null}
    </>
  );
}

function Scenarios({ ctl }: { ctl: GridController }) {
  const [name, setName] = useState('Best Case');
  return (
    <>
      <p>Die markierten Zellen werden als Szenario gespeichert.</p>
      <ul>{ctl.wb.scenarios.map((item) => <li key={item.name}><button type="button" onClick={() => ctl.applyScenario(item.name)}>{item.name}</button></li>)}</ul>
      <input className="field" value={name} onChange={(event) => setName(event.target.value)} />
      <button type="button" className="rb on" onClick={() => ctl.saveScenario(name)}>Markierung speichern</button>
    </>
  );
}

function Solver({ ctl }: { ctl: GridController }) {
  const [note, setNote] = useState('Markiere die veränderbaren Zahlen. Die Zelle direkt darunter muss die Zielformel sein.');
  return (
    <>
      <p>{note}</p>
      <div className="row">
        <button type="button" className="rb on" onClick={() => setNote(ctl.solve('max'))}>Maximum</button>
        <button type="button" className="rb" onClick={() => setNote(ctl.solve('min'))}>Minimum</button>
      </div>
    </>
  );
}

function Cond({ ctl }: { ctl: GridController }) {
  const [kind, setKind] = useState<'gt' | 'lt' | 'bar' | 'scale' | 'dup'>('bar');
  const [value, setValue] = useState('10000');
  return (
    <>
      <select className="field" value={kind} onChange={(event) => setKind(event.target.value as typeof kind)}>
        <option value="bar">Datenbalken</option>
        <option value="scale">Farbskala</option>
        <option value="dup">Duplikate</option>
        <option value="gt">Größer als</option>
        <option value="lt">Kleiner als</option>
      </select>
      <input className="field" value={value} onChange={(event) => setValue(event.target.value)} />
      <button type="button" className="rb on" onClick={() => { ctl.addRule({ kind, value, fill: '#3d9b4f', color: '#d1fae5' }); ctl.closeDialog(); }}>Anwenden</button>
      <button type="button" className="rb" onClick={() => ctl.clearRules()}>Regeln löschen</button>
    </>
  );
}

function Protect({ ctl }: { ctl: GridController }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const locked = ctl.sheet().protected;
  return (
    <>
      <p>{locked ? 'Das Blatt ist geschützt. Entsperrte Zellen bleiben editierbar.' : 'Gesperrte Zellen können danach nicht mehr geändert werden. Der Hash ist SHA-256.'}</p>
      <input className="field" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
      {error ? <p>{error}</p> : null}
      <button type="button" className="rb on" onClick={() => (locked ? ctl.unprotect(password) : ctl.protect(password)).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)))}>
        {locked ? 'Schutz aufheben' : 'Blatt schützen'}
      </button>
    </>
  );
}

function Dlp({ ctl }: { ctl: GridController }) {
  const found = ctl.dlp();
  if (!found.length) return <p>Keine E-Mail, IBAN oder Kartennummer nach Luhn erkannt.</p>;
  return (
    <ul>
      {found.map((item) => <li key={`${item.sheet}${item.addr}${item.kind}`}>{item.sheet}!{item.addr}: {item.kind} ({item.sample})</li>)}
    </ul>
  );
}

function Versions({ ctl }: { ctl: GridController }) {
  const [label, setLabel] = useState('Stand');
  return (
    <>
      <ul>
        {ctl.wb.versions.map((item) => (
          <li key={item.id}>
            <button type="button" onClick={() => ctl.restoreVersion(item.id)}>{new Date(item.at).toLocaleString('de-DE')} · {item.label}</button>
          </li>
        ))}
      </ul>
      <input className="field" value={label} onChange={(event) => setLabel(event.target.value)} />
      <button type="button" className="rb on" onClick={() => ctl.saveVersion(label)}>Version sichern</button>
    </>
  );
}

function Views({ ctl }: { ctl: GridController }) {
  const [name, setName] = useState('Meine Ansicht');
  const views = ctl.wb.views.filter((item) => item.sheet === ctl.sheet().name);
  return (
    <>
      <ul>{views.map((item) => <li key={item.name}><button type="button" onClick={() => ctl.applyView(item.name)}>{item.name}</button></li>)}</ul>
      <input className="field" value={name} onChange={(event) => setName(event.target.value)} />
      <button type="button" className="rb on" onClick={() => ctl.saveView(name)}>Aktuellen Filter speichern</button>
    </>
  );
}

function Pivot({ ctl }: { ctl: GridController }) {
  const [row, setRow] = useState(0);
  const [value, setValue] = useState(3);
  const [agg, setAgg] = useState<'sum' | 'count' | 'avg'>('sum');
  return (
    <>
      <p>Kopfzeile in der ersten Zeile des Filters oder des benutzten Bereichs. Ergebnis landet auf dem Blatt Pivot.</p>
      <label>Zeilenfeld<input className="field" type="number" value={row} onChange={(event) => setRow(Number(event.target.value))} /></label>
      <label>Wertefeld<input className="field" type="number" value={value} onChange={(event) => setValue(Number(event.target.value))} /></label>
      <select className="field" value={agg} onChange={(event) => setAgg(event.target.value as typeof agg)}>
        <option value="sum">Summe</option>
        <option value="count">Anzahl</option>
        <option value="avg">Mittelwert</option>
      </select>
      <button type="button" className="rb on" onClick={() => { ctl.pivot(row, value, agg); ctl.closeDialog(); }}>Erstellen</button>
    </>
  );
}

function Macros({ ctl }: { ctl: GridController }) {
  return (
    <ul>
      {ctl.wb.macros.map((macro) => (
        <li key={macro.name}>
          <button type="button" onClick={() => ctl.playMacro(macro.name)}>{macro.name}</button>
          <span> {macro.lang}</span>
        </li>
      ))}
      {!ctl.wb.macros.length ? <li>Noch kein Makro. Aufzeichnung über Ansicht → Makro.</li> : null}
    </ul>
  );
}

function Script({ ctl }: { ctl: GridController }) {
  const [lang, setLang] = useState<'js' | 'py' | 'vba'>('js');
  const [code, setCode] = useState('rg.set("A1", "ReckonGrid");\nrg.log(rg.value("A1"));');
  const [out, setOut] = useState('');
  return (
    <>
      <select className="field" value={lang} onChange={(event) => setLang(event.target.value as typeof lang)}>
        <option value="js">JavaScript</option>
        <option value="py">Python (Subset)</option>
        <option value="vba">VBA (Subset)</option>
      </select>
      <textarea className="field" rows={8} value={code} onChange={(event) => setCode(event.target.value)} />
      <div className="row">
        <button type="button" className="rb on" onClick={() => setOut(ctl.runScript(lang, code))}>Ausführen</button>
        <button type="button" className="rb" onClick={() => ctl.saveMacro({ name: `Skript${ctl.wb.macros.length + 1}`, lang, code })}>Speichern</button>
      </div>
      {out ? <p className="pre">{out}</p> : null}
    </>
  );
}

function Webhook({ ctl }: { ctl: GridController }) {
  const [url, setUrl] = useState('https://');
  const [error, setError] = useState('');
  return (
    <>
      <p>Die markierten Zellen werden als JSON per POST gesendet.</p>
      <input className="field" value={url} onChange={(event) => setUrl(event.target.value)} />
      {error ? <p>{error}</p> : null}
      <button type="button" className="rb on" onClick={() => ctl.webhook(url).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)))}>Senden</button>
    </>
  );
}

function Seal({ ctl }: { ctl: GridController }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  return (
    <>
      <p>Die Datei wird mit AES-GCM und PBKDF2 verschlüsselt. Ohne Passwort ist sie nicht lesbar.</p>
      <input className="field" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
      {error ? <p>{error}</p> : null}
      <button type="button" className="rb on" onClick={() => sealJson(JSON.stringify(ctl.wb), password).then((body) => { saveRggrid(ctl.wb, body); ctl.closeDialog(); }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : String(reason)))}>Verschlüsselt speichern</button>
    </>
  );
}

function Decrypt({ ctl, payload }: { ctl: GridController; payload: string }) {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  return (
    <>
      <input className="field" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
      {error ? <p>{error}</p> : null}
      <button type="button" className="rb on" onClick={() => {
        if (!isSealed(payload)) { setError('Keine verschlüsselte ReckonGrid-Datei.'); return; }
        openSealed(payload, password).then((json) => ctl.loadWorkbook(JSON.parse(json) as import('../model/types').Workbook)).catch(() => setError('Passwort stimmt nicht oder die Datei ist beschädigt.'));
      }}>Öffnen</button>
    </>
  );
}

function List({ items }: { items: string[] }) {
  return <ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul>;
}

function About() {
  return (
    <>
      <p><b>{AUTHOR.app}</b> {AUTHOR.version}</p>
      <p>{AUTHOR.name}<br />{AUTHOR.email}</p>
      <p>Tabellenkalkulation mit Formelkern, D-Funktionen, Pivot, Diagrammen und lokaler Automatisierung.</p>
    </>
  );
}

function titleOf(type: string): string {
  const map: Record<string, string> = {
    templates: 'Neue Arbeitsmappe',
    fn: 'Funktion einfügen',
    assist: 'Formel-Assistent',
    find: 'Suchen und Ersetzen',
    comment: 'Kommentar',
    link: 'Hyperlink',
    image: 'Bild aus URL',
    form: 'Formular',
    size: 'Größe',
    names: 'Namens-Manager',
    evaluate: 'Formelauswertung',
    sort: 'Sortieren',
    split: 'Text in Spalten',
    validation: 'Datenüberprüfung',
    url: 'Aus dem Web',
    query: 'Abfrage',
    map: 'Regionenkarte',
    quote: 'Beispielkurse',
    goal: 'Zielwertsuche',
    scenario: 'Szenario-Manager',
    solver: 'Solver',
    insights: 'Einblicke',
    cond: 'Bedingte Formatierung',
    protect: 'Blattschutz',
    dlp: 'Sensible Daten',
    a11y: 'Barrierefreiheit',
    versions: 'Versionen',
    views: 'Blattansichten',
    pivot: 'Pivot',
    macro: 'Makros',
    script: 'Skript',
    webhook: 'Webhook',
    seal: 'Verschlüsselt speichern',
    decrypt: 'Passwort',
    about: 'ReckonGrid',
  };
  return map[type] ?? 'ReckonGrid';
}

function addr(input: string): { r: number; c: number } | null {
  const match = /^\$?([A-Za-z]{1,3})\$?(\d+)$/.exec(input.trim());
  if (!match) return null;
  let n = 0;
  for (const ch of match[1].toUpperCase()) n = n * 26 + (ch.charCodeAt(0) - 64);
  return { r: Number(match[2]) - 1, c: n - 1 };
}
