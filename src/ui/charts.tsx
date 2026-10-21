import type { PointerEvent as ReactPointerEvent } from 'react';
import type { Chart } from '../model/types';
import type { GridController } from '../model/controller';
import { colName } from '../model/addr';

const COLORS = ['#2f7fe0', '#3d9b4f', '#e0a12f', '#d4544a', '#8b6ad6', '#3db8c9'];

export function ChartView({ ctl, chart }: { ctl: GridController; chart: Chart }) {
  const model = readChart(ctl, chart);
  const onPointerDown = (event: ReactPointerEvent<HTMLElement>) => {
    event.stopPropagation();
    const startX = event.clientX;
    const startY = event.clientY;
    const ox = chart.x;
    const oy = chart.y;
    const move = (ev: PointerEvent) => ctl.moveChart(chart.id, ox + ev.clientX - startX, oy + ev.clientY - startY);
    const up = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
  };
  return (
    <figure className="chart" style={{ left: chart.x, top: chart.y, width: chart.w, height: chart.h }}>
      <header onPointerDown={onPointerDown}>
        <span>{chart.title}</span>
        <button type="button" onClick={() => ctl.removeChart(chart.id)} aria-label="Diagramm entfernen">
          ×
        </button>
      </header>
      <svg viewBox="0 0 200 120" role="img" aria-label={chart.title}>
        <ChartShape type={chart.type} cats={model.cats} series={model.series} />
      </svg>
    </figure>
  );
}

export function Spark({ values, mode }: { values: number[]; mode: 'line' | 'col' | 'winloss' }) {
  if (!values.length) return null;
  const w = 72;
  const h = 16;
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const span = max - min || 1;
  if (mode === 'line') {
    const d = values
      .map((v, i) => {
        const x = (i / Math.max(1, values.length - 1)) * (w - 2) + 1;
        const y = h - 2 - ((v - min) / span) * (h - 4);
        return `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
    return (
      <svg className="spark" width={w} height={h} aria-hidden>
        <path d={d} fill="none" stroke="#7dcea0" strokeWidth="1.4" />
      </svg>
    );
  }
  const bw = w / values.length;
  return (
    <svg className="spark" width={w} height={h} aria-hidden>
      {values.map((v, i) => {
        const zero = h - 2 - ((0 - min) / span) * (h - 4);
        const y = h - 2 - ((v - min) / span) * (h - 4);
        const top = Math.min(zero, y);
        const height = Math.max(1, Math.abs(y - zero));
        const win = mode === 'winloss' ? (v > 0 ? '#3d9b4f' : v < 0 ? '#d4544a' : '#888') : COLORS[0];
        return <rect key={i} x={i * bw + 0.5} y={top} width={Math.max(1, bw - 1)} height={height} fill={win} />;
      })}
    </svg>
  );
}

function ChartShape({ type, cats, series }: { type: Chart['type']; cats: string[]; series: { name: string; data: number[] }[] }) {
  const first = series[0]?.data ?? [];
  if (!first.length) return <text x="8" y="60" fill="#9ab">Keine Zahlen im Bereich</text>;
  const primary = primarySeries(series);
  if (type === 'pie' || type === 'doughnut') return <Pie data={first} cats={cats} hole={type === 'doughnut'} />;
  if (type === 'radar') return <Radar data={first} cats={cats} />;
  if (type === 'scatter') return <Scatter xs={first} ys={series[1]?.data ?? first.map((_, i) => i)} />;
  if (type === 'funnel') return <Funnel data={first} cats={cats} />;
  if (type === 'waterfall') return <Waterfall data={first} />;
  if (type === 'treemap' || type === 'sunburst' || type === 'pareto') {
    if (!primary.some((value) => value !== 0)) return <text x="8" y="60" fill="#9ab">Keine Zahlen im Bereich</text>;
  }
  if (type === 'treemap') return <Treemap data={primary} cats={cats} />;
  if (type === 'sunburst') return <Sunburst data={primary} />;
  if (type === 'pareto') return <Pareto data={primary} cats={cats} />;
  if (type === 'boxplot') return <Boxplot series={numericSeries(series)} />;
  return <Bars type={type} cats={cats} series={series} />;
}

function numericSeries(series: { name: string; data: number[] }[]): { name: string; data: number[] }[] {
  const usable = series.filter((item) => item.data.some((value) => Number.isFinite(value) && value !== 0));
  return usable.length ? usable : series;
}

function primarySeries(series: { name: string; data: number[] }[]): number[] {
  let best = series[0]?.data ?? [];
  let bestRange = -1;
  for (const item of numericSeries(series)) {
    const range = Math.max(...item.data) - Math.min(...item.data);
    if (range > bestRange) {
      best = item.data;
      bestRange = range;
    }
  }
  return best;
}

function Bars({ type, cats, series }: { type: Chart['type']; cats: string[]; series: { name: string; data: number[] }[] }) {
  const flat = series.flatMap((s) => s.data);
  const max = Math.max(...flat, 0);
  const min = Math.min(...flat, 0);
  const span = max - min || 1;
  const horizontal = type === 'bar';
  const n = Math.max(1, series[0]?.data.length ?? 1);
  const group = (horizontal ? 100 : 170) / n;
  const zero = 108 - ((0 - min) / span) * 96;
  return (
    <g>
      <line x1="28" y1="8" x2="28" y2="108" stroke="#667" />
      <line x1="28" y1={zero} x2="196" y2={zero} stroke="#667" />
      {series.map((s, si) =>
        s.data.map((v, i) => {
          const size = (Math.abs(v) / span) * (horizontal ? 150 : 96);
          const bw = Math.max(2, group / (series.length + 0.4));
          if (type === 'line' || type === 'area') return null;
          if (horizontal) {
            const y = 8 + i * group + si * bw;
            return <rect key={`${si}-${i}`} x={28} y={y} width={size} height={bw - 1} fill={COLORS[si % COLORS.length]} />;
          }
          const x = 32 + i * group + si * bw;
          const y = v >= 0 ? zero - size : zero;
          return <rect key={`${si}-${i}`} x={x} y={y} width={bw - 1} height={size} fill={COLORS[si % COLORS.length]} />;
        }),
      )}
      {(type === 'line' || type === 'area') &&
        series.map((s, si) => {
          const d = s.data
            .map((v, i) => {
              const x = 32 + (i + 0.5) * group;
              const y = 108 - ((v - min) / span) * 96;
              return `${i ? 'L' : 'M'}${x},${y}`;
            })
            .join(' ');
          return (
            <g key={si}>
              {type === 'area' && <path d={`${d} L${32 + (s.data.length - 0.5) * group},108 L32,108 Z`} fill={COLORS[si % COLORS.length]} opacity="0.25" />}
              <path d={d} fill="none" stroke={COLORS[si % COLORS.length]} strokeWidth="1.6" />
            </g>
          );
        })}
      {cats.slice(0, 6).map((cat, i) => (
        <text key={cat + i} x={horizontal ? 2 : 32 + i * group} y={horizontal ? 14 + i * group : 118} fontSize="6" fill="#9ab">
          {cat.slice(0, 8)}
        </text>
      ))}
    </g>
  );
}

function Pie({ data, cats, hole }: { data: number[]; cats: string[]; hole: boolean }) {
  const sum = data.reduce((a, b) => a + Math.abs(b), 0) || 1;
  let angle = -Math.PI / 2;
  return (
    <g>
      {data.map((v, i) => {
        const sweep = (Math.abs(v) / sum) * Math.PI * 2;
        const large = sweep > Math.PI ? 1 : 0;
        const x1 = 90 + Math.cos(angle) * 48;
        const y1 = 60 + Math.sin(angle) * 48;
        const x2 = 90 + Math.cos(angle + sweep) * 48;
        const y2 = 60 + Math.sin(angle + sweep) * 48;
        const d = `M90,60 L${x1},${y1} A48,48 0 ${large} 1 ${x2},${y2} Z`;
        angle += sweep;
        return <path key={i} d={d} fill={COLORS[i % COLORS.length]}>
          <title>{`${cats[i] ?? i + 1}: ${v}`}</title>
        </path>;
      })}
      {hole && <circle cx="90" cy="60" r="24" className="pie-hole" />}
    </g>
  );
}

function Radar({ data, cats }: { data: number[]; cats: string[] }) {
  const max = Math.max(...data.map((v) => Math.abs(v)), 1);
  const n = data.length;
  const pt = (i: number, radius: number) => {
    const a = -Math.PI / 2 + (i / n) * Math.PI * 2;
    return [100 + Math.cos(a) * radius, 60 + Math.sin(a) * radius];
  };
  const d = data.map((v, i) => {
    const [x, y] = pt(i, (Math.abs(v) / max) * 46);
    return `${i ? 'L' : 'M'}${x},${y}`;
  }).join(' ') + ' Z';
  return (
    <g>
      <polygon points={Array.from({ length: n }, (_, i) => pt(i, 46).join(',')).join(' ')} fill="none" stroke="#556" />
      <path d={d} fill="rgba(47,127,224,.35)" stroke="#2f7fe0" />
      {cats.slice(0, n).map((cat, i) => {
        const [x, y] = pt(i, 54);
        return (
          <text key={cat + i} x={x} y={y} fontSize="6" fill="#9ab" textAnchor="middle">
            {cat.slice(0, 8)}
          </text>
        );
      })}
    </g>
  );
}

function Scatter({ xs, ys }: { xs: number[]; ys: number[] }) {
  const maxX = Math.max(...xs, 1);
  const maxY = Math.max(...ys, 1);
  return (
    <g>
      {xs.map((x, i) => (
        <circle key={i} cx={28 + (x / maxX) * 160} cy={108 - ((ys[i] ?? 0) / maxY) * 96} r="2.4" fill="#2f7fe0" />
      ))}
    </g>
  );
}

function Funnel({ data, cats }: { data: number[]; cats: string[] }) {
  const max = Math.max(...data.map((v) => Math.abs(v)), 1);
  return (
    <g>
      {data.map((v, i) => {
        const w = 20 + (Math.abs(v) / max) * 150;
        return <rect key={i} x={(200 - w) / 2} y={8 + i * (100 / data.length)} width={w} height={100 / data.length - 3} fill={COLORS[i % COLORS.length]}>
          <title>{cats[i] ?? ''}</title>
        </rect>;
      })}
    </g>
  );
}

function Waterfall({ data }: { data: number[] }) {
  let run = 0;
  const totals = data.map((v) => {
    const start = run;
    run += v;
    return { start, end: run, v };
  });
  const min = Math.min(0, ...totals.flatMap((t) => [t.start, t.end]));
  const max = Math.max(0, ...totals.flatMap((t) => [t.start, t.end]));
  const span = max - min || 1;
  const yOf = (n: number) => 108 - ((n - min) / span) * 96;
  const bw = 150 / data.length;
  return (
    <g>
      {totals.map((t, i) => {
        const y = Math.min(yOf(t.start), yOf(t.end));
        const h = Math.max(1, Math.abs(yOf(t.end) - yOf(t.start)));
        return <rect key={i} x={32 + i * bw} y={y} width={bw - 4} height={h} fill={t.v >= 0 ? '#3d9b4f' : '#d4544a'} />;
      })}
    </g>
  );
}

function Treemap({ data, cats }: { data: number[]; cats: string[] }) {
  const values = data.map((value) => Math.abs(value));
  const boxes = sliceTreemap(values, 6, 8, 188, 104);
  return (
    <g>
      {boxes.map((box, i) => (
        <g key={i}>
          <rect x={box.x} y={box.y} width={Math.max(0, box.w - 1)} height={Math.max(0, box.h - 1)} fill={COLORS[i % COLORS.length]}>
            <title>{`${cats[i] ?? i + 1}: ${data[i]}`}</title>
          </rect>
          {box.w > 28 && box.h > 14 ? (
            <text x={box.x + 3} y={box.y + 11} fontSize="6" fill="#fff">{(cats[i] ?? '').slice(0, 10)}</text>
          ) : null}
        </g>
      ))}
    </g>
  );
}

function sliceTreemap(values: number[], x: number, y: number, w: number, h: number): { x: number; y: number; w: number; h: number }[] {
  const boxes = values.map(() => ({ x, y, w: 0, h: 0 }));
  const indexed = values.map((value, index) => ({ value, index })).filter((item) => item.value > 0);
  layoutTreemap(indexed.map((item) => item.value), x, y, w, h).forEach((box, order) => {
    boxes[indexed[order].index] = box;
  });
  return boxes;
}

function layoutTreemap(values: number[], x: number, y: number, w: number, h: number): { x: number; y: number; w: number; h: number }[] {
  if (!values.length || w <= 0 || h <= 0) return [];
  if (values.length === 1) return [{ x, y, w, h }];
  const total = values.reduce((sum, value) => sum + value, 0) || 1;
  const share = values[0] / total;
  if (w >= h) {
    const dw = w * share;
    return [{ x, y, w: dw, h }, ...layoutTreemap(values.slice(1), x + dw, y, w - dw, h)];
  }
  const dh = h * share;
  return [{ x, y, w, h: dh }, ...layoutTreemap(values.slice(1), x, y + dh, w, h - dh)];
}

function Sunburst({ data }: { data: number[] }) {
  const outer = data.map((value) => Math.abs(value));
  const inner: number[] = [];
  for (let i = 0; i < outer.length; i += 2) inner.push(outer[i] + (outer[i + 1] ?? 0));
  return (
    <g>
      <Ring values={inner.length ? inner : outer} r0={18} r1={36} />
      <Ring values={outer} r0={38} r1={54} />
    </g>
  );
}

function Ring({ values, r0, r1 }: { values: number[]; r0: number; r1: number }) {
  const sum = values.reduce((a, b) => a + b, 0) || 1;
  let angle = -Math.PI / 2;
  return (
    <g>
      {values.map((value, i) => {
        const sweep = (value / sum) * Math.PI * 2;
        const large = sweep > Math.PI ? 1 : 0;
        const a2 = angle + Math.max(sweep - 0.02, 0);
        const p = (radius: number, a: number) => [100 + Math.cos(a) * radius, 60 + Math.sin(a) * radius];
        const [x1, y1] = p(r1, angle);
        const [x2, y2] = p(r1, a2);
        const [x3, y3] = p(r0, a2);
        const [x4, y4] = p(r0, angle);
        const d = `M${x1},${y1} A${r1},${r1} 0 ${large} 1 ${x2},${y2} L${x3},${y3} A${r0},${r0} 0 ${large} 0 ${x4},${y4} Z`;
        angle += sweep;
        return <path key={i} d={d} fill={COLORS[i % COLORS.length]} />;
      })}
    </g>
  );
}

function Pareto({ data, cats }: { data: number[]; cats: string[] }) {
  const rows = data.map((value, i) => ({ value: Math.abs(value), cat: cats[i] ?? String(i + 1) })).sort((a, b) => b.value - a.value);
  const max = Math.max(...rows.map((row) => row.value), 1);
  const total = rows.reduce((sum, row) => sum + row.value, 0) || 1;
  const n = rows.length;
  const group = 160 / n;
  let run = 0;
  const line = rows.map((row, i) => {
    run += row.value;
    const x = 32 + (i + 0.5) * group;
    const y = 108 - (run / total) * 90;
    return `${i ? 'L' : 'M'}${x},${y}`;
  }).join(' ');
  return (
    <g>
      {rows.map((row, i) => {
        const h = (row.value / max) * 80;
        return <rect key={row.cat + i} x={32 + i * group} y={108 - h} width={Math.max(2, group - 3)} height={h} fill={COLORS[0]} />;
      })}
      <path d={line} fill="none" stroke="#e0a12f" strokeWidth="1.6" />
      {rows.map((row, i) => {
        const step = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(160 / 36))));
        if (i % step !== 0) return null;
        return <text key={row.cat + i} x={32 + (i + 0.2) * group} y={116} fontSize="6" fill="#9ab">{row.cat.slice(0, 6)}</text>;
      })}
    </g>
  );
}

function Boxplot({ series }: { series: { name: string; data: number[] }[] }) {
  const boxes = series.map((item) => quartiles(item.data)).filter((box): box is Quartiles => box !== null);
  if (!boxes.length) return <text x="8" y="60" fill="#9ab">Keine Zahlen im Bereich</text>;
  const min = Math.min(...boxes.map((box) => box.min));
  const max = Math.max(...boxes.map((box) => box.max));
  const span = max - min || 1;
  const yOf = (n: number) => 108 - ((n - min) / span) * 96;
  const slot = 160 / boxes.length;
  return (
    <g>
      {boxes.map((box, i) => {
        const x = 36 + i * slot;
        const top = yOf(box.q3);
        const bottom = yOf(box.q1);
        return (
          <g key={i}>
            <line x1={x + 10} y1={yOf(box.max)} x2={x + 10} y2={yOf(box.min)} stroke="#9ab" />
            <line x1={x + 4} y1={yOf(box.max)} x2={x + 16} y2={yOf(box.max)} stroke="#9ab" />
            <line x1={x + 4} y1={yOf(box.min)} x2={x + 16} y2={yOf(box.min)} stroke="#9ab" />
            <rect x={x} y={top} width={20} height={Math.max(1, bottom - top)} fill={COLORS[i % COLORS.length]} opacity="0.85" />
            <line x1={x} y1={yOf(box.mid)} x2={x + 20} y2={yOf(box.mid)} stroke="#fff" />
          </g>
        );
      })}
    </g>
  );
}

interface Quartiles { min: number; q1: number; mid: number; q3: number; max: number }

function quartiles(data: number[]): Quartiles | null {
  const sorted = data.filter((value) => Number.isFinite(value)).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const at = (p: number) => {
    const index = (sorted.length - 1) * p;
    const lo = Math.floor(index);
    const hi = Math.ceil(index);
    return sorted[lo] * (1 - (index - lo)) + sorted[hi] * (index - lo);
  };
  return { min: sorted[0], q1: at(0.25), mid: at(0.5), q3: at(0.75), max: sorted[sorted.length - 1] };
}

function readChart(ctl: GridController, chart: Chart): { cats: string[]; series: { name: string; data: number[] }[] } {
  const sheet = ctl.sheet();
  const body = chart.hasHeader ? chart.r1 + 1 : chart.r1;
  const cats: string[] = [];
  const columns: { name: string; data: number[]; text: boolean }[] = [];
  for (let c = chart.c1; c <= chart.c2; c++) {
    const name = chart.hasHeader ? sheet.cells[`${chart.r1},${c}`]?.raw || colName(c) : `Reihe ${colName(c)}`;
    const data: number[] = [];
    let text = 0;
    for (let r = body; r <= chart.r2; r++) {
      const n = ctl.numAt(r, c, sheet);
      if (c === chart.c1) cats.push(n === null ? ctl.display(r, c, sheet) || `${r + 1}` : String(r + 1));
      if (n === null && ctl.display(r, c, sheet)) text++;
      data.push(n ?? 0);
    }
    columns.push({ name, data, text: text > data.length / 2 });
  }
  const series = (columns[0]?.text ? columns.slice(1) : columns).map(({ name, data }) => ({ name, data }));
  return { cats, series: series.length ? series : columns.map(({ name, data }) => ({ name, data })) };
}
