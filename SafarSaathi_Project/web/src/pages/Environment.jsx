import React, { useState } from 'react';
import { api, compact, fmt } from '../api.js';
import { useAction, useQuery } from '../hooks.js';
import { Button, ErrorNotice, Field, Notes, Page, Panel, Pill, Query, Raw, Segmented, Select, Table, humanize } from '../components/ui.jsx';
import { CompareBars, LineChart } from '../components/charts.jsx';
import { UnavailableModel } from './Hazards.jsx';

const label = key => humanize(key).replace('Pm25', 'PM2.5').replace('km2', 'km²').replace('ug m3', 'µg/m³');

function NationalTrend({ years }) {
  const q = useQuery('indicators:IND:all', () => Promise.all(years.map(y => api.indicators('IND', y))));
  return (
    <Query q={q} label="Loading national indicator history…">{rows => {
      const obs = rows.map(r => r.observation);
      return (
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="mb-2 text-sm font-semibold text-snow">Domestic tourist visits, India</h3>
            <LineChart label="Domestic visits" series={[{ name: 'Domestic visits', color: 'var(--color-gold)', dots: true, points: obs.map(o => ({ x: String(o.year), y: o.domestic_visits })) }]} height={220} />
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold text-snow">Modeled PM2.5 exposure, India</h3>
            <LineChart label="PM2.5" yFormat={v => fmt(v, 0)} series={[{ name: 'PM2.5 (µg/m³)', color: 'var(--color-ember)', dots: true, points: obs.filter(o => o.pm25_exposure_ug_m3 != null).map(o => ({ x: String(o.year), y: o.pm25_exposure_ug_m3 })) }]} height={220} />
          </div>
        </div>
      );
    }}</Query>
  );
}

function StateRanking({ geographies, geographyYears }) {
  const [year, setYear] = useState(2024);
  const states = geographies.filter(g => g !== 'IND' && geographyYears[g]?.includes(year));
  const q = useQuery(`indicators:states:${year}`, () => Promise.all(states.map(g => api.indicators(g, year))));
  return (
    <Panel title="Visits by State and Union Territory" description="Reported domestic visits from the India Tourism Statistics compendium. Repeat visits count separately, so this is footfall volume, not unique visitors or crowding."
      aside={<Segmented label="Year" value={year} onChange={setYear} options={[2023, 2024].map(y => ({ value: y, label: String(y) }))} />}>
      <Query q={q} label="Loading State/UT indicators…">{rows => {
        const sorted = rows.map(r => r.observation).filter(o => o.domestic_visits_million != null).sort((a, b) => b.domestic_visits_million - a.domestic_visits_million);
        return <CompareBars format={v => `${fmt(v, 1)} M`} rows={sorted.slice(0, 15).map(o => ({
          label: o.geography, note: o.domestic_visit_growth_percent != null ? `${o.domestic_visit_growth_percent > 0 ? '+' : ''}${fmt(o.domestic_visit_growth_percent, 1)}% vs previous year` : undefined,
          values: [{ name: 'Domestic', value: o.domestic_visits_million, color: o.geography === 'Uttarakhand' ? 'var(--color-gold)' : 'var(--color-mist)' }],
        }))} />;
      }}</Query>
    </Panel>
  );
}

export default function Environment() {
  const meta = useQuery('indicator-meta', api.indicatorMetadata);
  const [geo, setGeo] = useState('Uttarakhand');
  const [year, setYear] = useState('');
  const lookup = useAction();
  const pm = useAction();
  return (
    <Page title="Environment and pressure" intro="Historical visit volumes and environmental indicators from official compilations. Destination stress is scored by the transparent Destination Stress Index on the Digital twin page; a learned stress model is not trained because there is no observed crowding or carrying-capacity data.">
      <Query q={meta}>{m => {
        const years = m.geography_years[geo] || [];
        const y = years.includes(Number(year)) ? Number(year) : years.at(-1);
        return (
          <>
            <Panel title="Look up an indicator record" description={`${m.geographies.length} geographies. India has ${m.geography_years.IND.length} years (${m.geography_years.IND[0]}–${m.geography_years.IND.at(-1)}); States and UTs have 2023–2024.`}>
              <form className="flex flex-wrap items-end gap-3" onSubmit={e => { e.preventDefault(); lookup.run(() => api.indicators(geo, y)); }}>
                <Field label="Geography" className="w-60"><Select value={geo} onChange={e => { setGeo(e.target.value); setYear(''); }}>{m.geographies.map(g => <option key={g} value={g}>{g === 'IND' ? 'India (national)' : g}</option>)}</Select></Field>
                <Field label="Year" className="w-32"><Select value={y ?? ''} onChange={e => setYear(e.target.value)}>{years.map(v => <option key={v}>{v}</option>)}</Select></Field>
                <Button type="submit" disabled={lookup.loading || !y}>Show record</Button>
              </form>
              <div className="mt-4"><ErrorNotice error={lookup.error} /></div>
              {lookup.data && (
                <div className="mt-4">
                  <div className="mb-2 flex gap-2"><Pill tone="muted">Historical record, not a prediction</Pill><Pill>{humanize(lookup.data.observation.source_quality)}</Pill></div>
                  <Table columns={['Field', 'Value']} rows={Object.entries(lookup.data.observation).filter(([k]) => !['geography', 'year'].includes(k)).map(([k, v]) => [label(k), v === null ? <span className="text-mist">Not reported</span> : typeof v === 'number' ? (v > 1e5 ? compact(v) : fmt(v, 3)) : String(v)])} />
                  <Notes items={[...Object.entries(lookup.data.formulae).map(([k, v]) => `${humanize(k)}: ${v}`), lookup.data.missing_data_rule]} title="Formulae and missing-data rule" />
                </div>
              )}
              <Notes items={m.limitations} />
            </Panel>
            <Panel title="National trend" description="All observed years for India. 2020–2021 show the pandemic collapse in domestic travel."><NationalTrend years={m.geography_years.IND} /></Panel>
            <StateRanking geographies={m.geographies} geographyYears={m.geography_years} />
          </>
        );
      }}</Query>

      <Panel title="PM2.5 exposure forecast, India" description="Ridge model on the World Bank / GBD modeled national annual series. It extrapolates one year past the last observation (2023 → 2024); it is not current air quality.">
        <Button onClick={() => pm.run(api.pm25Forecast)} disabled={pm.loading}>{pm.loading ? 'Forecasting…' : 'Forecast 2024 exposure'}</Button>
        <div className="mt-4"><ErrorNotice error={pm.error} /></div>
        {pm.data && (
          <div className="mt-4">
            <p className="font-display text-3xl font-semibold text-ember num">{fmt(pm.data.forecasts[0].prediction, 1)} <span className="text-base font-normal text-mist">{pm.data.units} in {pm.data.forecasts[0].date}</span></p>
            <p className="mt-1 text-sm text-mist">Target: {pm.data.target_definition}</p>
            <Notes items={pm.data.limitations} />
            <Raw data={pm.data} />
          </div>
        )}
      </Panel>

      <UnavailableModel title="Destination stress" call={api.stressPredict} cacheKey="stress-predict" served={{
        label: 'Index v1.0', method: 'Transparent weighted index, the MVP choice in the project report (§9.2, §9.10).',
        text: 'Served as the Destination Stress Index for 28 destinations, with what-if scenarios and an intervention planner.',
        links: [['#/twin', 'Digital twin and stress'], ['#/optimizer', 'Intervention planner']],
        learned: 'it needs observed crowding, occupancy or carrying-capacity labels that do not exist yet.' }} />
    </Page>
  );
}
