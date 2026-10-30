import React from 'react';

export default function ApiState({ loading, error, retry, empty, children }) {
  const label = !error ? '' : error.kind === 'timeout' ? 'REQUEST TIMEOUT'
    : error.kind === 'unavailable' ? 'MODEL / DATASET UNAVAILABLE'
    : error.status === 422 || !error.kind ? 'INVALID INPUT / REQUEST FAILED'
    : error.kind === 'format' ? 'INVALID API RESPONSE'
    : error.kind === 'network' ? 'API UNAVAILABLE' : 'REQUEST FAILED';
  return <div className="font-mono text-xs text-slate-300" aria-live="polite" aria-busy={!!loading}>
    {loading && <p className="text-primary py-2" role="status">Loading backend data…</p>}
    {error && <div className="border border-amber-500/40 rounded p-3 my-2" role="alert">
      <span className="text-amber-400">{label}: </span>
      {error.message}{retry && <button type="button" className="ml-3 text-primary underline" onClick={retry}>Retry</button>}
    </div>}
    {!loading && !error && empty && <p className="text-slate-400 py-2">No results available.</p>}
    {children}
  </div>;
}

export function DataTable({ columns, rows }) {
  return <div className="overflow-x-auto"><table className="w-full text-left font-mono text-[11px]">
    <thead className="text-slate-400"><tr>{columns.map(c => <th key={c} className="p-2 border-b border-white/10">{c}</th>)}</tr></thead>
    <tbody>{rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j} className="p-2 border-b border-white/5 align-top break-words">{cell ?? 'Not recorded'}</td>)}</tr>)}</tbody>
  </table>{!rows.length && <p className="p-2 text-slate-400">No records available.</p>}</div>;
}

export function Limitations({ items = [] }) {
  const values = Array.isArray(items) ? items : [items];
  return <div className="text-[11px] text-slate-400 leading-relaxed mt-3">{values.map((item, i) => <p key={i}>{item}</p>)}</div>;
}
