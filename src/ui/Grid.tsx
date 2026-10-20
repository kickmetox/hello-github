import { useEffect, useMemo, useRef, useState } from 'react';
import type { MouseEvent as ReactMouseEvent } from 'react';
import { colName } from '../model/addr';
import type { GridController } from '../model/controller';
import type { Sheet } from '../model/types';
import { ChartView, Spark } from './charts';
import { useGrid } from './useGrid';

const HEAD_W = 46;
const HEAD_H = 22;

export function Grid({ ctl }: { ctl: GridController }) {
  useGrid(ctl);
  const sheet = ctl.sheet();
  const zoom = ctl.view.zoom;
  const scroller = useRef<HTMLDivElement>(null);
  const editor = useRef<HTMLInputElement>(null);
  const [scroll, setScroll] = useState({ left: 0, top: 0 });
  const [view, setView] = useState({ w: 900, h: 600 });
  const [filterCol, setFilterCol] = useState<{ col: number; x: number; y: number } | null>(null);
  const layout = useMemo(() => buildLayout(sheet, ctl.hiddenRows(sheet), zoom), [ctl, sheet, zoom, ctl.getSnapshot()]);

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const watch = new ResizeObserver(() => setView({ w: el.clientWidth, h: el.clientHeight }));
    watch.observe(el);
    setView({ w: el.clientWidth, h: el.clientHeight });
    return () => watch.disconnect();
  }, []);

  useEffect(() => {
    if (!ctl.view.editing) return;
    const el = editor.current;
    const active = document.activeElement;
    if (active?.classList.contains('formula-input') || active?.classList.contains('namebox')) return;
    if (!el || active === el) return;
    el.focus();
    const n = el.value.length;
    el.setSelectionRange(n, n);
  }, [ctl.view.editing]);

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const { r, c } = ctl.view.focus;
    const top = layout.rowY[r];
    const left = layout.colX[c];
    const frozenT = layout.rowY[sheet.freezeRows] ?? 0;
    const frozenL = layout.colX[sheet.freezeCols] ?? 0;
    if (r >= sheet.freezeRows && top < el.scrollTop + frozenT) el.scrollTop = Math.max(0, top - frozenT);
    if (top + layout.rowH[r] > el.scrollTop + el.clientHeight) el.scrollTop = top + layout.rowH[r] - el.clientHeight + 4;
    if (c >= sheet.freezeCols && left < el.scrollLeft + frozenL) el.scrollLeft = Math.max(0, left - frozenL);
    if (left + layout.colW[c] > el.scrollLeft + el.clientWidth) el.scrollLeft = left + layout.colW[c] - el.clientWidth + 4;
  }, [ctl.view.focus.r, ctl.view.focus.c, layout, sheet.freezeCols, sheet.freezeRows]);

  const c0 = indexAt(layout.colX, scroll.left);
  const c1 = Math.min(sheet.cols - 1, indexAt(layout.colX, scroll.left + view.w) + 1);
  const r0 = indexAt(layout.rowY, scroll.top);
  const r1 = Math.min(sheet.rows - 1, indexAt(layout.rowY, scroll.top + view.h) + 1);
  const bounds = ctl.bounds();
  const editAt = ctl.view.editing ? ctl.view.editAt : null;

  const paintCell = (r: number, c: number) => {
    const merge = ctl.mergeAt(r, c);
    if (merge && !merge.origin) return null;
    if (!layout.rowH[r] || !layout.colW[c]) return null;
    const cell = sheet.cells[`${r},${c}`];
    const computed = ctl.comp(r, c);
    const paint = ctl.paint.get(`${r},${c}`);
    const selected = r >= bounds.r1 && r <= bounds.r2 && c >= bounds.c1 && c <= bounds.c2;
    const active = ctl.view.focus.r === r && ctl.view.focus.c === c;
    const traced = ctl.view.trace.some((pos) => pos.r === r && pos.c === c);
    const peer = ctl.view.peers.find((item) => item.sheet === sheet.name && item.r === r && item.c === c);
    const width = merge ? layout.colX[merge.c2 + 1] - layout.colX[merge.c1] : layout.colW[c];
    const height = merge ? layout.rowY[merge.r2 + 1] - layout.rowY[merge.r1] : layout.rowH[r];
    const raw = cell?.raw ?? '';
    const image = /^https?:\/\/\S+\.(png|jpe?g|gif|webp|svg)(\?\S*)?$/i.test(raw);
    const style = cell?.style;
    return (
      <div
        key={`${r}-${c}`}
        className={`cell${selected ? ' sel' : ''}${active ? ' active' : ''}${traced ? ' trace' : ''}${computed?.error ? ' err' : ''}${peer ? ' peer' : ''}`}
        style={{
          left: layout.colX[c],
          top: layout.rowY[r],
          width,
          height,
          fontWeight: style?.bold ? 700 : undefined,
          fontStyle: style?.italic ? 'italic' : undefined,
          textDecoration: [style?.underline ? 'underline' : '', style?.strike ? 'line-through' : ''].filter(Boolean).join(' ') || undefined,
          fontFamily: style?.font,
          fontSize: style?.size ? style.size * zoom : undefined,
          color: style?.color ?? paint?.color,
          background: style?.fill ?? paint?.fill,
          justifyContent: style?.align === 'center' ? 'center' : style?.align === 'right' ? 'flex-end' : undefined,
          alignItems: style?.valign === 'top' ? 'flex-start' : style?.valign === 'bottom' ? 'flex-end' : 'center',
          whiteSpace: style?.wrap ? 'normal' : 'nowrap',
          lineHeight: style?.wrap ? '1.2' : undefined,
          boxShadow: borderShadow(sheet, r, c),
          outline: peer ? `2px solid ${peer.color}` : undefined,
        }}
        title={cell?.comment}
        onMouseDown={(event) => onCellDown(event, r, c)}
        onDoubleClick={() => ctl.beginEdit()}
        onContextMenu={(event) => {
          event.preventDefault();
          ctl.select(r, c, event.shiftKey);
          ctl.openMenu(event.clientX, event.clientY);
        }}
      >
        {image ? <img src={raw} alt="" style={{ maxHeight: height - 2, maxWidth: width - 4 }} /> : null}
        {!image && computed?.spark ? <Spark values={computed.spark.values} mode={computed.spark.mode} /> : null}
        {!image && !computed?.spark && computed?.href ? (
          <a href={computed.href} target="_blank" rel="noreferrer" onMouseDown={(event) => event.stopPropagation()}>
            {computed.label || computed.href}
          </a>
        ) : null}
        {!image && !computed?.spark && !computed?.href ? ctl.display(r, c) : null}
        {paint?.bar !== undefined ? <i className="bar" style={{ width: `${Math.max(0, Math.min(1, paint.bar)) * 100}%`, background: paint.fill }} /> : null}
        {cell?.comment ? <i className="note" /> : null}
        {sheet.filter && r === sheet.filter.r1 && c >= sheet.filter.c1 && c <= sheet.filter.c2 ? (
          <button
            type="button"
            className="filter-btn"
            style={{ right: 1, top: 1 }}
            onMouseDown={(event) => {
              event.stopPropagation();
              const rect = (event.target as HTMLElement).getBoundingClientRect();
              setFilterCol({ col: c, x: rect.left, y: rect.bottom });
            }}
          >
            ▾
          </button>
        ) : null}
      </div>
    );
  };

  const cells = [];
  for (let r = r0; r <= r1; r++) for (let c = c0; c <= c1; c++) {
    const node = paintCell(r, c);
    if (node) cells.push(node);
  }

  const onCellDown = (event: ReactMouseEvent, r: number, c: number) => {
    if (event.button !== 0) return;
    if (ctl.view.painter) {
      ctl.select(r, c, false);
      return;
    }
    ctl.select(r, c, event.shiftKey);
    if (event.shiftKey) return;
    const move = (ev: PointerEvent) => {
      const hit = hitCell(ev.clientX, ev.clientY);
      if (hit) ctl.select(hit.r, hit.c, true);
    };
    const up = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  };

  const hitCell = (clientX: number, clientY: number) => {
    const el = scroller.current;
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    const x = clientX - rect.left + el.scrollLeft;
    const y = clientY - rect.top + el.scrollTop;
    if (x < 0 || y < 0) return null;
    return { c: indexAt(layout.colX, x), r: indexAt(layout.rowY, y) };
  };

  const editorStyle = editAt
    ? {
        left: HEAD_W + layout.colX[editAt.c] - (editAt.c < sheet.freezeCols ? 0 : scroll.left),
        top: HEAD_H + layout.rowY[editAt.r] - (editAt.r < sheet.freezeRows ? 0 : scroll.top),
        width: layout.colW[editAt.c],
        height: layout.rowH[editAt.r],
      }
    : undefined;

  const fillX = HEAD_W + layout.colX[bounds.c2] + layout.colW[bounds.c2] - 4 - scroll.left;
  const fillY = HEAD_H + layout.rowY[bounds.r2] + layout.rowH[bounds.r2] - 4 - scroll.top;

  return (
    <div className={`gridroot${sheet.showGrid ? ' lines' : ''}`}>
      <div className="corner" onMouseDown={() => ctl.selectAll()} />
      <div className="colhead">
        <div style={{ width: layout.width, height: HEAD_H, transform: `translateX(${-scroll.left}px)`, position: 'relative' }}>
          {range(c0, c1).map((c) => (
            <div
              key={c}
              className={`col-item${c >= bounds.c1 && c <= bounds.c2 ? ' on' : ''}`}
              style={{ left: layout.colX[c], width: layout.colW[c], height: HEAD_H }}
              onMouseDown={(event) => ctl.selectArea(event.shiftKey ? ctl.view.anchor.r : 0, event.shiftKey ? ctl.view.anchor.c : c, sheet.rows - 1, c)}
            >
              {colName(c)}
              <i
                className="resize"
                onMouseDown={(event) => {
                  event.stopPropagation();
                  const start = event.clientX;
                  const width = sheet.colWidths[c] ?? 96;
                  ctl.pushHistory();
                  const move = (ev: PointerEvent) => ctl.resizeCol(c, width + (ev.clientX - start) / zoom);
                  const up = () => {
                    window.removeEventListener('pointermove', move);
                    window.removeEventListener('pointerup', up);
                  };
                  window.addEventListener('pointermove', move);
                  window.addEventListener('pointerup', up);
                }}
              />
            </div>
          ))}
        </div>
      </div>
      <div className="rowhead">
        <div style={{ height: layout.height, transform: `translateY(${-scroll.top}px)`, position: 'relative' }}>
          {range(r0, r1).map((r) =>
            layout.rowH[r] ? (
              <div
                key={r}
                className={`row-item${r >= bounds.r1 && r <= bounds.r2 ? ' on' : ''}`}
                style={{ top: layout.rowY[r], height: layout.rowH[r], width: HEAD_W }}
                onMouseDown={(event) => ctl.selectArea(event.shiftKey ? ctl.view.anchor.r : r, 0, r, sheet.cols - 1)}
              >
                {r + 1}
                {sheet.groups.map((group, index) =>
                  group.start === r ? (
                    <button key={group.start} type="button" className="filter-btn" style={{ left: 1, top: 2 }} onMouseDown={(event) => { event.stopPropagation(); ctl.toggleGroup(index); }}>
                      {group.collapsed ? '+' : '−'}
                    </button>
                  ) : null,
                )}
              </div>
            ) : null,
          )}
        </div>
      </div>
      <div
        className="scroller"
        ref={scroller}
        onScroll={(event) => setScroll({ left: event.currentTarget.scrollLeft, top: event.currentTarget.scrollTop })}
      >
        <div className="canvas" style={{ width: layout.width, height: layout.height }}>
          {cells}
          {sheet.charts.map((chart) => (
            <ChartView key={chart.id} ctl={ctl} chart={chart} />
          ))}
          {sheet.slicers.map((slicer) => (
            <SlicerBox key={slicer.id} ctl={ctl} slicerId={slicer.id} />
          ))}
        </div>
      </div>
      {sheet.freezeRows > 0 ? (
        <div className="freeze" style={{ left: HEAD_W, top: HEAD_H, right: 0, height: layout.rowY[sheet.freezeRows] }}>
          <div style={{ position: 'relative', width: layout.width, height: layout.rowY[sheet.freezeRows], transform: `translateX(${-scroll.left}px)` }}>
            {range(0, sheet.freezeRows - 1).flatMap((r) => range(0, sheet.cols - 1).map((c) => paintCell(r, c)))}
          </div>
        </div>
      ) : null}
      {sheet.freezeCols > 0 ? (
        <div className="freeze" style={{ left: HEAD_W, top: HEAD_H + layout.rowY[sheet.freezeRows], bottom: 0, width: layout.colX[sheet.freezeCols] }}>
          <div style={{ position: 'relative', height: layout.height, transform: `translateY(${-scroll.top}px)` }}>
            {range(0, sheet.rows - 1).flatMap((r) => range(0, sheet.freezeCols - 1).map((c) => paintCell(r, c)))}
          </div>
        </div>
      ) : null}
      {editAt && editorStyle ? (
        <input
          ref={editor}
          className="cell-editor"
          style={editorStyle}
          value={ctl.view.editValue}
          onChange={(event) => ctl.setEditValue(event.target.value)}
          onKeyDown={(event) => onEditorKey(event, ctl)}
          onBlur={() => {
            if (ctl.view.editing) ctl.commitEdit();
          }}
        />
      ) : null}
      {!editAt ? (
        <button
          type="button"
          className="fill-handle"
          style={{ left: fillX, top: fillY }}
          aria-label="Ausfüllkästchen"
          onMouseDown={(event) => {
            event.preventDefault();
            event.stopPropagation();
            const move = (ev: PointerEvent) => {
              const hit = hitCell(ev.clientX, ev.clientY);
              if (hit) ctl.view.focus = { r: Math.max(bounds.r1, hit.r), c: Math.max(bounds.c1, hit.c) };
            };
            const up = (ev: PointerEvent) => {
              const hit = hitCell(ev.clientX, ev.clientY);
              window.removeEventListener('pointermove', move);
              window.removeEventListener('pointerup', up);
              if (hit) ctl.fillTo(hit.r, hit.c);
            };
            window.addEventListener('pointermove', move);
            window.addEventListener('pointerup', up);
          }}
        />
      ) : null}
      {ctl.view.menu ? <ContextMenu ctl={ctl} /> : null}
      {filterCol ? <FilterPop ctl={ctl} col={filterCol.col} x={filterCol.x} y={filterCol.y} onClose={() => setFilterCol(null)} /> : null}
    </div>
  );
}

function SlicerBox({ ctl, slicerId }: { ctl: GridController; slicerId: string }) {
  const slicer = ctl.sheet().slicers.find((item) => item.id === slicerId);
  if (!slicer) return null;
  const values = ctl.uniqueValues(slicer.col);
  const selected = ctl.sheet().filter?.selected[slicer.col] ?? null;
  return (
    <aside className="slicer" style={{ left: slicer.x, top: slicer.y }}>
      <header>
        <span>{slicer.title}</span>
      </header>
      <button type="button" className={selected === null ? 'on' : ''} onClick={() => ctl.setFilter(slicer.col, null)}>
        Alle
      </button>
      {values.map((value) => {
        const on = selected === null || selected.includes(value);
        return (
          <button
            type="button"
            key={value}
            className={on ? 'on' : ''}
            onClick={() => {
              const base = selected ?? values;
              const next = base.includes(value) ? base.filter((item) => item !== value) : [...base, value];
              ctl.setFilter(slicer.col, next.length === values.length ? null : next);
            }}
          >
            {value}
          </button>
        );
      })}
    </aside>
  );
}

function FilterPop({ ctl, col, x, y, onClose }: { ctl: GridController; col: number; x: number; y: number; onClose: () => void }) {
  const values = ctl.uniqueValues(col);
  const selected = ctl.sheet().filter?.selected[col] ?? null;
  const [picked, setPicked] = useState<string[]>(selected ?? values);
  return (
    <div className="filter-pop" style={{ left: x, top: y }}>
      <label>
        <input type="checkbox" checked={picked.length === values.length} onChange={(event) => setPicked(event.target.checked ? values : [])} />
        Alle
      </label>
      {values.map((value) => (
        <label key={value}>
          <input
            type="checkbox"
            checked={picked.includes(value)}
            onChange={(event) => setPicked(event.target.checked ? [...picked, value] : picked.filter((item) => item !== value))}
          />
          {value}
        </label>
      ))}
      <div className="row">
        <button type="button" className="rb on" onClick={() => { ctl.setFilter(col, picked.length === values.length ? null : picked); onClose(); }}>
          OK
        </button>
        <button type="button" className="rb" onClick={onClose}>Abbrechen</button>
      </div>
    </div>
  );
}

function ContextMenu({ ctl }: { ctl: GridController }) {
  const menu = ctl.view.menu;
  if (!menu) return null;
  const item = (label: string, run: () => void) => (
    <button
      type="button"
      onClick={() => {
        ctl.closeMenu();
        run();
      }}
    >
      {label}
    </button>
  );
  return (
    <div className="ctx" style={{ left: menu.x, top: menu.y }}>
      {item('Ausschneiden', () => ctl.copy(true))}
      {item('Kopieren', () => ctl.copy(false))}
      {item('Einfügen', () => ctl.paste())}
      {item('Zeile einfügen', () => ctl.insertRows())}
      {item('Zeile löschen', () => ctl.deleteRows())}
      {item('Zeilenumbruch', () => {
        const on = !!ctl.sheet().cells[`${ctl.view.focus.r},${ctl.view.focus.c}`]?.style?.wrap;
        ctl.patchStyle({ wrap: !on });
      })}
      {item('Rahmen außen', () => ctl.patchStyle({ border: 'outer' }))}
      {item('Kommentar', () => ctl.openDialog('comment'))}
      {item('Hyperlink', () => ctl.openDialog('link'))}
      {item('Filter', () => ctl.toggleFilter())}
    </div>
  );
}

function onEditorKey(event: React.KeyboardEvent, ctl: GridController): void {
  if (event.key === 'Enter') {
    event.preventDefault();
    ctl.commitEdit({ dr: event.shiftKey ? -1 : 1, dc: 0 });
  } else if (event.key === 'Tab') {
    event.preventDefault();
    ctl.commitEdit({ dr: 0, dc: event.shiftKey ? -1 : 1 });
  } else if (event.key === 'Escape') {
    event.preventDefault();
    ctl.cancelEdit();
  } else if (event.key === 'F4') {
    event.preventDefault();
    ctl.cycleAbs();
  } else if (event.key === 'ArrowUp') {
    event.preventDefault();
    ctl.nudgePoint(-1, 0);
  } else if (event.key === 'ArrowDown') {
    event.preventDefault();
    ctl.nudgePoint(1, 0);
  } else if (event.key === 'ArrowLeft') {
    event.preventDefault();
    ctl.nudgePoint(0, -1);
  } else if (event.key === 'ArrowRight') {
    event.preventDefault();
    ctl.nudgePoint(0, 1);
  }
}

function borderShadow(sheet: Sheet, r: number, c: number): string | undefined {
  const border = sheet.cells[`${r},${c}`]?.style?.border;
  if (!border || border === 'none') return undefined;
  const color = '#c5d0dc';
  if (border === 'bottom') return `inset 0 -2px 0 ${color}`;
  if (border === 'thick') return `inset 0 0 0 2px ${color}`;
  if (border === 'all') return `inset 0 0 0 1px ${color}`;
  const same = (rr: number, cc: number) => sheet.cells[`${rr},${cc}`]?.style?.border === 'outer';
  const parts: string[] = [];
  if (!same(r - 1, c)) parts.push(`inset 0 1px 0 ${color}`);
  if (!same(r + 1, c)) parts.push(`inset 0 -1px 0 ${color}`);
  if (!same(r, c - 1)) parts.push(`inset 1px 0 0 ${color}`);
  if (!same(r, c + 1)) parts.push(`inset -1px 0 0 ${color}`);
  return parts.join(', ');
}

function buildLayout(sheet: Sheet, hidden: Set<number>, zoom: number) {
  const colW: number[] = [];
  const rowH: number[] = [];
  const colX = [0];
  const rowY = [0];
  for (let c = 0; c < sheet.cols; c++) {
    colW.push(Math.round((sheet.colWidths[c] ?? 96) * zoom));
    colX.push(colX[c] + colW[c]);
  }
  for (let r = 0; r < sheet.rows; r++) {
    const base = sheet.rowHeights[r] === 0 || hidden.has(r) ? 0 : (sheet.rowHeights[r] ?? 22);
    rowH.push(base ? Math.round(base * zoom) : 0);
    rowY.push(rowY[r] + rowH[r]);
  }
  return { colW, rowH, colX, rowY, width: colX[colX.length - 1], height: rowY[rowY.length - 1] };
}

function indexAt(prefix: number[], pos: number): number {
  let lo = 0;
  let hi = Math.max(0, prefix.length - 2);
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (prefix[mid] <= pos) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

function range(a: number, b: number): number[] {
  const out: number[] = [];
  for (let i = a; i <= b; i++) out.push(i);
  return out;
}
