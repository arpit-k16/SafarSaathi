import React, { useState } from 'react';
import { api, fmt } from '../api.js';
import { useAction } from '../hooks.js';
import { Button, ErrorNotice, Field, Grid, Input, Notes, Panel, Pill, Raw, Segmented, Stat, Table } from '../components/ui.jsx';
import { LineChart } from '../components/charts.jsx';
import Explain from '../components/Explain.jsx';

// Planning assumptions (₹ lakh, % of annual visitors). Mirrors the backend defaults; every value is editable.
const DEFAULTS = [
  ['ked-badri', 'shift', 'kedarnath', 'badrinath', 15, 40, 'Promote Badrinath slots to shift Kedarnath pilgrims'],
  ['ked-permit', 'cap', 'kedarnath', null, 10, 15, 'Daily permit cap at Kedarnath'],
  ['tehri-cap', 'cap', 'tehri', null, 15, 20, 'Lake-zone entry management at Tehri'],
  ['mussoorie-kausani', 'shift', 'mussoorie', 'kausani', 15, 25, 'Package tours from Mussoorie to Kausani'],
  ['nainital-ranikhet', 'shift', 'nainital', 'ranikhet', 20, 15, 'Shuttle and stay incentives, Nainital to Ranikhet'],
  ['haridwar-cap', 'cap', 'haridwar', null, 5, 60, 'Crowd management at Haridwar ghats'],
  ['dehradun-cap', 'cap', 'dehradun', null, 10, 35, 'Peak-weekend traffic restrictions in Dehradun'],
  ['gangotri-uttarkashi', 'shift', 'gangotri', 'uttarkashi', 20, 15, 'Stage Gangotri visitors through Uttarkashi'],
  ['auli-joshimath', 'shift', 'auli', 'joshimath', 20, 10, 'Day-trip model: Auli stays moved to Joshimath'],
  ['rishikesh-kotdwar', 'shift', 'rishikesh', 'kotdwar', 10, 20, 'Promote Kotdwar circuits from Rishikesh'],
].map(([id, type, from, to, pct, cost, label]) => ({ id, type, from, ...(to ? { to } : {}), pct, cost, label, on: true }));

export default function InterventionPlanner() {
  const [items, setItems] = useState(DEFAULTS);
  const [budget, setBudget] = useState(100);
  const [lam, setLam] = useState(2);
  const [algorithm, setAlgorithm] = useState('ga');
  const action = useAction();
  const set = (i, k, v) => setItems(items.map((x, j) => (j === i ? { ...x, [k]: v } : x)));
  const run = () => action.run(() => api.interventions({
    budget, lost_visit_weight: lam, algorithm,
    interventions: items.filter(x => x.on).map(({ on, ...rest }) => rest),
  }));
  const d = action.data;
  const label = id => items.find(x => x.id === id)?.label || id;
  return (
    <>
      <Panel title="Intervention planner" description="Choose which interventions to fund so that destinations fall below the high-stress threshold, without turning away too many visitors. Each candidate plan is pushed through the digital twin and scored with the Destination Stress Index. GA or PSO searches the plans; the result is checked against doing nothing, a greedy rule and the exhaustive optimum.">
        <div className="mb-4 grid gap-4 md:grid-cols-3">
          <Field label="Budget (₹ lakh, assumed)" hint="Total cost of funded interventions must fit"><Input type="number" min={0} max={10000} value={budget} onChange={e => setBudget(Number(e.target.value))} /></Field>
          <Field label={<span className="flex justify-between"><span>Weight on lost visits</span><span className="num text-gold">{lam}</span></span>} hint="Higher values penalise caps that turn visitors away">
            <input type="range" min={0} max={10} step={0.5} value={lam} onChange={e => setLam(Number(e.target.value))} className="accent-[#e8bd4f]" />
          </Field>
          <Field label="Solver"><Segmented label="Solver" value={algorithm} onChange={setAlgorithm} options={[{ value: 'ga', label: 'Genetic (GA)' }, { value: 'pso', label: 'Particle swarm (PSO)' }]} /></Field>
        </div>
        <Table dense columns={['Use', 'Intervention', 'Type', '% of visitors', 'Cost (₹ lakh)']} rows={items.map((x, i) => [
          <input type="checkbox" checked={x.on} onChange={e => set(i, 'on', e.target.checked)} aria-label={`Include ${x.label}`} className="accent-[#e8bd4f]" />,
          x.label, <Pill tone={x.type === 'cap' ? 'warn' : 'info'}>{x.type === 'cap' ? 'cap' : 'shift'}</Pill>,
          <Input type="number" min={1} max={50} value={x.pct} onChange={e => set(i, 'pct', Number(e.target.value))} />,
          <Input type="number" min={0} max={5000} value={x.cost} onChange={e => set(i, 'cost', Number(e.target.value))} />,
        ])} />
        <p className="mt-2 text-xs text-mist">Costs and effects are planning assumptions, not verified data. Shifts move visitors between destinations; caps turn them away.</p>
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={run} disabled={action.loading || !items.some(x => x.on)}>{action.loading ? 'Searching plans…' : 'Find the best plan'}</Button>
          <ErrorNotice error={action.error} />
        </div>
      </Panel>
      {d && (
        <>
          <Grid cols={4}>
            <Stat label="Plan objective" value={fmt(d.plan.objective, 3)} note={`Do nothing: ${fmt(d.baselines.do_nothing.objective, 3)}`} tone="good" />
            <Stat label="Cost" value={`₹${fmt(d.plan.cost, 0)} lakh`} note={`Budget ₹${fmt(d.budget, 0)} lakh`} />
            <Stat label="Visitors turned away" value={`${fmt(d.plan.lost_visit_share * 100, 2)}%`} note="of annual visitors" tone={d.plan.lost_visit_share > 0 ? 'hazard' : undefined} />
            <Stat label="Gap to the true optimum" value={d.optimality_gap == null ? '—' : fmt(d.optimality_gap, 4)} note={d.optimality_gap === 0 ? `${d.algorithm.toUpperCase()} found the optimum` : 'Exhaustive check'} tone={d.optimality_gap === 0 ? 'good' : undefined} />
          </Grid>
          <Panel title={`Recommended plan (${d.algorithm.toUpperCase()}, ${d.year})`} description={d.objective_definition}>
            {d.plan.selected.length ? (
              <ul className="mb-4 list-disc space-y-1 pl-5 text-sm">{d.plan.selected.map(id => <li key={id}>{label(id)}</li>)}</ul>
            ) : <p className="mb-4 text-sm text-mist">No funded intervention improves on doing nothing under these assumptions.</p>}
            <Table dense columns={['Destination', 'Stress index before', 'After', 'Change']} rows={d.plan.changes.map(c => [c.name, fmt(c.before, 3), fmt(c.after, 3), `${c.after - c.before > 0 ? '+' : ''}${fmt(c.after - c.before, 3)}`])}
              empty="The plan changes no destination's index." />
            <h3 className="mt-6 font-display font-semibold">Against the baselines</h3>
            <Table dense columns={['Strategy', 'Interventions', 'Cost', 'Objective', 'Above threshold', 'Visitors lost']} rows={[
              ['Do nothing', '—', 0, d.baselines.do_nothing],
              ['Greedy: best benefit per rupee first', d.baselines.greedy_benefit_per_cost.selected.length, d.baselines.greedy_benefit_per_cost.cost, d.baselines.greedy_benefit_per_cost],
              ...(d.baselines.exhaustive_optimum ? [['Exhaustive search (true optimum)', d.baselines.exhaustive_optimum.selected.length, d.baselines.exhaustive_optimum.cost, d.baselines.exhaustive_optimum]] : []),
              [`${d.algorithm.toUpperCase()} plan`, d.plan.selected.length, d.plan.cost, d.plan],
            ].map(([name, n, cost, e]) => [name, n, `₹${fmt(cost, 0)} lakh`, fmt(e.objective, 4), e.destinations_above_threshold, `${fmt(e.lost_visit_share * 100, 2)}%`])} />
            <div className="mt-5"><LineChart label="Search convergence" yFormat={v => fmt(v, 3)} series={[{ name: `${d.algorithm.toUpperCase()} best objective`, color: 'var(--color-gold)', points: d.convergence.map((v, i) => ({ x: String(i), y: v })) }]} /></div>
          </Panel>
          <Explain title="Why this plan"
            rule="Each plan changes annual visitor numbers, the digital twin recomputes every destination's stress index, and the objective adds up how far destinations sit above the threshold plus a penalty for visitors turned away."
            baseline={d.plan.changes.some(c => c.after > c.before) ? 'Shifting visitors raises stress at the receiving destination, so shifts only help when the receiving place has spare headroom on the index.' : null}
            factors={d.plan.changes.map(c => ({ label: c.name, value: c.after - c.before }))}
            format={v => `${v > 0 ? '+' : ''}${fmt(v, 3)}`}
            uncertainty="Costs and effects are your assumptions. Results are simulated estimates, not observed outcomes."
            freshness={`UTDB visitors ${d.year}; NASA POWER climate ${d.year}`}
            provenance={[['Search', `${d.algorithm.toUpperCase()}, seed ${d.seed}, ${d.runtime_ms} ms`]]} />
          <Notes items={d.limitations} />
          <Raw data={d} />
        </>
      )}
    </>
  );
}
