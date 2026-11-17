import React, { useState } from 'react';
import { api, bytes, fmt } from '../api.js';
import { useQuery } from '../hooks.js';
import { Button, Field, Grid, Notes, Origin, Page, Panel, Pill, Query, Select, Stat, Table } from '../components/ui.jsx';
import { CompareBars } from '../components/charts.jsx';

const PAGE = 25;

export default function DataHub() {
  const [category, setCategory] = useState('');
  const [offset, setOffset] = useState(0);
  const overview = useQuery('datasets:overview', () => api.datasets(0, 1));
  const page = useQuery(`datasets:${category}:${offset}`, () => api.datasets(offset, PAGE, category));
  return (
    <Page title="Data hub" intro="The project's local data collection: what files exist, how large they are, and the source, coverage and license declared in the collection manifest. Listing a file does not mean it was ingested or re-verified.">
      <Query q={overview}>{o => {
        const groups = Object.entries(o.groups).sort((a, b) => b[1].size_bytes - a[1].size_bytes);
        const total = groups.reduce((s, [, g]) => s + g.size_bytes, 0);
        return (
          <>
            <Grid cols={4}>
              <Stat label="Files" value={fmt(o.total, 0)} />
              <Stat label="Total size" value={bytes(total)} />
              <Stat label="Source groups" value={groups.length} />
              <Stat label="Live connectors" value="None" note="All sources are archived files" />
            </Grid>
            <Panel title="Size by source group" aside={<Origin data={o} />}>
              <CompareBars format={bytes} rows={groups.slice(0, 14).map(([k, g]) => ({ label: k, note: `${fmt(g.files, 0)} files`, values: [{ name: 'Size', value: g.size_bytes, color: 'var(--color-gold)' }] }))} />
            </Panel>
            <Panel title="Files">
              <div className="mb-4 flex flex-wrap items-end gap-3">
                <Field label="Category" className="w-64">
                  <Select value={category} onChange={e => { setCategory(e.target.value); setOffset(0); }}>
                    <option value="">All categories</option>
                    {(o.categories || []).map(c => <option key={c} value={c}>{c}</option>)}
                  </Select>
                </Field>
              </div>
              <Query q={page}>{p => (
                <>
                  <Table dense columns={['File', 'Group', 'Format', 'Size', 'Coverage', 'License', 'Declared size']} rows={p.files.map(f => [
                    <span className="break-all">{f.relative_path}</span>, `${f.root}/${f.category}`, f.format, bytes(f.size_bytes),
                    f.coverage_start ? `${f.coverage_start} – ${f.coverage_end ?? ''}` : null, f.license,
                    f.declared_size_matches == null ? <span className="text-mist">Not declared</span> : <Pill tone={f.declared_size_matches ? 'ok' : 'off'}>{f.declared_size_matches ? 'Matches' : 'Differs'}</Pill>,
                  ])} />
                  <div className="mt-4 flex items-center justify-between text-sm text-mist">
                    <span>{p.total ? `${fmt(offset + 1, 0)}–${fmt(Math.min(offset + PAGE, p.total), 0)} of ${fmt(p.total, 0)}` : 'No files in this category'}</span>
                    <div className="flex gap-2">
                      <Button variant="secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</Button>
                      <Button variant="secondary" disabled={offset + PAGE >= p.total} onClick={() => setOffset(offset + PAGE)}>Next</Button>
                    </div>
                  </div>
                  <Notes items={p.limitations} />
                </>
              )}</Query>
            </Panel>
          </>
        );
      }}</Query>
    </Page>
  );
}
