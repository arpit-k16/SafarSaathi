import React, { useState } from 'react';
import { API_BASE, api, request } from '../api.js';
import { useQuery } from '../hooks.js';
import { Button, Field, Page, Panel, Pill, Query, Raw, Select, Table, inputClass } from '../components/ui.jsx';

const ENDPOINTS = [
  ['GET', '/health'], ['GET', '/models'], ['GET', '/models/tourism_demand_forecaster'], ['GET', '/capabilities'], ['GET', '/system/summary'],
  ['GET', '/integration/status'], ['GET', '/deployment/status'], ['GET', '/research/status'], ['GET', '/tourism/history'],
  ['GET', '/destinations'], ['GET', '/destinations/kedarnath'], ['GET', '/destinations/kedarnath/climate'], ['GET', '/map/layers'],
  ['GET', '/satellite/metadata'], ['GET', '/datasets?offset=0&limit=5'], ['GET', '/stress/indicator-metadata'], ['GET', '/optimization/metadata'],
  ['POST', '/tourism/forecast', { destination: 'IND', horizon: 3 }], ['POST', '/tourism/monthly-forecast', { destination: 'IND', horizon: 6 }],
  ['POST', '/disaster/cyclone-count', { geography: 'NI', horizon: 12 }], ['POST', '/environment/pm25-forecast', { geography: 'IND', horizon: 1 }],
  ['POST', '/stress/indicators', { geography: 'Uttarakhand', year: 2024 }], ['POST', '/reviews/classify', { model_id: 'nlp-20261024T182952Z', reviews: ['Great stay near the river.'] }],
  ['POST', '/scenarios/simulate', { baseline_visitors: 100, capacity: 120, demand_change_percent: 50, available_capacity_percent: 50 }],
  ['POST', '/optimization/allocate', { problem: { demand: 100, exposure_tradeoff: 0.5, destinations: [{ id: 'A', capacity: 80, accessibility: 1, road_capacity: 80, resource_capacity: 80, exposure_weight: 0.7 }, { id: 'B', capacity: 60, accessibility: 1, road_capacity: 60, resource_capacity: 60, exposure_weight: 0.2 }] }, algorithm: 'pso', seed: 1, population: 16, iterations: 20 }],
  ['POST', '/optimization/solve', {}], ['POST', '/reports/generate', {}], ['POST', '/disaster/predict', {}], ['POST', '/stress/predict', {}],
  ['POST', '/flood/segment', 'Use the Flood segmentation page: the 128 × 128 × 2 tile is too large to edit here.'],
];

function Console() {
  const [index, setIndex] = useState(0);
  const [method, path, sample] = ENDPOINTS[index];
  const [target, setTarget] = useState(path);
  const [body, setBody] = useState('');
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const pick = i => { const [, p, s] = ENDPOINTS[i]; setIndex(i); setTarget(p); setBody(s === undefined ? '' : typeof s === 'string' ? s : JSON.stringify(s, null, 2)); setResult(null); };
  const send = async () => {
    setBusy(true); const started = performance.now();
    try {
      const payload = method === 'POST' ? JSON.parse(body || '{}') : undefined;
      const data = await request(target, { method, body: payload });
      setResult({ ok: true, ms: performance.now() - started, data });
    } catch (e) {
      setResult({ ok: false, ms: performance.now() - started, status: e.status, data: e.body ?? { detail: e.message } });
    } finally { setBusy(false); }
  };
  return (
    <Panel title="API console" description={`Send any request to ${API_BASE}. Responses are shown exactly as returned.`}>
      <div className="grid gap-4 md:grid-cols-[320px_1fr]">
        <Field label="Endpoint"><Select value={index} onChange={e => pick(Number(e.target.value))}>{ENDPOINTS.map(([m, p], i) => <option key={i} value={i}>{m} {p}</option>)}</Select></Field>
        <Field label="Path"><input className={`${inputClass} font-mono`} value={target} onChange={e => setTarget(e.target.value)} /></Field>
      </div>
      {method === 'POST' && <Field label="JSON body" className="mt-4"><textarea className={`${inputClass} min-h-36 font-mono text-xs`} value={body} onChange={e => setBody(e.target.value)} /></Field>}
      <Button className="mt-4" onClick={send} disabled={busy || path === '/flood/segment'}>{busy ? 'Sending…' : `Send ${method}`}</Button>
      {result && (
        <div className="mt-4">
          <div className="flex gap-2"><Pill tone={result.ok ? 'ok' : 'off'}>{result.ok ? '200 OK' : `Error ${result.status ?? ''}`}</Pill><Pill>{Math.round(result.ms)} ms</Pill></div>
          <pre className="scroll-thin mt-3 max-h-[28rem] overflow-auto rounded-lg border border-line bg-ink p-3 font-mono text-xs text-mist">{JSON.stringify(result.data, null, 2)}</pre>
        </div>
      )}
    </Panel>
  );
}

export default function System() {
  const health = useQuery('health', api.health);
  const deploy = useQuery('deployment', api.deploymentStatus);
  const integration = useQuery('integration', api.integrationStatus);
  const summary = useQuery('summary', api.systemSummary);
  return (
    <Page title="System and API" intro="Backend health, where each data source is coming from on this server, and a console for calling any endpoint directly.">
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Backend">
          <Query q={health}>{h => <Table columns={['Property', 'Value']} rows={[['Status', <Pill tone="ok">{h.status}</Pill>], ['Service', h.service], ['API schema', h.api_schema_version], ['Saved models', h.trained_models], ['Training on request', h.training_on_request ? 'Yes' : 'No'], ['Base URL', API_BASE]]} />}</Query>
        </Panel>
        <Panel title="Data sources on this server" description="Local files are used when present; otherwise the checksum-verified build snapshot.">
          <Query q={deploy}>{d => (
            <>
              <Table columns={['Source', 'Local files present']} rows={Object.entries(d.live_sources).map(([k, v]) => [k.replaceAll('_', ' '), v ? <Pill tone="ok">Yes</Pill> : <Pill>No</Pill>])} />
              <p className="mt-3 text-sm text-mist">{d.snapshot.available ? `Snapshot from ${new Date(d.snapshot.generated_utc).toLocaleString('en-IN')}, sections: ${d.snapshot.sections.join(', ')}. Mode: ${d.snapshot.mode}.` : 'No deployment snapshot is installed.'}</p>
              {d.snapshot.omitted && Object.keys(d.snapshot.omitted).length > 0 && <p className="mt-2 text-sm text-gold">Missing from snapshot: {Object.keys(d.snapshot.omitted).join(', ')}. Run <code className="font-mono">python -m safarsaathi_ml.cli build-snapshot</code> on the machine with the full dataset collection.</p>}
            </>
          )}</Query>
        </Panel>
      </div>
      <Query q={integration}>{i => i.web_console && (
        <Panel title="Endpoint coverage" description="Every backend route and the page of this console that uses it.">
          <Table dense columns={['Page', 'Endpoints']} rows={Object.entries(i.web_console).map(([page, routes]) => [<a className="text-gold hover:underline" href={`#/${page}`}>{page}</a>, <span className="font-mono text-xs">{routes.join('  ')}</span>])} />
        </Panel>
      )}</Query>
      <Console />
      <Query q={summary}>{s => s.evaluation && (
        <Panel title="Stored evaluation audit" description="Post-hoc held-out replay recorded for the review classifier."><Raw data={s.evaluation} label="Evaluation audit JSON" /><p className="mt-2 text-sm text-mist">{s.operational_data_note}</p></Panel>
      )}</Query>
    </Page>
  );
}
