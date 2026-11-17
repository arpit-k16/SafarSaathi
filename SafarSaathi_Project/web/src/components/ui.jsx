import React from 'react';

export function Page({ title, intro, actions, children }) {
  return (
    <div className="mx-auto w-full max-w-[1180px] px-5 pb-16 pt-8 md:px-8">
      <header className="mb-7 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div className="max-w-[68ch]">
          <h1 className="text-[2rem] font-semibold leading-tight text-snow md:text-[2.4rem]">{title}</h1>
          {intro && <p className="mt-2 text-[15px] text-mist">{intro}</p>}
        </div>
        {actions && <div className="flex shrink-0 flex-wrap gap-2 no-print">{actions}</div>}
      </header>
      <div className="flex flex-col gap-6">{children}</div>
    </div>
  );
}

export function Panel({ title, description, aside, children, className = '', tone }) {
  const border = tone === 'hazard' ? 'border-ember/35' : tone === 'water' ? 'border-glacier/30' : 'border-line';
  return (
    <section className={`print-plain rounded-xl border ${border} bg-slate p-5 md:p-6 ${className}`}>
      {(title || aside) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div className="max-w-[72ch]">
            {title && <h2 className="text-lg font-semibold text-snow">{title}</h2>}
            {description && <p className="mt-1 text-sm text-mist">{description}</p>}
          </div>
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

export function Grid({ cols = 4, children }) {
  const map = { 2: 'md:grid-cols-2', 3: 'md:grid-cols-3', 4: 'sm:grid-cols-2 lg:grid-cols-4' };
  return <div className={`grid grid-cols-1 gap-4 ${map[cols]}`}>{children}</div>;
}

export function Stat({ label, value, note, tone }) {
  const color = tone === 'water' ? 'text-glacier' : tone === 'hazard' ? 'text-ember' : tone === 'good' ? 'text-moss' : 'text-snow';
  return (
    <div className="print-plain rounded-xl border border-line bg-slate px-5 py-4">
      <div className="text-sm text-mist">{label}</div>
      <div className={`num mt-1 font-display text-[1.75rem] font-semibold leading-tight ${color}`}>{value}</div>
      {note && <div className="mt-1 text-xs text-mist">{note}</div>}
    </div>
  );
}

const PILL = {
  ok: 'border-moss/40 text-moss bg-moss/10',
  warn: 'border-gold/40 text-gold bg-gold/10',
  off: 'border-ember/40 text-ember bg-ember/10',
  info: 'border-glacier/40 text-glacier bg-glacier/10',
  muted: 'border-line text-mist bg-ridge',
};
PILL.good = PILL.ok;
export function Pill({ tone = 'muted', children, title }) {
  return <span title={title} className={`inline-flex items-center whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium ${PILL[tone]}`}>{children}</span>;
}

export function qualityTone(status = '') {
  const s = String(status).toUpperCase();
  if (s.startsWith('FINAL')) return 'ok';
  if (s.includes('EVALUATED') && !s.includes('EXPERIMENTAL')) return 'ok';
  if (s.includes('EXPERIMENTAL') || s.includes('TRAINED')) return 'warn';
  if (s.includes('UNAVAILABLE') || s.includes('INSUFFICIENT') || s.includes('NOT')) return 'off';
  return 'muted';
}
export const humanize = s => (String(s) === 'FINAL_V1' ? 'Final v1.0' : String(s ?? '')).replaceAll('_', ' ').toLowerCase().replace(/^./, c => c.toUpperCase());

export function Button({ variant = 'primary', className = '', ...props }) {
  const styles = {
    primary: 'bg-gold text-ink hover:bg-[#f3cc63] disabled:bg-gold-dim/50',
    secondary: 'border border-line bg-ridge text-snow hover:border-gold/60',
    ghost: 'text-gold hover:bg-gold/10',
  };
  return <button type="button" className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${styles[variant]} ${className}`} {...props} />;
}

export function Field({ label, hint, children, className = '' }) {
  return (
    <label className={`flex flex-col gap-1.5 text-sm ${className}`}>
      <span className="font-medium text-snow">{label}</span>
      {children}
      {hint && <span className="text-xs text-mist">{hint}</span>}
    </label>
  );
}
export const inputClass = 'w-full rounded-lg border border-line bg-ridge px-3 py-2 text-sm text-snow placeholder:text-mist/60 focus:border-gold focus:outline-none';
export const Input = props => <input className={inputClass} {...props} />;
export const Select = ({ children, ...props }) => <select className={inputClass} {...props}>{children}</select>;

export function Loading({ label = 'Loading from the backend…' }) {
  return (
    <div role="status" className="flex items-center gap-3 py-6 text-sm text-mist">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-gold/30 border-t-gold" aria-hidden />
      {label}
    </div>
  );
}

const ERROR_TITLE = {
  network: 'Backend not reachable', timeout: 'Backend timed out', unavailable: 'Not available on this installation',
  invalid: 'Input rejected', format: 'Unexpected response', http: 'Request failed', canceled: 'Canceled',
};
export function ErrorNotice({ error, retry }) {
  if (!error) return null;
  const tone = error.kind === 'unavailable' ? 'border-gold/40 bg-gold/5' : 'border-ember/40 bg-ember/5';
  return (
    <div role="alert" className={`rounded-lg border ${tone} px-4 py-3 text-sm`}>
      <div className="font-semibold text-snow">{ERROR_TITLE[error.kind] || 'Something went wrong'}{error.status ? <span className="ml-2 font-normal text-mist">HTTP {error.status}</span> : null}</div>
      <p className="mt-1 text-mist">{error.message}</p>
      {retry && <Button variant="ghost" className="mt-2 -ml-3" onClick={retry}>Try again</Button>}
    </div>
  );
}

export function Query({ q, children, label }) {
  if (q.loading && !q.data) return <Loading label={label} />;
  if (q.error) return <ErrorNotice error={q.error} retry={q.retry} />;
  if (!q.data) return null;
  return children(q.data);
}

export function Notes({ items, title = 'Scope and limitations' }) {
  const list = (Array.isArray(items) ? items : [items]).filter(Boolean);
  if (!list.length) return null;
  return (
    <details className="group mt-4 rounded-lg border border-line bg-ink/40 px-4 py-2 text-sm">
      <summary className="cursor-pointer select-none py-1 text-mist hover:text-snow">{title} ({list.length})</summary>
      <ul className="mt-2 list-disc space-y-1 pb-2 pl-5 text-mist">{list.map((x, i) => <li key={i}>{typeof x === 'string' ? x : JSON.stringify(x)}</li>)}</ul>
    </details>
  );
}

export function Table({ columns, rows, empty = 'No records.', dense }) {
  return (
    <div className="scroll-thin overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr>{columns.map(c => <th key={c} className="border-b border-line px-3 py-2 font-medium text-mist">{c}</th>)}</tr>
        </thead>
        <tbody className="num">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-ridge/60">
              {row.map((cell, j) => <td key={j} className={`border-b border-line/60 px-3 ${dense ? 'py-1.5' : 'py-2'} align-top`}>{cell ?? <span className="text-mist">—</span>}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && <p className="px-3 py-4 text-sm text-mist">{empty}</p>}
    </div>
  );
}

export function Origin({ data }) {
  if (!data?.data_origin) return null;
  return data.data_origin === 'BUILD_SNAPSHOT'
    ? <Pill tone="info" title="Captured from local files at build time and checksum-verified">Snapshot of {new Date(data.snapshot_generated_utc).toLocaleDateString('en-IN', { dateStyle: 'medium' })}</Pill>
    : <Pill tone="ok" title="Read from files on this server">Local source files</Pill>;
}

export function Raw({ data, label = 'Full JSON response' }) {
  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer text-mist hover:text-snow">{label}</summary>
      <pre className="scroll-thin mt-2 max-h-96 overflow-auto rounded-lg border border-line bg-ink p-3 font-mono text-xs text-mist">{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}

export function Segmented({ options, value, onChange, label }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-lg border border-line bg-ridge p-0.5">
      {options.map(o => (
        <button key={o.value} type="button" role="radio" aria-checked={value === o.value} onClick={() => onChange(o.value)}
          className={`rounded-md px-3 py-1.5 text-sm transition-colors ${value === o.value ? 'bg-gold text-ink font-semibold' : 'text-mist hover:text-snow'}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}
