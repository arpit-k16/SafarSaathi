import React, { useState } from 'react';
import { api, download, fmt } from '../api.js';
import { useAction, useSession } from '../hooks.js';
import { Button, ErrorNotice, Notes, Page, Panel, Pill, Raw, Table, humanize, qualityTone } from '../components/ui.jsx';

export default function Reports() {
  const session = useSession();
  const latest = session.scenarios[0];
  const [withScenario, setWithScenario] = useState(!!latest);
  const [withOpt, setWithOpt] = useState(!!session.optimization);
  const action = useAction();
  const generate = () => action.run(() => api.report({
    scenario: withScenario && latest ? latest.parameters : undefined,
    optimization: withOpt && session.optimization ? session.optimization : undefined,
  }));
  const r = action.data;
  const stamp = r ? r.generated_utc.slice(0, 19).replaceAll(':', '') : '';
  return (
    <Page title="Reports" intro="An evidence report the backend assembles itself: the model registry, the data inventory and, if you include them, a scenario and an optimisation that it recomputes from your inputs. Your browser never supplies the results."
      actions={r && <><Button variant="secondary" onClick={() => window.print()}>Print or save as PDF</Button><Button onClick={() => download(`safarsaathi-report-${stamp}.json`, r)}>Download JSON</Button></>}>
      <Panel title="Include in this report" className="no-print">
        <div className="flex flex-col gap-3 text-sm">
          <label className="flex items-start gap-3">
            <input type="checkbox" className="mt-1 accent-[var(--color-gold)]" checked={withScenario && !!latest} disabled={!latest} onChange={e => setWithScenario(e.target.checked)} />
            <span>Latest capacity scenario{latest ? ` — baseline ${fmt(latest.parameters.baseline_visitors, 0)}, demand ${latest.parameters.demand_change_percent}%, capacity ${latest.parameters.available_capacity_percent}% available` : <> — none yet. <a className="text-gold hover:underline" href="#/scenarios">Run a scenario</a></>}</span>
          </label>
          <label className="flex items-start gap-3">
            <input type="checkbox" className="mt-1 accent-[var(--color-gold)]" checked={withOpt && !!session.optimization} disabled={!session.optimization} onChange={e => setWithOpt(e.target.checked)} />
            <span>Allocation optimisation{session.optimization ? ` — ${session.optimization.algorithm.toUpperCase()}, ${session.optimization.problem.destinations.length} sites, seed ${session.optimization.seed}` : <> — none yet. <a className="text-gold hover:underline" href="#/optimizer">Run the optimizer</a></>}</span>
          </label>
          <div><Button onClick={generate} disabled={action.loading}>{action.loading ? 'Generating…' : 'Generate report'}</Button></div>
        </div>
        <div className="mt-4"><ErrorNotice error={action.error} retry={generate} /></div>
      </Panel>

      {r && (
        <article className="flex flex-col gap-6">
          <Panel title="SafarSaathi evidence report" description={`Generated ${new Date(r.generated_utc).toLocaleString('en-IN', { dateStyle: 'long', timeStyle: 'short' })} by the backend.`}>
            <h3 className="mb-2 text-sm font-semibold text-snow">Models in the registry</h3>
            <Table columns={['Model', 'Task', 'Status']} rows={r.models.map(m => [m.model_id, m.task, <Pill tone={qualityTone(m.quality_status)}>{humanize(m.quality_status)}</Pill>])} />
            <h3 className="mb-2 mt-6 text-sm font-semibold text-snow">Data inventory</h3>
            {r.dataset_inventory
              ? <Table dense columns={['Group', 'Files', 'Size (MB)']} rows={Object.entries(r.dataset_inventory).map(([k, g]) => [k, fmt(g.files, 0), fmt(g.size_bytes / 1048576, 1)])} />
              : <p className="text-sm text-gold">{r.dataset_inventory_note || 'Dataset inventory is not available on this server.'}</p>}
          </Panel>
          {r.scenario && (
            <Panel title="Capacity scenario (recomputed)">
              <Table columns={['', 'Baseline', 'Scenario']} rows={[['Demand', 'visitors'], ['Available capacity', 'available_capacity'], ['Served', 'served_visitors'], ['Not served', 'unserved_visitors']].map(([l, k]) => [l, fmt(r.scenario.baseline[k], 0), fmt(r.scenario.scenario[k], 0)])} />
              <Notes items={[...r.scenario.assumptions, ...r.scenario.limitations]} />
            </Panel>
          )}
          {r.optimization && (
            <Panel title={`Allocation optimisation, ${r.optimization.algorithm.toUpperCase()} (recomputed)`}>
              <Table columns={['Site', 'Effective capacity', 'Proportional', 'Candidate']} rows={r.optimization.allocations.map(a => [a.id, fmt(a.effective_capacity, 1), fmt(a.baseline, 1), fmt(a.candidate, 1)])} />
              <p className="mt-3 text-sm text-mist">Objective {fmt(r.optimization.baseline.objective, 4)} → {fmt(r.optimization.candidate.objective, 4)}. Not claimed to be globally optimal.</p>
              <Notes items={r.optimization.limitations} />
            </Panel>
          )}
          <Panel title="Sources and limitations">
            <ul className="list-disc pl-5 text-sm text-mist">{r.sources.map(s => <li key={s}>{s}</li>)}</ul>
            <Notes items={r.limitations} />
            <Raw data={r} />
          </Panel>
        </article>
      )}
    </Page>
  );
}
