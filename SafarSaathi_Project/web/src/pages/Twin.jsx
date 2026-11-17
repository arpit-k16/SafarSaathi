import React, { useEffect, useMemo, useState } from 'react';
import { api, compact, fmt } from '../api.js';
import { useAction, useQuery } from '../hooks.js';
import { Button, ErrorNotice, Field, Grid, Notes, Page, Panel, Pill, Query, Raw, Select, Stat, Table } from '../components/ui.jsx';
import LayerMap from '../components/LayerMap.jsx';
import Explain, { StatusPill } from '../components/Explain.jsx';

export const BAND_COLOR = { Low: '#8fb878', Moderate: '#e8bd4f', High: '#e89a55', Severe: '#e5765f' };
const BAND_TONE = { Low: 'ok', Moderate: 'warn', High: 'off', Severe: 'off' };
const pct = v => `${v > 0 ? '+' : ''}${v}%`;

function Slider({ label, value, onChange, min, max, step = 1, suffix = '' }) {
  return (
    <Field label={<span className="flex justify-between gap-3"><span>{label}</span><span className="num text-gold">{value}{suffix}</span></span>}>
      <input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(Number(e.target.value))} className="accent-[#e8bd4f]" />
    </Field>
  );
}

function Form({ meta, onRun, loading }) {
  const [year, setYear] = useState(meta.default_year);
  const [weights, setWeights] = useState(() => Object.fromEntries(Object.entries(meta.components).map(([k, c]) => [k, Math.round(c.default_weight * 100)])));
  const [demand, setDemand] = useState(30);
  const [rain, setRain] = useState(0);
  const [target, setTarget] = useState('all');
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  const run = () => onRun({
    year, weights: Object.fromEntries(Object.entries(weights).map(([k, v]) => [k, v / 100])),
    scenario: { demand_change_pct: demand, rainfall_change_pct: rain, ...(target === 'all' ? {} : { destinations: [target] }) },
  });
  useEffect(() => { run(); }, []); // first state on load
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="flex flex-col gap-4">
        <h3 className="font-display font-semibold">State</h3>
        <Field label="Year (observed data)">
          <Select value={year} onChange={e => setYear(Number(e.target.value))}>{[...meta.years].reverse().map(y => <option key={y}>{y}</option>)}</Select>
        </Field>
        <p className="text-xs text-mist">Visitors from UTDB and climate from NASA POWER for this year. Growth uses the five years before it.</p>
      </div>
      <div className="flex flex-col gap-3">
        <h3 className="font-display font-semibold">Index weights <span className="text-xs font-normal text-mist">(normalised; total {total})</span></h3>
        {Object.entries(meta.components).map(([k, c]) => (
          <Slider key={k} label={c.label} value={weights[k]} min={0} max={60} onChange={v => setWeights({ ...weights, [k]: v })} />
        ))}
      </div>
      <div className="flex flex-col gap-3">
        <h3 className="font-display font-semibold">What-if scenario</h3>
        <Slider label="Visitor demand" value={demand} min={-50} max={100} step={5} suffix="%" onChange={setDemand} />
        <Slider label="Monsoon rainfall" value={rain} min={-50} max={100} step={5} suffix="%" onChange={setRain} />
        <Field label="Apply to">
          <Select value={target} onChange={e => setTarget(e.target.value)}>
            <option value="all">All destinations</option>
            {meta.destinations.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </Select>
        </Field>
        <Button onClick={run} disabled={loading || total === 0}>{loading ? 'Recomputing…' : 'Update the twin'}</Button>
      </div>
    </div>
  );
}

function Detail({ row, scen, meta, year }) {
  const statusOf = row.field_status;
  return (
    <Explain
      title={`${row.name}: why ${row.band.toLowerCase()} (${fmt(row.stress_index, 3)})`}
      factors={row.contributions.map(c => ({ label: `${c.label} (${fmt(c.score, 2)} × ${fmt(c.weight, 2)})`, value: c.contribution, note: meta.components[c.component].definition }))}
      uncertainty={`Rank ${row.rank} of 28; between ${row.rank_interval_90[0]} and ${row.rank_interval_90[1]} in 90% of weightings resampled ±50%.`}
      freshness={`UTDB visitors ${year}; NASA POWER climate ${year}.`}
      provenance={[['Index', 'Derived: weighted sum of the five proxies above'], ['Bands', 'Display cut-offs, not validated risk levels']]}
    >
      <div className="mt-4 overflow-x-auto">
        <Table dense columns={['Field', 'Observed state', scen ? 'Scenario (simulated)' : null, 'Status of observed value'].filter(Boolean)} rows={[
          ['Visitors', compact(row.raw.visitors), scen && compact(scen.raw.visitors), <StatusPill status={statusOf.visitors} />],
          ['Five-year mean', compact(row.raw.five_year_mean), scen && compact(scen.raw.five_year_mean), <StatusPill status="observed" />],
          ['Growth ratio', fmt(row.raw.growth_ratio, 2), scen && fmt(scen.raw.growth_ratio, 2), <StatusPill status="derived" />],
          ['Monsoon rain (mm)', fmt(row.raw.monsoon_mm, 0), scen && fmt(scen.raw.monsoon_mm, 0), <StatusPill status={statusOf.monsoon_mm} />],
          ['Heavy-rain days', fmt(row.raw.heavy_days, 0), scen && fmt(scen.raw.heavy_days, 1), <StatusPill status={statusOf.heavy_days} />],
          ['Elevation (m)', fmt(row.raw.elevation_m, 0), scen && fmt(scen.raw.elevation_m, 0), <StatusPill status="observed" />],
          ['Stress index', fmt(row.stress_index, 3), scen && fmt(scen.stress_index, 3), <StatusPill status={scen ? 'simulated' : 'derived'} />],
        ].map(r => r.filter((_, i) => scen || i !== 2))} />
      </div>
    </Explain>
  );
}

function Results({ data, meta }) {
  const [selected, setSelected] = useState(data.baseline[0].id);
  const [view, setView] = useState('scenario');
  const scen = data.scenario;
  const scenBy = useMemo(() => Object.fromEntries((scen?.rows || []).map(r => [r.id, r])), [scen]);
  const rows = view === 'scenario' && scen ? scen.rows : data.baseline;
  const row = data.baseline.find(r => r.id === selected) || data.baseline[0];
  const counts = b => rows.filter(r => r.band === b).length;
  return (
    <>
      <Grid cols={4}>
        <Stat label={`Highest pressure, ${data.year}`} value={data.baseline[0].name} note={`Index ${fmt(data.baseline[0].stress_index, 3)}`} />
        <Stat label="High or severe now" value={data.baseline.filter(r => ['High', 'Severe'].includes(r.band)).length} note="of 28 destinations" tone="hazard" />
        <Stat label="Band changes in scenario" value={scen ? scen.band_changes : '—'} note={scen ? `Demand ${pct(scen.assumptions.demand_change_pct)}, rain ${pct(scen.assumptions.rainfall_change_pct)}` : 'No scenario'} />
        <Stat label="Ranking robustness" value={`ρ ${fmt(data.sensitivity.median_rho, 2)}`} note={`5th percentile ρ ${fmt(data.sensitivity.p5_rho, 2)} over 200 re-weightings`} tone="good" />
      </Grid>
      <Panel title="Destination state map" description="Colour shows the stress band. Click a destination to see what drives its score."
        aside={scen && <div className="flex gap-2"><Button variant={view === 'baseline' ? 'primary' : 'secondary'} onClick={() => setView('baseline')}>Observed</Button><Button variant={view === 'scenario' ? 'primary' : 'secondary'} onClick={() => setView('scenario')}>Scenario</Button></div>}>
        <LayerMap fitKey="twin" onSelect={setSelected} label="Destination stress map"
          points={rows.map(r => ({ id: r.id, lat: r.lat, lon: r.lon, color: BAND_COLOR[r.band], radius: 5 + r.stress_index * 9, ring: r.id === selected,
            label: `${r.name}: ${r.band} (${fmt(r.stress_index, 2)})` }))} />
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-mist">
          {Object.entries(BAND_COLOR).map(([b, c]) => <span key={b} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: c }} />{b} ({counts(b)})</span>)}
          <span>{view === 'scenario' && scen ? 'Showing simulated scenario values' : 'Showing observed-year values'}</span>
        </div>
      </Panel>
      <Detail row={row} scen={scenBy[row.id]} meta={meta} year={data.year} />
      <Panel title="Ranked destinations" description="Observed index with the 90% rank range under re-weighting, and the scenario result beside it.">
        <Table dense columns={['Rank', 'Destination', 'Visitors', 'Index', 'Band', 'Rank range', 'Top driver', ...(scen ? ['Scenario index', 'Change', 'Scenario band'] : [])]}
          rows={data.baseline.map(r => {
            const s = scenBy[r.id];
            return [r.rank, <button type="button" className="text-left text-gold hover:underline" onClick={() => setSelected(r.id)}>{r.name}</button>,
              compact(r.raw.visitors), fmt(r.stress_index, 3), <Pill tone={BAND_TONE[r.band]}>{r.band}</Pill>, `${r.rank_interval_90[0]}–${r.rank_interval_90[1]}`,
              r.contributions[0].label,
              ...(s ? [fmt(s.stress_index, 3), `${s.delta_index >= 0 ? '+' : ''}${fmt(s.delta_index, 3)}`, s.band !== r.band ? <Pill tone={BAND_TONE[s.band]}>{s.band}</Pill> : <span className="text-mist">same</span>] : [])];
          })} />
        <Notes items={data.limitations} />
        <Raw data={data} />
      </Panel>
    </>
  );
}

export default function Twin() {
  const meta = useQuery('twin:meta', api.twinMetadata);
  const action = useAction();
  return (
    <Page title="Digital twin and stress index" intro="A destination-level state for 28 Uttarakhand destinations, built from UTDB visitor counts and NASA POWER climate. The Destination Stress Index is a transparent weighted sum of five proxies: change the weights or run a what-if scenario and the state recomputes. Every value is labelled observed, derived or simulated.">
      <Query q={meta}>{m => (
        <>
          <Panel title="Set up the twin" description={`Components: ${Object.values(m.components).map(c => c.label.toLowerCase()).join(', ')}. Visitor rows pass UTDB's own Indian + foreign = total check (${m.sources.visitor_sum_check_failures} failures).`}>
            <Form meta={m} loading={action.loading} onRun={body => action.run(() => api.twinState(body))} />
            <div className="mt-4"><ErrorNotice error={action.error} /></div>
          </Panel>
          {action.data && <Results key={JSON.stringify(action.data.weights) + action.data.year + JSON.stringify(action.data.scenario?.assumptions)} data={action.data} meta={m} />}
          <Panel title="How each component is defined">
            <Table dense columns={['Component', 'Default weight', 'Definition', 'Status']} rows={Object.values(m.components).map(c => [c.label, fmt(c.default_weight, 2), c.definition, <StatusPill status={c.status} />])} />
          </Panel>
        </>
      )}</Query>
    </Page>
  );
}
