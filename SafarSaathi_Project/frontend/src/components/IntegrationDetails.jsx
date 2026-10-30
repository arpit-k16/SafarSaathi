import React, { useEffect, useState } from 'react';
import { api } from '../services/api/resources.js';
import { number } from '../services/api/adapters.js';
import { useApiAction } from '../hooks/useApi.js';
import ApiState, { DataTable, Limitations } from './ApiState.jsx';

const inputClass = 'bg-surface-container border border-white/10 rounded px-3 py-2 text-white text-xs font-mono max-w-full';
const buttonClass = 'px-3 py-2 rounded bg-primary/20 border border-primary/40 text-primary text-xs font-mono hover:bg-primary/30 transition-colors disabled:opacity-40';

export function ScenarioDetails({ result }) {
  if (!result) return <p className="text-slate-400">No submitted scenario. Run the What-If Simulator first.</p>;
  return <div data-testid="scenario-result">
    <p className="text-primary mb-2">{result.status} · {result.model_version} · not a prediction</p>
    <DataTable columns={['Outcome', 'Baseline', 'Scenario']} rows={[
      ['Visitors', number(result.baseline.visitors), number(result.scenario.visitors)],
      ['Available capacity', number(result.baseline.available_capacity), number(result.scenario.available_capacity)],
      ['Served visitors', number(result.baseline.served_visitors), number(result.scenario.served_visitors)],
      ['Unserved visitors', number(result.baseline.unserved_visitors), number(result.scenario.unserved_visitors)],
      ['Demand / capacity', result.baseline.utilization_ratio ?? 'Undefined (zero capacity)', result.scenario.utilization_ratio ?? 'Undefined (zero capacity)'],
    ]} />
    <p className="mt-2">Units: {result.units}. Affected locations: not modeled.</p>
    <DataTable columns={['Submitted parameter', 'Value']} rows={Object.entries(result.parameters).map(([key, value]) => [key, number(value)])} />
    <Limitations items={[...result.assumptions, ...result.limitations]} />
  </div>;
}

function ForecastTool({ kind }) {
  const [horizon, setHorizon] = useState(1);
  const action = useApiAction();
  const max = { annual: 3, monthly: 6, cyclone: 12, pm25: 1 }[kind];
  const run = () => action.run(() => ({ annual: api.annualForecast, monthly: api.monthlyForecast,
    cyclone: api.cycloneForecast, pm25: api.pm25Forecast })[kind](horizon));
  return <div className="mt-4 pt-3 border-t border-white/10">
    <form onSubmit={event => { event.preventDefault(); run(); }} className="flex items-center flex-wrap gap-2">
      <label className="text-slate-300">{kind.toUpperCase()} historical forecast · horizon <select aria-label={`${kind} forecast horizon`} className={inputClass} value={horizon} onChange={e => setHorizon(Number(e.target.value))}>
        {Array.from({ length: max }, (_, i) => <option key={i + 1}>{i + 1}</option>)}
      </select></label>
      <button className={buttonClass} disabled={action.loading}>Run {kind} forecast</button>
    </form>
    <ApiState {...action} />
    {action.data && <div data-testid={`${kind}-forecast-result`}>
      <p className="my-2 text-primary">{action.data.status} · {action.data.model_id} · origin {action.data.forecast_origin ?? action.data.forecast_origin_year}</p>
      <p>Scope: {action.data.geography ?? action.data.destination}. Units: {action.data.units}</p>
      <DataTable columns={['Target period', 'Horizon', 'Model estimate']} rows={action.data.forecasts.map(r => [r.date ?? r.year, r.horizon, number(r.prediction)])} />
      <Limitations items={action.data.limitations} />
    </div>}
  </div>;
}

function HistoricalIndicators({ metadata }) {
  const [geography, setGeography] = useState('IND');
  const years = metadata.geography_years?.[geography] || [];
  const [year, setYear] = useState('');
  const action = useApiAction();
  const selectedYear = years.includes(Number(year)) ? Number(year) : years.at(-1);
  return <div>
    <p className="text-amber-400 mb-3">STRESS MODEL NOT IMPLEMENTED — historical input indicators only.</p>
    <form className="flex flex-wrap items-center gap-2" onSubmit={e => { e.preventDefault(); action.run(() => api.indicators(geography, selectedYear)); }}>
      <label>Geography <select aria-label="Indicator geography" className={inputClass} value={geography} onChange={e => { setGeography(e.target.value); setYear(''); }}>
        {metadata.geographies.map(g => <option key={g}>{g}</option>)}
      </select></label>
      <label>Year <select aria-label="Indicator year" className={inputClass} value={selectedYear ?? ''} onChange={e => setYear(e.target.value)}>
        {years.map(y => <option key={y}>{y}</option>)}
      </select></label>
      <button className={buttonClass} disabled={action.loading || !selectedYear}>Load historical indicators</button>
    </form>
    <ApiState {...action} />
    {action.data && <><DataTable columns={['Historical field', 'Source value']} rows={Object.entries(action.data.observation).map(([k, v]) => [k, v === null ? 'Not observed / not available' : String(v)])} /><Limitations items={action.data.limitations} /></>}
    <ForecastTool kind="pm25" />
  </div>;
}

function ModelDetails({ data }) {
  const detail = useApiAction();
  const availability = model => {
    for (const cap of data.capabilities) {
      if (cap.model_id === model.model_id) return cap.inference_available ? 'Experimental inference available' : cap.status;
      if (cap.monthly_fta?.model_id === model.model_id) return cap.monthly_fta.inference_available ? 'Experimental inference available' : 'Unavailable';
      if (cap.scoped_forecast?.model_id === model.model_id) return cap.scoped_forecast.inference_available ? 'Scoped experimental inference' : 'Unavailable';
    }
    return model.task === 'review classification' ? 'Persisted review pipeline; run on Insights page' : 'Not reported';
  };
  return <>
    <DataTable columns={['Model', 'Version', 'Recorded status', 'Inference scope']} rows={data.models.map(m => [m.model_id, m.model_version, m.quality_status, availability(m)])} />
    <div className="flex flex-wrap gap-2 mt-3">{data.models.map(m => <button key={m.model_id} className={buttonClass} disabled={detail.loading} onClick={() => detail.run(() => api.model(m.model_id))}>Inspect {m.model_id}</button>)}</div>
    <ApiState {...detail} />
    {detail.data && <div data-testid="model-metadata" className="mt-3">
      <p className="text-primary">{detail.data.model_id} · recorded metadata, not a new validation run</p>
      <p>Input: {detail.data.task === 'review classification' ? 'model_id + 1..100 non-empty review strings; saved TF-IDF preprocessing' : JSON.stringify(detail.data.feature_schema ?? 'Input schema not recorded')}</p>
      <p>Output / target: {detail.data.target_definition ?? detail.data.task}</p>
      <details><summary className="cursor-pointer text-primary py-2">Recorded evaluation metrics</summary><pre className="whitespace-pre-wrap break-all text-[10px] max-h-80 overflow-auto">{JSON.stringify(detail.data.metrics, null, 2)}</pre></details>
      <Limitations items={detail.data.limitations} />
    </div>}
    <Limitations items={['Successful artifact loading does not establish operational accuracy. Historical models are experimental; none is a local emergency warning.']} />
  </>;
}

function ReviewTool({ models }) {
  const available = models.filter(m => m.task === 'review classification');
  const [text, setText] = useState('');
  const action = useApiAction();
  if (!available.length) return <p className="text-amber-400">NLP MODEL NOT CONNECTED.</p>;
  return <>
    <p className="mb-3">{available[0].model_id} · source-domain binary labels; no verified local community corpus.</p>
    <form onSubmit={e => { e.preventDefault(); action.run(() => api.classify(available[0].model_id, [text.trim()])); }}>
      <label htmlFor="review-input">Review to classify (submitted only when you run inference)</label>
      <textarea id="review-input" required maxLength={20000} rows={4} className={`${inputClass} w-full mt-2`} value={text} onChange={e => setText(e.target.value)} />
      <button className={`${buttonClass} mt-2`} disabled={action.loading || !text.trim()}>Classify review</button>
    </form>
    <ApiState {...action} />
    {action.data && <div data-testid="review-result" className="mt-3"><p className="text-primary">Model response: {action.data.predictions.join(', ')}</p><p>{action.data.model_id} · {action.data.model_version}</p><Limitations items={action.data.limitations} /></div>}
  </>;
}

function SatelliteDetails({ data }) {
  const [file, setFile] = useState(null);
  const action = useApiAction();
  const infer = () => action.run(async () => {
    if (!file || file.size > 1000000) throw new Error('Select a supported STURM-preprocessed JSON tile of at most 1 MB.');
    const payload = JSON.parse(await file.text());
    return api.segment(payload);
  });
  return <>
    <DataTable columns={['Product / source', 'Acquisition from ID', 'Local files / bytes']} rows={data.scenes.map(s => [<span key={s.product_id}>{s.product_id}<br />{s.source ?? 'Source not recorded'}<br />{s.license ?? 'License not recorded'}</span>, s.acquisition_from_product_id, `${s.files} / ${number(s.size_bytes)}`])} />
    <Limitations items={data.limitations} />
    <details className="mt-4"><summary className="text-primary cursor-pointer">Experimental STURM tile segmentation</summary>
      <p className="my-2">Only a delivered 128×128×2 STURM-preprocessed JSON tile plus source metadata is accepted. Raw Sentinel scenes above are not interchangeable. This is not a flood warning.</p>
      <label>Preprocessed JSON tile <input className={inputClass} type="file" accept=".json,application/json" onChange={e => setFile(e.target.files?.[0] ?? null)} /></label>
      <button className={`${buttonClass} ml-2 mt-2`} onClick={infer} disabled={action.loading || !file}>Segment selected tile</button>
      <ApiState {...action} />
      {action.data && <div data-testid="segmentation-result"><p className="text-primary">{action.data.model_id} · mask {action.data.dimensions.join('×')} · threshold {action.data.threshold}</p>
        <p>Reference-positive pixels: {number(action.data.mask.flat().reduce((sum, v) => sum + v, 0))}. Confidence scores are uncalibrated.</p>
        <svg role="img" aria-label="Returned reference-positive water mask" viewBox="0 0 128 128" className="w-48 h-48 bg-black my-2" shapeRendering="crispEdges"><path fill="#f2ca50" d={action.data.mask.flatMap((row, y) => row.map((v, x) => v ? `M${x} ${y}h1v1h-1z` : '')).join('')} /></svg>
        <Limitations items={action.data.limitations} /></div>}
    </details>
  </>;
}

function ReportTool({ lastScenario }) {
  const action = useApiAction();
  const [include, setInclude] = useState(false);
  const [url, setUrl] = useState(null);
  useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);
  const generate = async () => {
    setUrl(null);
    const data = await action.run(() => api.report(include ? lastScenario : null));
    if (data) setUrl(URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })));
  };
  return <>
    <p className="text-amber-400 mb-3">PDF EXPORT COMING SOON. JSON reports use actual registry/file stats and recomputed scenario inputs.</p>
    <label className="block mb-3"><input type="checkbox" checked={include} disabled={!lastScenario} onChange={e => setInclude(e.target.checked)} /> Include last submitted session scenario {lastScenario ? '' : '(none yet)'}</label>
    <button className={buttonClass} disabled={action.loading} onClick={generate}>Generate JSON report</button>
    <ApiState {...action} />
    {action.data && <div data-testid="report-result" className="mt-3"><p className="text-primary">{action.data.report_type} · {action.data.generated_utc}</p>
      {url && <a className="text-primary underline block my-2" href={url} download="safarsaathi-report.json">Download JSON report</a>}
      <DataTable columns={['Source', 'Report value']} rows={[
        ['Registered models', action.data.models.length], ['Catalog source groups', Object.keys(action.data.dataset_inventory).length],
        ['Scenario included', action.data.scenario ? 'Recomputed hypothetical capacity inputs' : 'No scenario'],
        ...action.data.sources.map(s => ['Source', s]),
      ]} />
      <Limitations items={action.data.limitations} /></div>}
  </>;
}

function OptimizerBoundary() {
  const action = useApiAction();
  return <><p className="text-amber-400 mb-3">OPTIMIZATION ENGINE NOT AVAILABLE. No GA/PSO execution, convergence or optimal intervention is claimed.</p>
    <button className={buttonClass} disabled={action.loading} onClick={() => action.run(api.optimizationAvailability)}>Check optimization availability</button><ApiState {...action} /></>;
}

export default function IntegrationDetails({ tab, data, lastScenario, page, setPage }) {
  if (tab === 'simulation-results') return <ScenarioDetails result={lastScenario} />;
  if (tab.includes('optim')) return <OptimizerBoundary />;
  if (tab === 'notifications' || tab === 'settings') return <p className="text-amber-400">NOT IMPLEMENTED — no live notification feed or persisted settings service is configured.</p>;
  if (!data) return null;
  if (tab === 'tourism-intelligence') return <>
    {data.series.map(series => <details key={series.frequency} open={series.frequency === 'monthly'}><summary className="text-primary cursor-pointer py-2">{series.frequency.toUpperCase()} history · {series.observations.length} observations · {series.units}</summary>
      <div className="max-h-72 overflow-auto"><DataTable columns={['Observed period', 'Arrivals']} rows={series.observations.map(r => [r.date ?? r.year, number(r.arrivals)])} /></div>
      <p className="text-slate-400">Source: {series.frequency === 'annual' ? 'World Bank ST.INT.ARVL / UN Tourism' : 'Ministry of Tourism, India · FTA excludes NRI'} · national historical observations</p>
    </details>)}<Limitations items={data.limitations} /><ForecastTool kind="annual" /><ForecastTool kind="monthly" />
  </>;
  if (tab === 'crowd-destination-stress') return <HistoricalIndicators metadata={data} />;
  if (tab === 'risk-resilience') return <><p className="text-amber-400">No current hazard observations or geographic exposure feed. The forecast below concerns historical NI-basin archive counts, not local risk or alerts.</p>
    <DataTable columns={['Capability', 'Availability']} rows={data.map(c => [c.name, c.status])} /><ForecastTool kind="cyclone" /></>;
  if (tab === 'ai-model-center') return <ModelDetails data={data} />;
  if (tab === 'tourist-community-insights') return <ReviewTool models={data} />;
  if (tab === 'satellite-intelligence') return <SatelliteDetails data={data} />;
  if (tab === 'reports-briefs') return <ReportTool lastScenario={lastScenario} />;
  if (tab === 'live-geospatial-map') return <><DataTable columns={['Archived location', 'Longitude', 'Latitude', 'Coverage']} rows={data.features.map(f => [f.properties.name, f.geometry.coordinates[0], f.geometry.coordinates[1], `${f.properties.coverage_start} – ${f.properties.coverage_end}`])} /><Limitations items={[data.coordinate_metadata, ...data.limitations]} /></>;
  if (tab === 'data-hub') return <><DataTable columns={['Dataset / file', 'Format / bytes', 'Coverage', 'Source / license', 'Availability']} rows={data.files.map(f => [<span key={f.relative_path}>{f.root}/{f.relative_path}</span>, `${f.format ?? 'unknown'} / ${number(f.size_bytes)}`, `${f.coverage_start ?? 'Unknown'} – ${f.coverage_end ?? 'Unknown'} · ${f.geographic_coverage ?? 'Unknown geography'}`, <span key={`${f.root}/${f.relative_path}`}>{f.source ?? 'Not recorded'}<br />{f.license ?? 'License not recorded'}</span>, 'LOCAL FILE · not an ingestion/connection test'])} />
    <div className="flex items-center gap-3 mt-3"><button className={buttonClass} disabled={!page} onClick={() => setPage(page - 1)}>Previous files</button><span>Files {data.offset + 1}–{data.offset + data.files.length} of {number(data.total)}</span><button className={buttonClass} disabled={data.offset + data.files.length >= data.total} onClick={() => setPage(page + 1)}>Next files</button></div><Limitations items={data.limitations} /></>;
  return <><DataTable columns={['Backend field', 'Value']} rows={Object.entries(data).map(([key, value]) => [key, String(value)])} /><p className="mt-3 text-slate-400">Local React/Vite + Python HTTP API. No security certification, live synchronization or external failover is asserted.</p></>;
}
