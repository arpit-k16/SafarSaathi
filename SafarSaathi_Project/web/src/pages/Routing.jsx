import React, { useState } from 'react';
import { api, fmt } from '../api.js';
import { useAction, useQuery } from '../hooks.js';
import { Button, ErrorNotice, Field, Grid, Notes, Page, Panel, Pill, Query, Raw, Select, Stat, Table } from '../components/ui.jsx';
import LayerMap from '../components/LayerMap.jsx';
import Explain from '../components/Explain.jsx';

const GREEK = { alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', epsilon: 'ε' };
const NAMES = { alpha: 'Travel time', beta: 'Hazard exposure', gamma: 'Vulnerability', delta: 'Congestion', epsilon: 'Uncertainty' };
const change = v => (v == null ? '—' : `${v > 0 ? '+' : ''}${fmt(v, 1)}%`);

function Form({ meta, onRun, loading }) {
  const [from, setFrom] = useState('rishikesh');
  const [to, setTo] = useState('kedarnath');
  const [w, setW] = useState(meta.default_weights);
  const [closures, setClosures] = useState([{ near: 'rudraprayag', radius_km: 4 }]);
  const run = () => onRun({ from, to, weights: w, closures });
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="flex flex-col gap-4">
        <h3 className="font-display font-semibold">Trip</h3>
        <Field label="From"><Select value={from} onChange={e => setFrom(e.target.value)}>{meta.places.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</Select></Field>
        <Field label="To"><Select value={to} onChange={e => setTo(e.target.value)}>{meta.places.map(p => <option key={p.id} value={p.id}>{p.name}{p.trek_or_offroad ? ' (road head)' : ''}</option>)}</Select></Field>
        <Button onClick={run} disabled={loading || from === to}>{loading ? 'Routing…' : 'Compare routes'}</Button>
      </div>
      <div className="flex flex-col gap-3">
        <h3 className="font-display font-semibold">Route-cost coefficients</h3>
        {Object.keys(meta.default_weights).map(k => (
          <Field key={k} label={<span className="flex justify-between"><span>{GREEK[k]} · {NAMES[k]}</span><span className="num text-gold">{w[k]}</span></span>}>
            <input type="range" min={k === 'alpha' ? 0.5 : 0} max={10} step={0.5} value={w[k]} onChange={e => setW({ ...w, [k]: Number(e.target.value) })} className="accent-[#e8bd4f]" />
          </Field>
        ))}
      </div>
      <div className="flex flex-col gap-3">
        <h3 className="font-display font-semibold">Simulated road closures</h3>
        <p className="text-xs text-mist">Close every road within a radius of a place, as a landslide or washout might.</p>
        {closures.map((c, i) => (
          <div key={i} className="grid grid-cols-[1fr_5.5rem_auto] items-end gap-2">
            <Field label="Near"><Select value={c.near} onChange={e => setClosures(closures.map((x, j) => (j === i ? { ...x, near: e.target.value } : x)))}>{meta.places.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</Select></Field>
            <Field label="Radius km"><Select value={c.radius_km} onChange={e => setClosures(closures.map((x, j) => (j === i ? { ...x, radius_km: Number(e.target.value) } : x)))}>{[1, 2, 3, 4, 5, 8, 10, 15].map(r => <option key={r}>{r}</option>)}</Select></Field>
            <Button variant="ghost" onClick={() => setClosures(closures.filter((_, j) => j !== i))} aria-label="Remove closure">Remove</Button>
          </div>
        ))}
        {closures.length < 5 && <Button variant="secondary" onClick={() => setClosures([...closures, { near: 'joshimath', radius_km: 3 }])}>Add a closure</Button>}
      </div>
    </div>
  );
}

function Result({ data, meta }) {
  const circles = (data.request?.closures || []).map(c => {
    const p = meta.places.find(x => x.id === c.near);
    return p && { lat: p.lat, lon: p.lon, radius_km: c.radius_km, label: `Simulated closure near ${p.name} (${c.radius_km} km)` };
  }).filter(Boolean);
  if (data.status === 'NO_ROUTE') {
    return <Panel title="No route" tone="hazard"><p className="text-snow">{data.detail}</p>
      <div className="mt-4"><LayerMap fitKey={JSON.stringify(data.request)} circles={circles} points={[data.from, data.to].map(p => ({ ...p, color: '#ebe7dc', label: p.name }))} /></div></Panel>;
  }
  const s = data.shortest_time, r = data.risk_aware, c = data.comparison;
  const term = (k, v) => ({ label: `${NAMES[k]}`, value: v });
  return (
    <>
      <Grid cols={4}>
        <Stat label="Risk-aware travel time" value={`${fmt(r.time_min / 60, 1)} h`} note={`${change(c.time_change_pct)} vs shortest time (${fmt(s.time_min / 60, 1)} h)`} />
        <Stat label="Distance" value={`${fmt(r.distance_km, 0)} km`} note={`${change(c.distance_change_pct)} vs ${fmt(s.distance_km, 0)} km`} />
        <Stat label="Hazard exposure (exposure-km)" value={fmt(r.exposure_km, 0)} note={`${change(c.exposure_change_pct)} vs ${fmt(s.exposure_km, 0)}`} tone={c.exposure_change_pct < 0 ? 'good' : undefined} />
        <Stat label="Closed road segments" value={data.closed_segments} note={c.same_route ? 'Both methods chose the same road' : 'The two methods diverge'} tone={data.closed_segments ? 'hazard' : undefined} />
      </Grid>
      <Panel title={`${data.from.name} to ${data.to.name}`} description="Gold: risk-aware route. Grey dashed: shortest-time baseline. Red circles: simulated closures.">
        <LayerMap fitKey={JSON.stringify(data.request)} circles={circles}
          lines={[{ coords: s.geometry, color: '#a39f92', weight: 4, dashed: true, label: 'Shortest time' }, { coords: r.geometry, color: '#e8bd4f', weight: 5, label: 'Risk-aware' }]}
          points={[data.from, data.to].map(p => ({ id: p.id, lat: p.lat, lon: p.lon, color: '#ebe7dc', radius: 7, label: p.name }))} />
        {(data.snap_km.from > 2 || data.snap_km.to > 2) && <p className="mt-3 text-sm text-gold">The road network ends {fmt(Math.max(data.snap_km.from, data.snap_km.to), 1)} km from {data.snap_km.to > 2 ? data.to.name : data.from.name}; the last stretch is on foot and is not routed.</p>}
        <div className="mt-4">
          <Table dense columns={['', 'Shortest time', 'Risk-aware', 'Change']} rows={[
            ['Travel time', `${fmt(s.time_min, 0)} min`, `${fmt(r.time_min, 0)} min`, change(c.time_change_pct)],
            ['Distance', `${fmt(s.distance_km, 1)} km`, `${fmt(r.distance_km, 1)} km`, change(c.distance_change_pct)],
            ['Hazard exposure (mean, 0–1)', fmt(s.hazard_exposure, 3), fmt(r.hazard_exposure, 3), ''],
            ['Exposure-km', fmt(s.exposure_km, 1), fmt(r.exposure_km, 1), change(c.exposure_change_pct)],
            ['Vulnerability (mean)', fmt(s.vulnerability, 3), fmt(r.vulnerability, 3), ''],
            ['Congestion (mean)', fmt(s.congestion, 3), fmt(r.congestion, 3), ''],
            ['Highest point (m, interpolated)', fmt(s.max_elevation_m, 0), fmt(r.max_elevation_m, 0), ''],
            ['Main roads', s.main_roads.slice(0, 3).map(x => x.name).join(', '), r.main_roads.slice(0, 3).map(x => x.name).join(', '), ''],
          ]} />
        </div>
      </Panel>
      <Explain title="Why the risk-aware route looks like this"
        rule={data.explanation.formula}
        baseline={c.same_route ? 'Both searches chose the same road: in this valley there is no alternative that lowers risk enough to justify the extra time at these coefficients.' : 'The searches diverge because the extra minutes spent on the risk-aware route are outweighed by the risk penalties it avoids.'}
        factors={['beta', 'gamma', 'delta', 'epsilon'].map(k => term(k, data.weights[k] * ({ beta: r.hazard_exposure, gamma: r.vulnerability, delta: r.congestion, epsilon: r.uncertainty })[k] * r.distance_km))}
        format={v => `${fmt(v, 0)} min`}
        uncertainty="Proxies only: no landslide-susceptibility, live road status or traffic data. Mountain travel is slower than class speeds suggest."
        freshness={`Roads: ${data.explanation.data.roads}. Hazard: ${data.explanation.data.hazard}. Congestion: ${data.explanation.data.congestion}.`}
        provenance={[['Coefficients', Object.entries(data.weights).map(([k, v]) => `${GREEK[k]} ${v}`).join(' · ')]]} />
      <Notes items={data.limitations} />
      <Raw data={{ ...data, shortest_time: { ...s, geometry: `${s.geometry.length} points` }, risk_aware: { ...r, geometry: `${r.geometry.length} points` } }} />
    </>
  );
}

export default function Routing() {
  const meta = useQuery('routing:meta', api.routingMetadata);
  const action = useAction();
  const [last, setLast] = useState(null);
  return (
    <Page title="Risk-aware routing" intro="Compares the fastest road route between two destinations with a route that also weighs hazard exposure, road vulnerability, congestion and data uncertainty, using the cost formula from the project report. Simulate a landslide closure and see how both routes respond.">
      <Query q={meta}>{m => (
        <>
          <Panel title="Plan a route" description={`${m.formula}. Coefficients are extra minutes per km at full intensity. Road network: ${fmt(m.graph.segments, 0)} segments from OpenStreetMap.`}>
            <Form meta={m} loading={action.loading} onRun={body => { setLast(body); action.run(() => api.route(body)); }} />
            <div className="mt-4"><ErrorNotice error={action.error} /></div>
          </Panel>
          {action.data && <Result data={{ ...action.data, request: last }} meta={m} />}
          <Panel title="What each term measures">
            <Table dense columns={['Term', 'Default', 'Proxy used']} rows={Object.entries(m.terms).map(([k, v]) => [`${GREEK[k]} · ${NAMES[k]}`, m.default_weights[k], v])} />
            <p className="mt-3 text-xs text-mist">Road km by class: {Object.entries(m.graph.km_by_class).map(([k, v]) => `${k} ${fmt(v, 0)}`).join(', ')}. {m.graph.source}.</p>
            <Notes items={m.limitations} />
          </Panel>
        </>
      )}</Query>
    </Page>
  );
}
