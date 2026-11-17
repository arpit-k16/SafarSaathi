import React from 'react';
import { api, compact, monthLabel } from '../api.js';
import { useQuery } from '../hooks.js';
import { Grid, Page, Panel, Pill, Query, Stat, humanize } from '../components/ui.jsx';
import { LineChart } from '../components/charts.jsx';

const CAPABILITY_PAGES = {
  tourism_demand_forecaster: ['tourism', 'Annual and monthly arrival forecasts'],
  disaster_risk_predictor: ['hazards', 'North Indian Ocean cyclone archive counts'],
  flood_segmentation_model: ['flood', 'Water extent from Sentinel-1 tiles'],
  destination_stress_predictor: ['environment', 'Historical visit and PM2.5 indicators'],
};

function CapabilityRow({ cap }) {
  const [page0, what] = CAPABILITY_PAGES[cap.model_id] || ['models', cap.name];
  const page = cap.served_as?.page || page0;
  const scoped = cap.scoped_forecast?.inference_available;
  const broad = cap.inference_available;
  return (
    <a href={`#/${page}`} className="grid grid-cols-1 gap-2 border-b border-line/70 py-4 last:border-0 hover:bg-ridge/40 md:grid-cols-[1.1fr_1.4fr_auto] md:items-center md:px-2">
      <div>
        <div className="font-display text-base font-semibold text-snow">{cap.name}</div>
        <div className="text-sm text-mist">{what}</div>
      </div>
      <p className="text-sm text-mist">{broad ? cap.implementation_scope : cap.served_as ? cap.served_as.reason : cap.reason}</p>
      <div className="flex flex-wrap gap-2 md:justify-end">
        {cap.served_as && !broad
          ? <Pill tone="ok" title={cap.served_as.method}>{cap.served_as.label}</Pill>
          : <Pill tone={broad ? (cap.status === 'FINAL_V1' ? 'ok' : 'warn') : 'off'}>{broad ? (cap.status === 'FINAL_V1' ? 'Final v1.0' : 'Experimental model') : 'Broad model not trained'}</Pill>}
        {scoped && <Pill tone="info">Scoped forecast available</Pill>}
        {cap.monthly_fta?.inference_available && <Pill tone="info">Monthly model available</Pill>}
        {cap.historical_indicators?.available && <Pill tone="muted">Indicators only</Pill>}
      </div>
    </a>
  );
}

export default function Overview() {
  const history = useQuery('history', api.history);
  const caps = useQuery('capabilities', api.capabilities);
  const health = useQuery('health', api.health);
  const places = useQuery('destinations', api.destinations);
  const research = useQuery('research', api.research);
  const annual = history.data?.series.find(s => s.frequency === 'annual')?.observations || [];
  const monthly = history.data?.series.find(s => s.frequency === 'monthly')?.observations || [];
  return (
    <Page title="Where Uttarakhand's tourism meets its weather and hazards"
      intro="SafarSaathi brings together India's tourism arrivals, NASA POWER climate history for 29 Uttarakhand locations, flood segmentation on Sentinel-1 imagery and cyclone archives. Every figure here comes from the backend's saved models and source files.">
      <Grid cols={4}>
        <Stat label="Saved models serving requests" value={health.data ? health.data.trained_models : '…'} note="No training happens on request" />
        <Stat label="Climate source locations" value={places.data ? places.data.destinations.length : '…'} note="NASA POWER daily, 2000–2024" tone="water" />
        <Stat label={`India international arrivals, ${annual.at(-1)?.year ?? '…'}`} value={compact(annual.at(-1)?.arrivals)} note="World Bank ST.INT.ARVL" />
        <Stat label={`Foreign tourist arrivals, ${monthly.length ? monthLabel(monthly.at(-1).date) : '…'}`} value={compact(monthly.at(-1)?.arrivals)} note="Ministry of Tourism, monthly" />
      </Grid>

      <Panel title="Foreign tourist arrivals to India by month" description="The last 36 monthly observations from the Ministry of Tourism series used to train the monthly model."
        aside={<a href="#/tourism" className="text-sm font-semibold text-gold hover:underline">Forecast arrivals</a>}>
        <Query q={history}>{() => (
          <LineChart label="Monthly foreign tourist arrivals" series={[{ name: 'Foreign tourist arrivals', color: 'var(--color-gold)', points: monthly.slice(-36).map(o => ({ x: o.date, y: o.arrivals })) }]} />
        )}</Query>
      </Panel>

      <Panel title="What the console can answer today" description="Capability status reported live by the backend. Broad warning and stress models stay switched off until observed outcome data exists.">
        <Query q={caps}>{data => <div>{data.map(c => <CapabilityRow key={c.model_id} cap={c} />)}</div>}</Query>
      </Panel>

      <Panel title="Latest research validation" description="Stored audit findings from the project's evaluation run, not a live re-evaluation."
        aside={research.data && <Pill tone="warn">{research.data.date}</Pill>}>
        <Query q={research}>{data => (
          <>
            <p className="mb-3 text-sm text-snow">{humanize(data.status)}</p>
            <ul className="grid gap-2 text-sm text-mist md:grid-cols-2">{data.findings.map(f => <li key={f} className="rounded-lg border border-line bg-ink/40 px-3 py-2">{f}</li>)}</ul>
          </>
        )}</Query>
      </Panel>
    </Page>
  );
}
