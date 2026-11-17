import React, { useState } from 'react';
import { api, fmt, optimizationPayload } from '../api.js';
import { useAction, useQuery, useSession } from '../hooks.js';
import { Button, ErrorNotice, Field, Grid, Input, Notes, Page, Panel, Pill, Query, Raw, Segmented, Stat, Table, inputClass } from '../components/ui.jsx';
import { CompareBars, LineChart } from '../components/charts.jsx';
import InterventionPlanner from './InterventionPlanner.jsx';

const START = {
  demand: 180, exposure_tradeoff: 0.5, algorithm: 'ga', seed: 23, population: 24, iterations: 40,
  destinations: [
    { id: 'Site A', capacity: 120, accessibility: 1, road_capacity: 100, resource_capacity: 110, exposure_weight: 0.8 },
    { id: 'Site B', capacity: 100, accessibility: 0.9, road_capacity: 95, resource_capacity: 90, exposure_weight: 0.2 },
    { id: 'Site C', capacity: 80, accessibility: 1, road_capacity: 75, resource_capacity: 70, exposure_weight: 0.4 },
  ],
};
const COLS = [['id', 'Site', 'text'], ['capacity', 'Capacity'], ['accessibility', 'Access 0–1'], ['road_capacity', 'Road cap.'], ['resource_capacity', 'Resource cap.'], ['exposure_weight', 'Exposure 0–1']];

function Result({ r, onReport }) {
  return (
    <>
      <Grid cols={4}>
        <Stat label="Objective, proportional plan" value={fmt(r.baseline.objective, 4)} note="Allocate by effective capacity" />
        <Stat label={`Objective, ${r.algorithm.toUpperCase()} plan`} value={fmt(r.candidate.objective, 4)} note={`${r.objective_improvement >= 0 ? 'Lower by' : 'Higher by'} ${fmt(Math.abs(r.objective_improvement), 4)}`} tone={r.objective_improvement > 0 ? 'good' : undefined} />
        <Stat label="Exposure proxy" value={fmt(r.candidate.exposure_proxy, 3)} note={`Proportional ${fmt(r.baseline.exposure_proxy, 3)}`} tone="hazard" />
        <Stat label="Runtime" value={`${fmt(r.runtime_seconds * 1000, 0)} ms`} note={`Seed ${r.seed}, ${r.population} × ${r.iterations}`} />
      </Grid>
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Visitors per site" description="Candidate allocation against the proportional reference, with each site's effective capacity.">
          <CompareBars format={v => fmt(v, 1)} rows={r.allocations.map(a => ({
            label: a.id, note: `cap ${fmt(a.effective_capacity, 1)}`,
            values: [{ name: 'Proportional', value: a.baseline, color: 'var(--color-mist)' }, { name: r.algorithm.toUpperCase(), value: a.candidate, color: 'var(--color-gold)' }],
          }))} max={Math.max(...r.allocations.map(a => a.effective_capacity))} />
        </Panel>
        <Panel title="Convergence" description="Best objective found after each iteration.">
          <LineChart label="Convergence" yFormat={v => fmt(v, 3)} height={230} series={[{ name: 'Best objective', color: 'var(--color-gold)', points: r.convergence.map((v, i) => ({ x: String(i), y: v })) }]} />
        </Panel>
      </div>
      <Panel title="Feasibility checks" aside={<Pill tone="muted">{r.formulation_version}</Pill>}>
        <Table columns={['Check', 'Value']} rows={[
          ['Total demand conserved (error)', fmt(r.conservation_error, 9)],
          ['Largest capacity violation', fmt(r.max_capacity_violation, 9)],
          ['Globally optimal', r.globally_optimal ? 'Yes' : 'Not claimed — heuristic candidate'],
          ['Units', r.units],
        ]} />
        <Notes items={r.limitations} />
        <div className="mt-3 flex flex-wrap gap-3"><Button variant="secondary" onClick={onReport}>Use in report</Button></div>
        <Raw data={r} />
      </Panel>
    </>
  );
}

export default function Optimizer() {
  const meta = useQuery('opt-meta', api.optimizationMetadata);
  const session = useSession();
  const [form, setForm] = useState(START);
  const [inputError, setInputError] = useState(null);
  const action = useAction();
  const compare = useAction();
  const setRow = (i, key, value) => setForm(f => ({ ...f, destinations: f.destinations.map((d, j) => (j === i ? { ...d, [key]: value } : d)) }));
  const build = override => { try { const p = optimizationPayload({ ...form, ...override }); setInputError(null); return p; } catch (e) { setInputError(e); return null; } };
  const run = () => { const p = build(); if (p) { compare.reset(); action.run(() => api.optimize(p)); } };
  const runBoth = () => {
    const ga = build({ algorithm: 'ga' }); const pso = build({ algorithm: 'pso' });
    if (ga && pso) { action.reset(); compare.run(() => Promise.all([api.optimize(ga), api.optimize(pso)])); }
  };
  const toReport = r => { session.setOptimization(Object.fromEntries(['problem', 'algorithm', 'seed', 'population', 'iterations'].map(k => [k, r[k]]))); window.location.hash = '/reports'; };

  return (
    <Page title="Allocation optimizer" intro="Two optimisers. The allocation optimiser spreads a fixed number of visitors across sites to balance crowding against hazard exposure. The intervention planner chooses which interventions to fund, scoring each plan through the digital twin. Both use genetic-algorithm (GA) and particle-swarm (PSO) search with a fixed seed, so results are reproducible.">
      <Query q={meta}>{m => (
        <Panel title="Formulation" description="Every number below is an assumption you supply. There is no verified data on intervention costs or real exposure.">
          <dl className="grid gap-3 text-sm md:grid-cols-2">
            <div><dt className="text-mist">Minimise</dt><dd className="font-mono text-xs text-snow">{m.objective}</dd></div>
            <div><dt className="text-mist">Subject to</dt><dd className="font-mono text-xs text-snow">{m.constraints}</dd></div>
          </dl>
        </Panel>
      )}</Query>

      <Panel title="Problem">
        <div className="grid gap-4 md:grid-cols-3">
          <Field label="Total visitors to place" hint="Must not exceed total effective capacity"><Input type="number" step="any" value={form.demand} onChange={e => setForm({ ...form, demand: e.target.value })} /></Field>
          <Field label={`Exposure vs crowding weight: ${fmt(Number(form.exposure_tradeoff), 2)}`} hint="0 = only avoid crowding, 1 = only avoid exposure">
            <input type="range" min="0" max="1" step="0.05" value={form.exposure_tradeoff} onChange={e => setForm({ ...form, exposure_tradeoff: e.target.value })} className="mt-2 accent-[var(--color-gold)]" />
          </Field>
          <Field label="Solver"><Segmented label="Solver" value={form.algorithm} onChange={algorithm => setForm({ ...form, algorithm })} options={[{ value: 'ga', label: 'Genetic (GA)' }, { value: 'pso', label: 'Particle swarm (PSO)' }]} /></Field>
          <Field label="Seed" hint="0 to 4,294,967,295"><Input type="number" value={form.seed} onChange={e => setForm({ ...form, seed: e.target.value })} /></Field>
          <Field label="Population" hint="8 to 64"><Input type="number" value={form.population} onChange={e => setForm({ ...form, population: e.target.value })} /></Field>
          <Field label="Iterations" hint="1 to 100"><Input type="number" value={form.iterations} onChange={e => setForm({ ...form, iterations: e.target.value })} /></Field>
        </div>
        <div className="scroll-thin mt-6 overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead><tr>{COLS.map(([, l]) => <th key={l} className="px-1 pb-2 text-left font-medium text-mist">{l}</th>)}<th /></tr></thead>
            <tbody>
              {form.destinations.map((d, i) => (
                <tr key={i}>
                  {COLS.map(([key, l, type]) => (
                    <td key={key} className="px-1 py-1"><input aria-label={`${l}, row ${i + 1}`} className={inputClass} type={type || 'number'} step="any" value={d[key]} onChange={e => setRow(i, key, type ? e.target.value : e.target.value)} /></td>
                  ))}
                  <td className="px-1"><Button variant="ghost" aria-label={`Remove ${d.id}`} disabled={form.destinations.length <= 1} onClick={() => setForm(f => ({ ...f, destinations: f.destinations.filter((_, j) => j !== i) }))}>Remove</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-mist">Effective capacity = min(capacity × access, road capacity, resource capacity).</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Button variant="secondary" disabled={form.destinations.length >= 12} onClick={() => setForm(f => ({ ...f, destinations: [...f.destinations, { id: `Site ${String.fromCharCode(65 + f.destinations.length)}`, capacity: 50, accessibility: 1, road_capacity: 50, resource_capacity: 50, exposure_weight: 0.5 }] }))}>Add site</Button>
          <Button onClick={run} disabled={action.loading || compare.loading}>{action.loading ? 'Optimising…' : `Run ${form.algorithm.toUpperCase()}`}</Button>
          <Button variant="secondary" onClick={runBoth} disabled={action.loading || compare.loading}>{compare.loading ? 'Running both…' : 'Compare GA and PSO'}</Button>
        </div>
        {inputError && <div className="mt-4"><ErrorNotice error={{ kind: 'invalid', message: inputError.message }} /></div>}
        <div className="mt-4"><ErrorNotice error={action.error || compare.error} /></div>
      </Panel>

      {action.data && <Result r={action.data} onReport={() => toReport(action.data)} />}
      {compare.data && (
        <Panel title="GA against PSO" description="Same problem and seed. Lower objective is better.">
          <LineChart label="GA vs PSO convergence" yFormat={v => fmt(v, 3)} series={compare.data.map((r, k) => ({ name: r.algorithm.toUpperCase(), color: k ? 'var(--color-glacier)' : 'var(--color-gold)', points: r.convergence.map((v, i) => ({ x: String(i), y: v })) }))} />
          <Table columns={['Solver', 'Objective', 'Exposure proxy', 'Utilisation proxy', 'Runtime']} rows={compare.data.map(r => [r.algorithm.toUpperCase(), fmt(r.candidate.objective, 5), fmt(r.candidate.exposure_proxy, 4), fmt(r.candidate.utilization_proxy, 4), `${fmt(r.runtime_seconds * 1000, 0)} ms`])} />
          <div className="mt-3 flex gap-3">{compare.data.map(r => <Button key={r.algorithm} variant="secondary" onClick={() => toReport(r)}>Use {r.algorithm.toUpperCase()} in report</Button>)}</div>
        </Panel>
      )}

      <InterventionPlanner />
    </Page>
  );
}
