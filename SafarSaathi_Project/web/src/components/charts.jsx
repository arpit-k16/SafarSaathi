import React, { useEffect, useMemo, useRef, useState } from 'react';
import { compact, fmt } from '../api.js';

function useWidth() {
  const ref = useRef(null);
  const [width, setWidth] = useState(640);
  useEffect(() => {
    if (!ref.current) return undefined;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(260, entry.contentRect.width)));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, width];
}

function niceTicks(min, max, count = 4) {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [0, 1];
  if (min === max) { max = min + 1; }
  const step0 = (max - min) / count;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= step0) || step0;
  const start = Math.floor(min / step) * step;
  const ticks = [];
  for (let v = start; v < max + step * 0.999; v += step) ticks.push(Number(v.toFixed(10)));
  return ticks.length >= 2 ? ticks : [min, max];
}

/**
 * Categorical-x line chart. series: [{ name, color, dashed, points: [{ x, y }] }]
 * x values are joined in first-seen order, so history and forecast continue naturally.
 */
export function LineChart({ series, height = 260, yFormat = compact, zeroBased = false, label }) {
  const [ref, width] = useWidth();
  const [hover, setHover] = useState(null);
  const xs = useMemo(() => {
    const seen = []; const set = new Set();
    series.forEach(s => s.points.forEach(p => { if (!set.has(p.x)) { set.add(p.x); seen.push(p.x); } }));
    return seen;
  }, [series]);
  const values = series.flatMap(s => s.points.map(p => p.y)).filter(Number.isFinite);
  const pad = { l: 56, r: 14, t: 12, b: 28 };
  const lo = zeroBased ? 0 : Math.min(...values); const hi = Math.max(...values);
  const ticks = niceTicks(zeroBased ? 0 : lo - (hi - lo) * 0.05, hi + (hi - lo) * 0.05);
  const y0 = ticks[0], y1 = ticks.at(-1);
  const W = width, H = height;
  const xAt = i => pad.l + (xs.length <= 1 ? 0 : (i / (xs.length - 1)) * (W - pad.l - pad.r));
  const yAt = v => pad.t + (1 - (v - y0) / (y1 - y0 || 1)) * (H - pad.t - pad.b);
  const index = new Map(xs.map((x, i) => [x, i]));
  const labelEvery = Math.max(1, Math.ceil(xs.length / Math.max(2, Math.floor((W - 80) / 70))));
  const onMove = e => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const i = Math.round(((px - pad.l) / (W - pad.l - pad.r)) * (xs.length - 1));
    setHover(i >= 0 && i < xs.length ? i : null);
  };
  return (
    <div ref={ref} className="relative w-full">
      <svg width={W} height={H} role="img" aria-label={label} onMouseMove={onMove} onMouseLeave={() => setHover(null)} className="block">
        {ticks.map(t => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={yAt(t)} y2={yAt(t)} stroke="var(--color-line)" strokeDasharray="2 4" />
            <text x={pad.l - 8} y={yAt(t) + 4} textAnchor="end" fontSize="11" fill="var(--color-mist)">{yFormat(t)}</text>
          </g>
        ))}
        {xs.map((x, i) => i % labelEvery === 0 && (
          <text key={x} x={xAt(i)} y={H - 8} textAnchor="middle" fontSize="11" fill="var(--color-mist)">{String(x)}</text>
        ))}
        {series.map(s => {
          const pts = s.points.filter(p => Number.isFinite(p.y));
          const d = pts.map((p, k) => `${k ? 'L' : 'M'}${xAt(index.get(p.x)).toFixed(1)},${yAt(p.y).toFixed(1)}`).join('');
          return (
            <g key={s.name}>
              {!s.markersOnly && <path d={d} fill="none" stroke={s.color} strokeWidth={s.dashed ? 2 : 2.2} strokeDasharray={s.dashed ? '6 5' : undefined} strokeLinejoin="round" />}
              {(s.dots || s.markersOnly || pts.length < 16) && pts.map(p => <circle key={p.x} cx={xAt(index.get(p.x))} cy={yAt(p.y)} r={s.markersOnly ? 5 : 3} fill={s.color} />)}
            </g>
          );
        })}
        {hover !== null && <line x1={xAt(hover)} x2={xAt(hover)} y1={pad.t} y2={H - pad.b} stroke="var(--color-mist)" strokeOpacity=".5" />}
      </svg>
      {hover !== null && (
        <div className="pointer-events-none absolute top-2 rounded-lg border border-line bg-ridge px-3 py-2 text-xs shadow-lg"
          style={{ left: Math.min(xAt(hover) + 12, W - 190) }}>
          <div className="mb-1 font-semibold text-snow">{String(xs[hover])}</div>
          {series.map(s => {
            const p = s.points.find(q => q.x === xs[hover]);
            return p ? <div key={s.name} className="num flex justify-between gap-4"><span style={{ color: s.color }}>{s.name}</span><span>{fmt(p.y, 2)}</span></div> : null;
          })}
        </div>
      )}
      <Legend items={series.map(s => ({ name: s.name, color: s.color, dashed: s.dashed }))} />
    </div>
  );
}

export function Legend({ items }) {
  return (
    <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-mist">
      {items.map(i => (
        <span key={i.name} className="inline-flex items-center gap-2">
          <svg width="22" height="8" aria-hidden><line x1="0" x2="22" y1="4" y2="4" stroke={i.color} strokeWidth={i.bar ? 8 : 2.4} strokeDasharray={i.dashed ? '5 4' : undefined} /></svg>
          {i.name}
        </span>
      ))}
    </div>
  );
}

/** Monthly precipitation bars with temperature lines on a second axis. */
export function ClimateChart({ months, height = 260 }) {
  const [ref, width] = useWidth();
  const pad = { l: 48, r: 44, t: 12, b: 28 };
  const W = width, H = height;
  const precip = months.map(m => m.PRECTOTCORR ?? 0);
  const temps = months.flatMap(m => [m.T2M_MIN, m.T2M_MAX]).filter(Number.isFinite);
  const pt = niceTicks(0, Math.max(...precip, 1));
  const tt = niceTicks(Math.min(...temps), Math.max(...temps));
  const band = (W - pad.l - pad.r) / 12;
  const xMid = i => pad.l + band * i + band / 2;
  const yP = v => pad.t + (1 - v / pt.at(-1)) * (H - pad.t - pad.b);
  const yT = v => pad.t + (1 - (v - tt[0]) / (tt.at(-1) - tt[0] || 1)) * (H - pad.t - pad.b);
  const line = key => months.map((m, i) => Number.isFinite(m[key]) ? `${i ? 'L' : 'M'}${xMid(i)},${yT(m[key])}` : '').join('');
  const MONTH = 'JFMAMJJASOND';
  return (
    <div ref={ref} className="w-full">
      <svg width={W} height={H} role="img" aria-label="Monthly rainfall and temperature climatology" className="block">
        {pt.map(t => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={yP(t)} y2={yP(t)} stroke="var(--color-line)" strokeDasharray="2 4" />
            <text x={pad.l - 8} y={yP(t) + 4} textAnchor="end" fontSize="11" fill="var(--color-glacier)">{t}</text>
          </g>
        ))}
        {tt.map(t => <text key={t} x={W - pad.r + 8} y={yT(t) + 4} fontSize="11" fill="var(--color-gold)">{t}°</text>)}
        {months.map((m, i) => (
          <g key={m.month}>
            <rect x={xMid(i) - band * 0.32} width={band * 0.64} y={yP(m.PRECTOTCORR ?? 0)} height={Math.max(0, H - pad.b - yP(m.PRECTOTCORR ?? 0))} rx="3" fill="var(--color-glacier)" fillOpacity=".75">
              <title>{`Month ${m.month}: ${fmt(m.PRECTOTCORR, 1)} mm, mean ${fmt(m.T2M, 1)} °C`}</title>
            </rect>
            <text x={xMid(i)} y={H - 8} textAnchor="middle" fontSize="11" fill="var(--color-mist)">{MONTH[i]}</text>
          </g>
        ))}
        <path d={line('T2M_MAX')} fill="none" stroke="var(--color-gold)" strokeWidth="2" />
        <path d={line('T2M_MIN')} fill="none" stroke="var(--color-gold)" strokeOpacity=".55" strokeWidth="2" strokeDasharray="5 4" />
      </svg>
      <Legend items={[{ name: 'Mean monthly rainfall (mm)', color: 'var(--color-glacier)', bar: true }, { name: 'Mean daily max (°C)', color: 'var(--color-gold)' }, { name: 'Mean daily min (°C)', color: 'var(--color-gold)', dashed: true }]} />
    </div>
  );
}

/** Horizontal comparison bars. rows: [{ label, values: [{ name, value, color }] , max }] */
export function CompareBars({ rows, max, format = v => fmt(v, 1) }) {
  const top = max ?? Math.max(...rows.flatMap(r => r.values.map(v => v.value)), 1);
  return (
    <div className="flex flex-col gap-3">
      {rows.map(r => (
        <div key={r.label}>
          <div className="mb-1 flex justify-between text-sm"><span className="text-snow">{r.label}</span>{r.note && <span className="text-xs text-mist">{r.note}</span>}</div>
          {r.values.map(v => (
            <div key={v.name} className="mb-1 flex items-center gap-3 text-xs">
              {r.values.length > 1 && <span className="w-20 shrink-0 text-mist">{v.name}</span>}
              <div className="h-3 flex-1 rounded-full bg-ridge">
                <div className="h-3 rounded-full" style={{ width: `${Math.min(100, (v.value / top) * 100)}%`, background: v.color }} />
              </div>
              <span className="num w-20 shrink-0 text-right text-snow">{format(v.value)}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

const ramp = (t, stops) => {
  const x = Math.min(1, Math.max(0, t)) * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(x)); const f = x - i;
  return stops[i].map((c, k) => Math.round(c + (stops[i + 1][k] - c) * f));
};
export const RAMPS = {
  gray: [[8, 10, 14], [235, 231, 220]],
  water: [[14, 17, 23], [37, 78, 99], [111, 184, 201], [235, 248, 252]],
  mask: [[14, 17, 23], [111, 184, 201]],
};

/** Paint a 2-D numeric grid to a crisp, pixelated canvas. */
export function GridImage({ grid, ramp: stops = RAMPS.gray, range, size = 256, label }) {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current; if (!canvas || !grid?.length) return;
    const h = grid.length, w = grid[0].length;
    canvas.width = w; canvas.height = h;
    const ctx = canvas.getContext('2d');
    const img = ctx.createImageData(w, h);
    let lo = range?.[0], hi = range?.[1];
    if (lo === undefined) {
      const flat = grid.flat().filter(Number.isFinite).sort((a, b) => a - b);
      lo = flat[Math.floor(flat.length * 0.02)]; hi = flat[Math.floor(flat.length * 0.98)];
    }
    for (let y = 0; y < h; y += 1) for (let x = 0; x < w; x += 1) {
      const [r, g, b] = ramp((grid[y][x] - lo) / ((hi - lo) || 1), stops);
      const o = (y * w + x) * 4; img.data[o] = r; img.data[o + 1] = g; img.data[o + 2] = b; img.data[o + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
  }, [grid, stops, range]);
  return <canvas ref={ref} role="img" aria-label={label} style={{ width: size, height: size, imageRendering: 'pixelated' }} className="max-w-full rounded-lg border border-line" />;
}
