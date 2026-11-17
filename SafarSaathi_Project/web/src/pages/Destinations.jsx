import React, { useMemo, useState } from 'react';
import { MONTHS, api, fmt } from '../api.js';
import { navigate, useQuery } from '../hooks.js';
import { Grid, Input, Notes, Origin, Page, Panel, Pill, Query, Raw, Stat, Table } from '../components/ui.jsx';
import { ClimateChart, LineChart } from '../components/charts.jsx';
import MapView from '../components/MapView.jsx';

function Climate({ id }) {
  const q = useQuery(`climate:${id}`, () => api.climate(id));
  return (
    <Query q={q} label="Summarising 25 years of daily NASA POWER data…">{c => {
      const months = c.monthly_climatology;
      const wettest = months.reduce((a, b) => ((b.PRECTOTCORR ?? -1) > (a.PRECTOTCORR ?? -1) ? b : a));
      const annualMean = c.annual.reduce((s, a) => s + a.precip_total_mm, 0) / c.annual.length;
      const monsoon = [6, 7, 8, 9].reduce((s, m) => s + (months[m - 1].PRECTOTCORR ?? 0), 0);
      const yearTotal = months.reduce((s, m) => s + (m.PRECTOTCORR ?? 0), 0);
      return (
        <>
          <Grid cols={4}>
            <Stat label="Mean annual rainfall" value={`${fmt(annualMean, 0)} mm`} note={`${c.annual[0].year}–${c.annual.at(-1).year} grid-cell estimate`} tone="water" />
            <Stat label="Share falling June–September" value={`${fmt((monsoon / yearTotal) * 100, 0)}%`} note={`Wettest month: ${MONTHS[wettest.month - 1]}, ${fmt(wettest.PRECTOTCORR, 0)} mm`} tone="water" />
            <Stat label="Wettest day on record" value={`${fmt(c.extremes.wettest_day?.mm, 0)} mm`} note={c.extremes.wettest_day ? new Date(c.extremes.wettest_day.date).toLocaleDateString('en-IN', { dateStyle: 'long' }) : ''} tone="hazard" />
            <Stat label="Coldest mean month" value={`${fmt(Math.min(...months.map(m => m.T2M_MIN ?? Infinity)), 1)} °C`} note="Mean daily minimum" />
          </Grid>
          <Panel title="Monthly climate" description="Average of 2000–2024 for this grid point. Bars are mean monthly rainfall totals; lines are mean daily maximum and minimum temperature." tone="water" aside={<Origin data={c} />}>
            <ClimateChart months={months} />
          </Panel>
          <Panel title="Rainfall by year" description="Annual totals help put a single season in context. They are reanalysis estimates, not gauge readings.">
            <LineChart label="Annual rainfall" yFormat={v => fmt(v, 0)} series={[{ name: 'Annual rainfall (mm)', color: 'var(--color-glacier)', dots: true, points: c.annual.map(a => ({ x: String(a.year), y: a.precip_total_mm })) }]} />
            <Table dense columns={['Month', 'Rain (mm)', 'Mean °C', 'Max °C', 'Min °C', 'Humidity %', 'Wind m/s']} rows={months.map(m => [MONTHS[m.month - 1], fmt(m.PRECTOTCORR, 1), fmt(m.T2M, 1), fmt(m.T2M_MAX, 1), fmt(m.T2M_MIN, 1), fmt(m.RH2M, 0), fmt(m.WS2M, 1)])} />
            <Notes items={c.limitations} />
          </Panel>
        </>
      );
    }}</Query>
  );
}

function Detail({ id }) {
  const q = useQuery(`destination:${id}`, () => api.destination(id));
  return (
    <Query q={q}>{({ destination: d, limitations }) => {
      const [lon, lat, elev] = d.geometry.coordinates;
      return (
        <>
          <Panel title={d.name} description={`${d.source}. Daily coverage ${d.coverage_start.slice(0, 4)}–${d.coverage_end.slice(0, 4)}.`} aside={<Pill tone="muted">Static source point</Pill>}>
            <Table columns={['', 'Latitude', 'Longitude', 'Elevation']} rows={[
              ['Requested location', fmt(d.query_coordinates.latitude, 4), fmt(d.query_coordinates.longitude, 4), '—'],
              ['Returned grid point', fmt(lat, 3), fmt(lon, 3), Number.isFinite(elev) ? `${fmt(elev, 0)} m` : '—'],
            ]} />
            <p className="mt-3 text-sm text-mist">Parameters available: {Object.entries(d.parameters).map(([k, v]) => `${v.longname} (${v.units})`).join(', ')}.</p>
            <Notes items={limitations} />
          </Panel>
          <Climate id={id} />
        </>
      );
    }}</Query>
  );
}

export default function Destinations({ route }) {
  const layers = useQuery('layers', api.layers);
  const [filter, setFilter] = useState('');
  const selected = route.param || 'kedarnath';
  const points = useMemo(() => (layers.data?.features || []).map(f => ({
    id: f.id, name: f.properties.name, lon: f.geometry.coordinates[0], lat: f.geometry.coordinates[1], elevation: f.geometry.coordinates[2],
  })), [layers.data]);
  const visible = points.filter(p => p.name.toLowerCase().includes(filter.toLowerCase())).sort((a, b) => a.name.localeCompare(b.name));
  return (
    <Page title="Destinations and climate" intro="Twenty-nine Uttarakhand towns, shrines and parks with 25 years of NASA POWER daily climate. Pick a place to see its monsoon profile, rainfall extremes and temperature range.">
      <Query q={layers}>{data => (
        <div className="grid gap-4 lg:grid-cols-[1fr_260px]">
          <div>
            <MapView points={points} selected={selected} onSelect={id => navigate(`destinations/${id}`)} />
            <p className="mt-2 text-xs text-mist">{data.coordinate_metadata} Points mark the NASA POWER grid locations returned for each query, not destination boundaries.</p>
          </div>
          <div className="flex max-h-[470px] flex-col rounded-xl border border-line bg-slate">
            <div className="p-3"><Input type="search" placeholder="Filter places" aria-label="Filter places" value={filter} onChange={e => setFilter(e.target.value)} /></div>
            <ul className="scroll-thin flex-1 overflow-y-auto px-2 pb-2">
              {visible.map(p => (
                <li key={p.id}>
                  <a href={`#/destinations/${p.id}`} aria-current={p.id === selected ? 'true' : undefined}
                    className={`flex justify-between rounded-lg px-3 py-1.5 text-sm ${p.id === selected ? 'bg-gold/10 text-gold font-semibold' : 'text-snow/85 hover:bg-ridge'}`}>
                    <span>{p.name}</span><span className="num text-xs text-mist">{Number.isFinite(p.elevation) ? `${Math.round(p.elevation)} m` : ''}</span>
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}</Query>
      {points.length > 0 && <Detail key={selected} id={selected} />}
      {layers.data && <Raw data={layers.data} label="Map layer GeoJSON" />}
    </Page>
  );
}
