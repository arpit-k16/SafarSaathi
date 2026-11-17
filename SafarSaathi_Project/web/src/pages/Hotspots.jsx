import React, { useMemo, useState } from 'react';
import { api, compact, fmt } from '../api.js';
import { useQuery } from '../hooks.js';
import { Field, Grid, Input, Notes, Page, Panel, Pill, Query, Raw, Segmented, Select, Stat, Table } from '../components/ui.jsx';
import { LineChart } from '../components/charts.jsx';
import LayerMap from '../components/LayerMap.jsx';
import Explain from '../components/Explain.jsx';

const PALETTE = ['#e8bd4f', '#6fb8c9', '#8fb878', '#e5765f', '#c7a3e0', '#d9cfa8', '#7fa7e0', '#e89a55', '#9ad3c0', '#f0a3b5'];
const color = c => (c < 0 ? '#5d6170' : PALETTE[c % PALETTE.length]);

function Clusters({ years }) {
  const [form, setForm] = useState({ year: years[years.length - 1], method: 'dbscan', eps_km: 35, min_samples: 2, k: 4 });
  const key = `hot:${JSON.stringify(form)}`;
  const q = useQuery(key, () => api.hotspots(form));
  return (
    <Panel title="Visitor hotspots" description="Clusters of the 28 UTDB destinations. DBSCAN groups places within a distance of each other; K-means groups by location and visitor volume together.">
      <div className="mb-4 grid gap-4 md:grid-cols-4">
        <Field label="Method"><Segmented label="Method" value={form.method} onChange={method => setForm({ ...form, method })} options={[{ value: 'dbscan', label: 'DBSCAN' }, { value: 'kmeans', label: 'K-means' }]} /></Field>
        <Field label="Year"><Select value={form.year} onChange={e => setForm({ ...form, year: Number(e.target.value) })}>{[...years].reverse().map(y => <option key={y}>{y}</option>)}</Select></Field>
        {form.method === 'dbscan' ? (
          <>
            <Field label="Neighbourhood radius (km)" hint="5–150"><Input type="number" min={5} max={150} value={form.eps_km} onChange={e => setForm({ ...form, eps_km: Number(e.target.value) })} /></Field>
            <Field label="Minimum places per cluster" hint="1–10"><Input type="number" min={1} max={10} value={form.min_samples} onChange={e => setForm({ ...form, min_samples: Number(e.target.value) })} /></Field>
          </>
        ) : (
          <Field label="Number of clusters (k)" hint="2–10"><Input type="number" min={2} max={10} value={form.k} onChange={e => setForm({ ...form, k: Number(e.target.value) })} /></Field>
        )}
      </div>
      <Query q={q} label="Clustering…">{d => (
        <div className="flex flex-col gap-5">
          <LayerMap fitKey="hotspots" label="Hotspot map" points={d.points.map(p => ({ id: p.id, lat: p.lat, lon: p.lon, color: color(p.cluster), radius: 4 + Math.log10(Math.max(p.visitors, 10)) * 1.6,
            label: `${p.name}: ${compact(p.visitors)} visitors${p.cluster < 0 ? ' (isolated)' : ` · cluster ${p.cluster + 1}`}` }))} />
          <Grid cols={3}>
            <Stat label="Clusters found" value={d.clusters.filter(c => !c.noise).length} note={d.clusters.some(c => c.noise) ? `${d.clusters.find(c => c.noise).members.length} isolated places` : 'No isolated places'} />
            <Stat label="Silhouette score" value={fmt(d.evaluation.silhouette, 2)} note={`Random-label baseline ${fmt(d.evaluation.random_label_baseline, 2)}`} tone="good" />
            <Stat label="Largest hotspot share" value={`${fmt(d.clusters[0].share_of_state * 100, 0)}%`} note={`of ${d.year} state visitors`} />
          </Grid>
          <Table dense columns={['', 'Cluster', 'Places', 'Visitors', 'Share', 'Mean stress index', 'Radius']} rows={d.clusters.map(c => [
            <span className="inline-block h-3 w-3 rounded-full" style={{ background: color(c.cluster) }} />,
            c.noise ? 'Isolated' : `Cluster ${c.cluster + 1}`, c.names.join(', '), compact(c.visitors), `${fmt(c.share_of_state * 100, 1)}%`, fmt(c.mean_stress_index, 3), `${fmt(c.radius_km, 0)} km`])} />
          <p className="text-xs text-mist">{d.evaluation.note}</p>
          <Notes items={d.limitations} />
        </div>
      )}</Query>
    </Panel>
  );
}

function Anomalies({ data, twin }) {
  const [dest, setDest] = useState('kedarnath');
  const series = useMemo(() => twin.destinations.find(d => d.id === dest), [twin, dest]);
  const flags = data.visitor_anomalies.filter(a => a.id === dest);
  const e = data.evaluation;
  return (
    <>
      <Grid cols={4}>
        <Stat label="Visitor anomalies flagged" value={data.visitor_anomalies.length} note="destination-years, 2001–2024" />
        <Stat label="Precision vs reference events" value={fmt(e.robust_z.precision, 2)} note={`Baseline ${fmt(e.baseline_50pct_change.precision, 2)}`} tone="good" />
        <Stat label="Recall vs reference events" value={fmt(e.robust_z.recall, 2)} note={`Baseline ${fmt(e.baseline_50pct_change.recall, 2)}`} />
        <Stat label="Rainfall anomalies flagged" value={data.rain_anomalies.length} note="unusual wettest day or monsoon total" tone="water" />
      </Grid>
      <Panel title="Unusual visitor years" description={data.visitor_method}
        aside={<Field label="Destination"><Select value={dest} onChange={ev => setDest(ev.target.value)}>{twin.destinations.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</Select></Field>}>
        <VisitsChart series={data.series[dest]} flags={flags} />
        <Table dense columns={['Year', 'Visitors', 'Previous year', 'Change', 'Robust z', 'Type']} rows={flags.map(f => [f.year, compact(f.visitors), compact(f.previous), `${f.change_pct > 0 ? '+' : ''}${fmt(f.change_pct, 0)}%`, fmt(f.robust_z, 1), <Pill tone={f.direction === 'drop' ? 'off' : 'info'}>{f.direction}</Pill>])}
          empty="No unusual years for this destination." />
        <div className="mt-5">
          <Explain title="How to read a flag"
            rule="A year is flagged when its year-on-year change is far outside that destination's own usual range, measured with the median and median absolute deviation so that past shocks do not hide new ones."
            uncertainty={`Against hand-listed reference events (${e.reference_events}) the detector reaches precision ${fmt(e.robust_z.precision, 2)} and recall ${fmt(e.robust_z.recall, 2)}; a plain ±50% rule reaches ${fmt(e.baseline_50pct_change.precision, 2)} and ${fmt(e.baseline_50pct_change.recall, 2)}.`}
            freshness="UTDB annual statistics 2000–2024"
            provenance={[['Note', e.note]]} />
        </div>
      </Panel>
      <Panel title="Unusual rainfall years" description={data.rain_method} tone="water">
        <Table dense columns={['Place', 'Year', 'Wettest day (mm)', 'z', 'Monsoon total (mm)', 'z']} rows={data.rain_anomalies.slice(0, 25).map(r => [r.name, r.year, fmt(r.max_day_mm, 0), fmt(r.max_day_z, 1), fmt(r.monsoon_mm, 0), fmt(r.monsoon_z, 1)])} />
        <Notes items={data.limitations} />
        <Raw data={data} />
      </Panel>
    </>
  );
}

function VisitsChart({ series, flags }) {
  if (!series) return null;
  const flagged = new Set(flags.map(f => f.year));
  return (
    <div className="mb-4">
      <LineChart label="Annual visitors" zeroBased series={[
        { name: 'Visitors', color: 'var(--color-snow)', points: series.map(p => ({ x: String(p.year), y: p.total })) },
        { name: 'Flagged year', color: 'var(--color-ember)', markersOnly: true, points: series.filter(p => flagged.has(p.year)).map(p => ({ x: String(p.year), y: p.total })) },
      ]} />
    </div>
  );
}

export default function Hotspots() {
  const twin = useQuery('twin:meta', api.twinMetadata);
  const anomalies = useQuery('anomalies', api.anomalies);
  return (
    <Page title="Hotspots and anomalies" intro="Where Uttarakhand's visitors concentrate, and which years broke the pattern. Hotspots cluster the 28 UTDB destinations; anomaly detection flags unusual visitor and rainfall years against each place's own history and checks itself against known events.">
      <Query q={twin}>{t => (
        <>
          <Clusters years={t.years} />
          <Query q={anomalies} label="Scanning 25 years…">{a => <Anomalies data={a} twin={t} />}</Query>
        </>
      )}</Query>
    </Page>
  );
}
