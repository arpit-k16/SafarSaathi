import React, { useState } from 'react';
import { api, compact, fmt, monthLabel } from '../api.js';
import { useAction, useQuery } from '../hooks.js';
import { Button, ErrorNotice, Field, Grid, Notes, Origin, Page, Panel, Pill, Query, Raw, Segmented, Select, Stat, Table, humanize, qualityTone } from '../components/ui.jsx';
import { LineChart } from '../components/charts.jsx';
import Explain from '../components/Explain.jsx';

function MetricLine({ metrics, label }) {
  if (!metrics) return null;
  return (
    <p className="text-sm text-mist">
      {label}: mean absolute error {compact(metrics.MAE)} arrivals, WAPE {fmt(metrics.WAPE * 100, 1)}%, MASE {fmt(metrics.MASE, 2)} over {metrics.n} held-out origins.
    </p>
  );
}

function ForecastPanel({ kind, history, caps }) {
  const annual = kind === 'annual';
  const [horizon, setHorizon] = useState(annual ? 3 : 6);
  const action = useAction();
  const observations = history.series.find(s => s.frequency === kind)?.observations || [];
  const tail = annual ? observations : observations.slice(-30);
  const key = annual ? 'year' : 'date';
  const run = () => action.run(() => (annual ? api.annualForecast : api.monthlyForecast)(horizon));
  const result = action.data;
  const last = tail.at(-1);
  const forecastPoints = result ? [{ x: String(last[key]), y: last.arrivals }, ...result.forecasts.map(f => ({ x: String(f[key]), y: f.prediction }))] : [];
  const tourismCap = caps?.find(c => c.model_id === 'tourism_demand_forecaster');
  const metricStep = annual ? 1 : horizon >= 6 ? 6 : horizon >= 3 ? 3 : 1;
  const metrics = annual ? tourismCap?.metrics : tourismCap?.monthly_fta?.metrics?.[String(metricStep)];
  return (
    <Panel
      title={annual ? 'Annual international arrivals, India' : 'Monthly foreign tourist arrivals, India'}
      description={annual
        ? 'World Bank ST.INT.ARVL, 1995–2019. The annual model forecasts forward from 2019, its last observation, so these are not 2026 predictions.'
        : 'Ministry of Tourism FTAs (excluding NRIs), January 2019 to December 2024. The monthly model forecasts from December 2024.'}
      aside={<Origin data={history} />}>
      <LineChart label={`${kind} arrivals`} series={[
        { name: 'Observed', color: 'var(--color-snow)', points: tail.map(o => ({ x: String(o[key]), y: o.arrivals })) },
        ...(result ? [{ name: 'Model forecast', color: 'var(--color-gold)', dashed: true, dots: true, points: forecastPoints }] : []),
      ]} />
      <form className="mt-5 flex flex-wrap items-end gap-3" onSubmit={e => { e.preventDefault(); run(); }}>
        <Field label={annual ? 'Years ahead' : 'Months ahead'} className="w-40">
          <Select value={horizon} onChange={e => setHorizon(Number(e.target.value))}>
            {Array.from({ length: annual ? 3 : 6 }, (_, i) => <option key={i + 1} value={i + 1}>{i + 1}</option>)}
          </Select>
        </Field>
        <Button type="submit" disabled={action.loading}>{action.loading ? 'Forecasting…' : 'Run forecast'}</Button>
        <MetricLine metrics={metrics} label={`Recorded test accuracy, ${metricStep} ${annual ? 'year' : 'month'}${metricStep > 1 ? 's' : ''} ahead`} />
      </form>
      <div className="mt-4"><ErrorNotice error={action.error} retry={run} /></div>
      {result && (
        <div className="mt-4">
          <div className="mb-3 flex flex-wrap gap-2">
            <Pill tone={qualityTone(result.quality_status)}>{humanize(result.quality_status)}</Pill>
            <Pill>Model version {result.model_version}</Pill>
            <Pill>Origin {annual ? result.forecast_origin_year : monthLabel(result.forecast_origin)}</Pill>
          </div>
          <Table columns={['Period', 'Horizon', `Forecast (${result.units})`]} rows={result.forecasts.map(f => [annual ? f.year : monthLabel(f.date), f.horizon, fmt(f.prediction, 0)])} />
          {result.target_definition && <p className="mt-2 text-sm text-mist">Target: {result.target_definition}</p>}
          {result.explanation && (
            <div className="mt-4">
              <Explain title="Why this forecast"
                rule={result.explanation.kind === 'rule' ? `Selected method: ${result.explanation.method.replaceAll('_', ' ')}. ${result.explanation.rule} It beat ridge regression and the other candidates on held-out data, so it was saved.` : null}
                baseline={result.explanation.kind === 'linear_contributions' ? `${result.explanation.baseline_label}: ${compact(result.explanation.baseline)}. Each bar shows how far a feature moves the first forecast from that average.` : null}
                factors={(result.explanation.contributions || []).map(c => ({ label: c.label, value: c.contribution }))}
                format={v => `${v > 0 ? '+' : ''}${compact(v)}`}
                uncertainty={result.explanation.uncertainty ? `Typical one-step error on held-out ${annual ? 'years' : 'months'}: ±${compact(result.explanation.uncertainty.held_out_MAE)} arrivals (WAPE ${fmt(result.explanation.uncertainty.WAPE * 100, 1)}%, n = ${result.explanation.uncertainty.n}). No calibrated intervals.` : 'No held-out error recorded.'}
                freshness={result.explanation.freshness}
                provenance={[['Model', `${result.model_id} · ${result.model_version}`]]} />
            </div>
          )}
          <Notes items={result.limitations} />
          <Raw data={result} />
        </div>
      )}
    </Panel>
  );
}

export default function Tourism() {
  const history = useQuery('history', api.history);
  const caps = useQuery('capabilities', api.capabilities);
  const [view, setView] = useState('monthly');
  return (
    <Page title="Tourism demand" intro="National arrival history and the two saved forecasting models. Annual and monthly series measure different things and are never combined.">
      <Query q={history}>{data => {
        const annual = data.series.find(s => s.frequency === 'annual');
        const monthly = data.series.find(s => s.frequency === 'monthly');
        const covid = annual.observations.find(o => o.year === 2019);
        return (
          <>
            <Grid cols={4}>
              <Stat label="Annual observations" value={annual.observations.length} note={`${annual.observations[0].year}–${annual.observations.at(-1).year}`} />
              <Stat label="Peak annual arrivals" value={compact(Math.max(...annual.observations.map(o => o.arrivals)))} note={`in ${covid?.year ?? ''}`} />
              <Stat label="Monthly observations" value={monthly.observations.length} note={`${monthLabel(monthly.observations[0].date)} to ${monthLabel(monthly.observations.at(-1).date)}`} />
              <Stat label="Lowest month" value={compact(Math.min(...monthly.observations.map(o => o.arrivals)))} note={monthLabel(monthly.observations.reduce((a, b) => (b.arrivals < a.arrivals ? b : a)).date)} tone="hazard" />
            </Grid>
            <div className="flex justify-end"><Segmented label="Series" value={view} onChange={setView} options={[{ value: 'monthly', label: 'Monthly model' }, { value: 'annual', label: 'Annual model' }]} /></div>
            <ForecastPanel key={view} kind={view} history={data} caps={caps.data} />
            <Notes items={data.limitations} title="About these series" />
          </>
        );
      }}</Query>
    </Page>
  );
}
