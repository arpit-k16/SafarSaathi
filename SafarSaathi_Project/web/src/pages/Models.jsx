import React from 'react';
import { api, fmt } from '../api.js';
import { useQuery } from '../hooks.js';
import { Notes, Page, Panel, Pill, Query, Raw, Table, humanize, qualityTone } from '../components/ui.jsx';

const USED_ON = {
  'review classification': ['reviews', 'Review insights'],
  tourism_demand_forecaster: ['tourism', 'Tourism demand'],
  tourism_monthly_fta_forecaster: ['tourism', 'Tourism demand'],
  flood_segmentation_model: ['flood', 'Flood segmentation'],
  north_indian_cyclone_count_forecaster: ['hazards', 'Cyclone archive'],
  india_pm25_exposure_forecaster: ['environment', 'Environment and pressure'],
};

function flatten(obj, prefix = '', depth = 0, out = []) {
  if (!obj || typeof obj !== 'object' || depth > 3) return out;
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix} › ${k}` : k;
    if (typeof v === 'number' && Number.isFinite(v)) out.push([key, v]);
    else if (v && typeof v === 'object' && !Array.isArray(v)) flatten(v, key, depth + 1, out);
  }
  return out;
}

function Detail({ id }) {
  const q = useQuery(`model:${id}`, () => api.model(id));
  return (
    <Query q={q}>{m => {
      const metrics = flatten(m.metrics?.test ? { test: m.metrics.test } : m.metrics?.methods ? { [m.metrics.selected_method]: m.metrics.methods[m.metrics.selected_method] } : m.metrics).slice(0, 60);
      const facts = [
        ['Task', m.task], ['Type', m.task_type], ['Version', m.model_version || m.model_id], ['Trained', m.trained_at && new Date(m.trained_at).toLocaleString('en-IN')],
        ['Method', m.method || m.metrics?.selected_method || m.metrics?.selected_method], ['Target', m.target_definition], ['Units', m.units],
        ['Latest observation', m.latest_observed_date || m.latest_observed_year], ['Training rows', m.train_rows], ['Test rows', m.test_rows],
      ].filter(([, v]) => v !== undefined && v !== null && v !== '');
      const [page, label] = USED_ON[m.model_id] || USED_ON[m.task] || [];
      return (
        <Panel title={m.model_id} description={m.task} aside={<div className="flex gap-2">{m.quality_status && <Pill tone={qualityTone(m.quality_status)}>{humanize(m.quality_status)}</Pill>}{page && <a className="text-sm font-semibold text-gold hover:underline" href={`#/${page}`}>Use on {label}</a>}</div>}>
          <Table columns={['Property', 'Value']} rows={facts.map(([k, v]) => [k, String(v)])} />
          {metrics.length > 0 && (
            <>
              <h3 className="mb-2 mt-6 text-sm font-semibold text-snow">Recorded evaluation metrics</h3>
              <Table dense columns={['Metric', 'Value']} rows={metrics.map(([k, v]) => [<span className="font-mono text-xs">{k}</span>, fmt(v, 4)])} />
            </>
          )}
          {m.feature_schema && <Raw data={m.feature_schema} label="Feature schema" />}
          {m.split && <Raw data={m.split} label="Train / validation / test split" />}
          {m.dataset_provenance && <Raw data={m.dataset_provenance} label="Dataset provenance" />}
          <Notes items={m.limitations} />
          <Raw data={m} label="Complete registry entry" />
        </Panel>
      );
    }}</Query>
  );
}

export default function Models({ route }) {
  const models = useQuery('models', api.models);
  const caps = useQuery('capabilities', api.capabilities);
  const rel = useQuery('release', api.release);
  return (
    <Page title="Model center" intro="Every model in the backend registry, with its recorded evaluation and scope. Metrics come from stored held-out evaluations; opening a model does not re-run them.">
      <Query q={models}>{list => (
        <Panel title={`${list.length} registered models`}>
          <Table columns={['Model', 'Task', 'Status', 'Trained']} rows={list.map(m => [
            <a href={`#/models/${encodeURIComponent(m.model_id)}`} className={`font-medium hover:underline ${route.param === m.model_id ? 'text-gold' : 'text-snow'}`}>{m.model_id}</a>,
            m.task, <Pill tone={qualityTone(m.quality_status)}>{humanize(m.quality_status)}</Pill>, m.trained_at ? new Date(m.trained_at).toLocaleDateString('en-IN', { dateStyle: 'medium' }) : '—',
          ])} />
        </Panel>
      )}</Query>
      <Query q={rel}>{r => (
        <Panel title={`Release ${r.release}: ${r.passed} of ${r.total} models passed the gate`} description={r.definition}
          aside={<Pill tone="ok">Frozen {new Date(r.frozen_utc).toLocaleDateString('en-IN', { dateStyle: 'medium' })}</Pill>}>
          <Table dense columns={['Model', 'Artifact checksum and reload', 'Held-out test vs naive baseline', 'Limitations documented', 'Release']} rows={r.models.map(m => {
            const g = m.gates.G2_beats_or_matches_naive_baseline;
            const num = v => (Math.abs(v) >= 1000 ? Math.round(v).toLocaleString('en-IN') : Number(v).toFixed(3));
            return [m.model_id, m.gates.G1_artifact_integrity ? 'Pass' : 'Fail',
              <span>{g.passed ? 'Pass' : 'Fail'}: {g.metric} {num(g.model)} vs {num(g.baseline)} ({g.baseline_name}){g.baseline_model ? '. The saved model is the baseline method itself.' : ''}{g.note && !g.baseline_model ? ` ${g.note}` : ''}</span>,
              m.gates.G3_limitations_documented ? 'Pass' : 'Fail', <Pill tone={m.release ? 'ok' : 'warn'}>{m.release ? 'Final v1.0' : humanize(m.status)}</Pill>];
          })} />
        </Panel>
      )}</Query>
      {route.param && <Detail key={route.param} id={decodeURIComponent(route.param)} />}
      <Query q={caps}>{list => (
        <Panel title="Capability readiness" description="Each parent capability, whether its data supports training, and what is actually served.">
          <Table columns={['Capability', 'Data readiness', 'Implementation', 'Inference', 'Reason']} rows={list.map(c => [
            c.served_as ? <a href={`#/${c.served_as.page}`} className="text-gold hover:underline">{c.name}</a> : c.name,
            c.served_as ? 'Indicators ready' : humanize(c.dataset_readiness),
            c.served_as ? <Pill tone="ok" title={c.served_as.method}>{c.served_as.label}</Pill> : <Pill tone={qualityTone(c.implementation_status)}>{humanize(c.implementation_status)}</Pill>,
            c.inference_available ? 'Yes' : c.served_as ? `Yes, ${c.served_as.how}` : c.scoped_forecast?.inference_available ? 'Scoped only' : 'No',
            c.served_as ? <span className="text-mist">{c.served_as.reason} <span className="text-mist/70">{c.served_as.learned_model}</span></span> : <span className="text-mist">{c.reason}</span>,
          ])} />
        </Panel>
      )}</Query>
    </Page>
  );
}
