import React, { useState } from 'react';
import { api, fmt, scenarioPayload } from '../api.js';
import { useAction, useSession } from '../hooks.js';
import { Button, ErrorNotice, Field, Grid, Input, Notes, Page, Panel, Pill, Raw, Stat, Table } from '../components/ui.jsx';
import { CompareBars } from '../components/charts.jsx';

const PRESETS = [
  { name: 'Pilgrim surge, road partly closed', values: { baseline_visitors: 18000, capacity: 20000, demand_change_percent: 25, available_capacity_percent: 60 } },
  { name: 'Off-season with full access', values: { baseline_visitors: 6000, capacity: 20000, demand_change_percent: -20, available_capacity_percent: 100 } },
  { name: 'Festival peak', values: { baseline_visitors: 15000, capacity: 16000, demand_change_percent: 80, available_capacity_percent: 90 } },
];
const FIELDS = [
  ['baseline_visitors', 'Baseline visitors', 'Visitors in your chosen period, e.g. one day', '0 to 1,000,000,000'],
  ['capacity', 'Visitor capacity', 'Places available in the same period (beds, permits, seats)', '1 to 1,000,000,000'],
  ['demand_change_percent', 'Demand change (%)', 'How much demand rises or falls', '−100 to 1,000'],
  ['available_capacity_percent', 'Capacity still available (%)', 'After closures, damage or diversions', '0 to 100'],
];

export default function Scenarios() {
  const session = useSession();
  const [form, setForm] = useState(PRESETS[0].values);
  const [inputError, setInputError] = useState(null);
  const action = useAction();
  const submit = async () => {
    let payload;
    try { payload = scenarioPayload(form); setInputError(null); } catch (e) { setInputError(e); return; }
    const result = await action.run(() => api.simulate(payload));
    if (result) session.addScenario(result);
  };
  const r = action.data;
  return (
    <Page title="Capacity scenarios" intro="Test what happens when demand rises and capacity shrinks. The backend does transparent arithmetic: served visitors are the smaller of demand and available capacity. Inputs are your assumptions; nothing here is a prediction.">
      <Panel title="Set the assumptions" description="Presets are illustrative starting points, not observed figures for any destination.">
        <div className="mb-4 flex flex-wrap gap-2">
          {PRESETS.map(p => <Button key={p.name} variant="secondary" onClick={() => { setForm(p.values); action.reset(); }}>{p.name}</Button>)}
        </div>
        <form onSubmit={e => { e.preventDefault(); submit(); }} className="grid gap-4 md:grid-cols-2">
          {FIELDS.map(([key, label, hint, range]) => (
            <Field key={key} label={label} hint={`${hint}. Range ${range}.`}>
              <Input type="number" step="any" inputMode="decimal" value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} required />
            </Field>
          ))}
          <div className="md:col-span-2"><Button type="submit" disabled={action.loading}>{action.loading ? 'Calculating…' : 'Run scenario'}</Button></div>
        </form>
        {inputError && <div className="mt-4"><ErrorNotice error={{ kind: 'invalid', message: inputError.message }} /></div>}
        <div className="mt-4"><ErrorNotice error={action.error} /></div>
      </Panel>

      {r && (
        <>
          <Grid cols={4}>
            <Stat label="Scenario demand" value={fmt(r.scenario.visitors, 0)} note={`Baseline ${fmt(r.baseline.visitors, 0)}`} />
            <Stat label="Available capacity" value={fmt(r.scenario.available_capacity, 0)} note={`Baseline ${fmt(r.baseline.available_capacity, 0)}`} tone="water" />
            <Stat label="Visitors who cannot be served" value={fmt(r.scenario.unserved_visitors, 0)} note={`${r.delta_unserved_visitors >= 0 ? '+' : ''}${fmt(r.delta_unserved_visitors, 0)} vs baseline`} tone={r.scenario.unserved_visitors > 0 ? 'hazard' : 'good'} />
            <Stat label="Demand ÷ capacity" value={r.scenario.utilization_ratio == null ? 'Undefined' : `${fmt(r.scenario.utilization_ratio * 100, 0)}%`} note={r.scenario.utilization_ratio == null ? 'No capacity available' : `Baseline ${fmt(r.baseline.utilization_ratio * 100, 0)}%`} tone={r.scenario.utilization_ratio > 1 ? 'hazard' : undefined} />
          </Grid>
          <Panel title="Baseline against scenario" aside={<Pill tone="muted">{r.model_version}</Pill>}>
            <CompareBars format={v => fmt(v, 0)} rows={[
              ['Demand', 'visitors', 'var(--color-snow)'], ['Available capacity', 'available_capacity', 'var(--color-glacier)'],
              ['Served', 'served_visitors', 'var(--color-moss)'], ['Not served', 'unserved_visitors', 'var(--color-ember)'],
            ].map(([label, key, color]) => ({ label, values: [{ name: 'Baseline', value: r.baseline[key], color: 'var(--color-mist)' }, { name: 'Scenario', value: r.scenario[key], color }] }))} />
            <p className="mt-3 text-sm text-mist">Units: {r.units}.</p>
            <Notes items={[...r.assumptions, ...r.limitations]} title="Assumptions and limitations" />
            <Raw data={r} />
          </Panel>
        </>
      )}

      {session.scenarios.length > 0 && (
        <Panel title="This session's scenarios" description="Kept in this browser tab only. The latest one can be included in a report."
          aside={<div className="flex gap-2"><a href="#/reports" className="text-sm font-semibold text-gold hover:underline">Build a report</a><Button variant="ghost" onClick={session.clearScenarios}>Clear</Button></div>}>
          <Table columns={['Run at', 'Baseline', 'Capacity', 'Demand Δ', 'Available', 'Not served']} rows={session.scenarios.map(s => [
            new Date(s.ranAt).toLocaleTimeString('en-IN'), fmt(s.parameters.baseline_visitors, 0), fmt(s.parameters.capacity, 0),
            `${fmt(s.parameters.demand_change_percent, 1)}%`, `${fmt(s.parameters.available_capacity_percent, 1)}%`, fmt(s.scenario.unserved_visitors, 0),
          ])} />
        </Panel>
      )}
    </Page>
  );
}
