import React from 'react';
import { fmt } from '../api.js';
import { Pill } from './ui.jsx';

export const STATUS_TONE = { observed: 'ok', derived: 'info', simulated: 'warn', estimated: 'warn' };
export function StatusPill({ status }) {
  return <Pill tone={STATUS_TONE[status] || 'muted'} title={`Data status: ${status}`}>{status}</Pill>;
}

/** Explanation block: contributing factors, uncertainty, freshness and provenance (report §10.5). */
export default function Explain({ title = 'Why this result', factors = [], format = v => fmt(v, 3), baseline, rule, uncertainty, freshness, provenance = [], children }) {
  const top = Math.max(...factors.map(f => Math.abs(f.value)), 1e-9);
  return (
    <div className="rounded-xl border border-gold/25 bg-ink/40 p-4 md:p-5">
      <h3 className="font-display text-base font-semibold text-gold">{title}</h3>
      {rule && <p className="mt-2 text-sm text-snow">{rule}</p>}
      {baseline && <p className="mt-2 text-sm text-mist">{baseline}</p>}
      {factors.length > 0 && (
        <ul className="mt-3 space-y-2">
          {factors.map(f => (
            <li key={f.label} className="grid grid-cols-[minmax(0,13rem)_1fr_auto] items-center gap-3 text-sm">
              <span className="truncate text-snow" title={f.note || f.label}>{f.label}</span>
              <span className="h-2.5 rounded-full bg-ridge">
                <span className={`block h-2.5 rounded-full ${f.value < 0 ? 'bg-glacier' : 'bg-gold'}`} style={{ width: `${(Math.abs(f.value) / top) * 100}%` }} />
              </span>
              <span className="num w-24 text-right text-mist">{format(f.value)}</span>
            </li>
          ))}
        </ul>
      )}
      {children}
      <dl className="mt-4 grid gap-x-6 gap-y-2 text-sm md:grid-cols-2">
        {uncertainty && <div><dt className="text-mist">Uncertainty</dt><dd className="text-snow">{uncertainty}</dd></div>}
        {freshness && <div><dt className="text-mist">Data freshness</dt><dd className="text-snow">{freshness}</dd></div>}
        {provenance.map(([k, v]) => <div key={k}><dt className="text-mist">{k}</dt><dd className="text-snow">{v}</dd></div>)}
      </dl>
    </div>
  );
}
