import React, { useState } from 'react';
import { api, fmt, monthLabel } from '../api.js';
import { useAction, useQuery } from '../hooks.js';
import { Button, ErrorNotice, Field, Grid, Notes, Page, Panel, Pill, Query, Raw, Select, Stat, Table } from '../components/ui.jsx';
import { LineChart } from '../components/charts.jsx';

export function UnavailableModel({ title, call, cacheKey, served }) {
  const q = useQuery(cacheKey, call, { enabled: !served });
  const body = q.error?.body;
  if (served) {
    return (
      <Panel title={title} description={served.method}>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <Pill tone="ok">{served.label}</Pill>
          <span className="text-snow">{served.text}</span>
        </div>
        <div className="mt-3 flex flex-wrap gap-4 text-sm">{served.links.map(([href, label]) => <a key={href} href={href} className="font-semibold text-gold hover:underline">{label}</a>)}</div>
        <p className="mt-3 text-xs text-mist">A learned predictor stays switched off: {served.learned}</p>
      </Panel>
    );
  }
  return (
    <Panel title={title} tone="hazard" description="The backend reports this capability directly. It stays off until observed outcome labels exist, so no score is shown.">
      {q.loading && <p className="text-sm text-mist">Checking availability…</p>}
      {body && (
        <div className="text-sm">
          <Pill tone="off">{String(body.status || 'unavailable').replaceAll('_', ' ')}</Pill>
          <p className="mt-2 max-w-[75ch] text-mist">{body.detail}</p>
        </div>
      )}
      {q.error && !body && <ErrorNotice error={q.error} retry={q.retry} />}
      {q.data && <Raw data={q.data} />}
    </Panel>
  );
}

export default function Hazards() {
  const meta = useQuery('model:cyclone', () => api.model('north_indian_cyclone_count_forecaster'));
  const [horizon, setHorizon] = useState(12);
  const action = useAction();
  const run = () => action.run(() => api.cycloneForecast(horizon));
  return (
    <Page title="Cyclone archive" intro="A monthly count of tropical systems in the North Indian Ocean basin from the IBTrACS best-track archive. It describes seasonal rhythm in the archive; it is not a landfall warning for India.">
      <Query q={meta}>{m => {
        const method = m.metrics.selected_method;
        const test = m.metrics.methods[method].test;
        const preds = m.metrics.predictions[method].test;
        const peak = preds.reduce((a, b) => (b.actual > a.actual ? b : a));
        return (
          <>
            <Grid cols={4}>
              <Stat label="Selected method" value={method.replaceAll('_', ' ')} note={m.metrics.selection} />
              <Stat label="Test mean absolute error" value={`${fmt(test.MAE, 2)} systems`} note={`${test.n} held-out months`} />
              <Stat label="Mean Poisson deviance" value={fmt(test.mean_poisson_deviance, 2)} note="Lower is better" />
              <Stat label="Busiest test month" value={`${peak.actual} systems`} note={monthLabel(peak.date)} tone="hazard" />
            </Grid>
            <Panel title="How the model did on held-out years" description="Observed archive counts against the model's estimate for each test month. Seasonal shape is captured; individual busy months are not.">
              <LineChart label="Held-out cyclone counts" yFormat={v => fmt(v, 1)} zeroBased series={[
                { name: 'Archive count', color: 'var(--color-snow)', points: preds.map(p => ({ x: p.date, y: p.actual })) },
                { name: 'Model estimate', color: 'var(--color-glacier)', points: preds.map(p => ({ x: p.date, y: p.prediction })) },
              ]} />
            </Panel>
          </>
        );
      }}</Query>

      <Panel title="Forecast archive counts" description="Months are counted from the last archived month (December 2024), not from today.">
        <form className="flex flex-wrap items-end gap-3" onSubmit={e => { e.preventDefault(); run(); }}>
          <Field label="Months ahead" className="w-40">
            <Select value={horizon} onChange={e => setHorizon(Number(e.target.value))}>{Array.from({ length: 12 }, (_, i) => <option key={i + 1}>{i + 1}</option>)}</Select>
          </Field>
          <Button type="submit" disabled={action.loading}>{action.loading ? 'Forecasting…' : 'Run forecast'}</Button>
        </form>
        <div className="mt-4"><ErrorNotice error={action.error} retry={run} /></div>
        {action.data && (
          <div className="mt-4">
            <div className="mb-3 flex flex-wrap gap-2"><Pill tone="warn">Experimental</Pill><Pill>Origin {monthLabel(action.data.forecast_origin)}</Pill><Pill>{action.data.units}</Pill></div>
            <LineChart label="Forecast counts" yFormat={v => fmt(v, 2)} zeroBased series={[{ name: 'Expected systems per month', color: 'var(--color-gold)', dots: true, points: action.data.forecasts.map(f => ({ x: f.date, y: f.prediction })) }]} />
            <Table dense columns={['Month', 'Expected count']} rows={action.data.forecasts.map(f => [monthLabel(f.date), fmt(f.prediction, 3)])} />
            <p className="mt-2 text-sm text-mist">Target: {action.data.target_definition}</p>
            <Notes items={action.data.limitations} />
            <Raw data={action.data} />
          </div>
        )}
      </Panel>

      <UnavailableModel title="Multi-hazard disaster risk" call={api.disasterPredict} cacheKey="disaster-predict" served={{
        label: 'Rule-based v1.0', method: 'Rules and scenario-based risk model, the MVP choice in the project report (§9.10).',
        text: 'Served through risk-aware routing with simulated closures, rainfall and visitor anomaly detection, and the cyclone forecaster above.',
        links: [['#/routing', 'Risk-aware routing'], ['#/hotspots', 'Hotspots and anomalies']],
        learned: 'it needs dated disaster event, impact and verified non-event labels that do not exist yet.' }} />
    </Page>
  );
}
