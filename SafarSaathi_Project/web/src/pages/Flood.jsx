import React, { useMemo, useRef, useState } from 'react';
import { api, fmt, validateFloodTile } from '../api.js';
import { useAction, useQuery } from '../hooks.js';
import { Button, ErrorNotice, Grid, Notes, Page, Panel, Pill, Raw, Stat } from '../components/ui.jsx';
import { GridImage, RAMPS } from '../components/charts.jsx';

const band = (image, k) => image.map(row => row.map(px => px[k]));

function Figure({ title, children, note }) {
  return (
    <figure className="flex flex-col gap-2">
      {children}
      <figcaption className="text-sm"><span className="text-snow">{title}</span>{note && <span className="block text-xs text-mist">{note}</span>}</figcaption>
    </figure>
  );
}

export default function Flood() {
  const caps = useQuery('capabilities', api.capabilities);
  const [tile, setTile] = useState(null);
  const [source, setSource] = useState('');
  const [inputError, setInputError] = useState(null);
  const fileRef = useRef(null);
  const action = useAction();
  const flood = caps.data?.find(c => c.model_id === 'flood_segmentation_model');

  const accept = (data, label) => {
    try { setTile(validateFloodTile(data)); setSource(label); setInputError(null); action.reset(); }
    catch (e) { setTile(null); setInputError(e); }
  };
  const loadSample = async () => {
    try {
      const response = await fetch('/samples/sturm_flood_tile.json');
      accept(await response.json(), 'STURM-Flood sample tile (CC BY 4.0)');
    } catch { setInputError(new Error('The bundled sample tile could not be loaded.')); }
  };
  const onFile = async e => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 1_000_000) { setInputError(new Error('Tiles must be under 1 MB of JSON, the backend request limit.')); return; }
    try { accept(JSON.parse(await file.text()), file.name); } catch { setInputError(new Error(`${file.name} is not valid JSON.`)); }
    e.target.value = '';
  };
  const run = () => action.run(() => api.segment(tile));
  const vv = useMemo(() => tile && band(tile.image, 0), [tile]);
  const vh = useMemo(() => tile && band(tile.image, 1), [tile]);
  const result = action.data;
  const waterShare = result ? result.mask.flat().reduce((s, v) => s + v, 0) / (128 * 128) : null;
  const crs = tile?.metadata?.geo_tags?.['34737'];

  return (
    <Page title="Flood segmentation" intro="Marks water and flood extent pixel by pixel in a 128 × 128 Sentinel-1 radar tile, using the saved gradient-boosting model trained on the STURM-Flood benchmark. Load the bundled sample or a tile of your own in the same preprocessed format.">
      {flood && (
        <Grid cols={4}>
          <Stat label="Held-out recall" value={fmt(flood.metrics.recall, 2)} note="Share of reference water found" tone="water" />
          <Stat label="Held-out precision" value={fmt(flood.metrics.precision, 2)} note="Many false positives on unseen events" tone="hazard" />
          <Stat label="Held-out IoU" value={fmt(flood.metrics.IoU, 2)} note="Country/event holdout" />
          <Stat label="Decision threshold" value={result ? fmt(result.threshold, 2) : '0.30'} note="Chosen on validation countries" />
        </Grid>
      )}

      <Panel title="1. Choose a tile" description="Input: JSON with image (128 × 128 × 2, VV and VH backscatter, STURM-preprocessed, |value| ≤ 10) and metadata with source_format and optional GeoTIFF tags. Raw Sentinel scenes cannot be uploaded.">
        <div className="flex flex-wrap gap-3">
          <Button onClick={loadSample}>Load sample tile</Button>
          <Button variant="secondary" onClick={() => fileRef.current?.click()}>Upload tile JSON</Button>
          <input ref={fileRef} type="file" accept="application/json,.json" className="hidden" onChange={onFile} />
        </div>
        {inputError && <div className="mt-3"><ErrorNotice error={{ kind: 'invalid', message: inputError.message }} /></div>}
        {tile && (
          <div className="mt-5">
            <p className="mb-3 text-sm text-mist">Loaded <span className="text-snow">{source}</span>{crs ? `, ${String(crs).split('|')[0]}` : ''}.</p>
            <div className="flex flex-wrap gap-6">
              <Figure title="VV backscatter" note="Brighter = stronger return"><GridImage grid={vv} size={220} label="VV band" /></Figure>
              <Figure title="VH backscatter" note="Calm water appears dark"><GridImage grid={vh} size={220} label="VH band" /></Figure>
            </div>
          </div>
        )}
      </Panel>

      <Panel title="2. Segment" tone="water">
        <Button onClick={run} disabled={!tile || action.loading}>{action.loading ? 'Segmenting 16,384 pixels…' : 'Run segmentation'}</Button>
        {!tile && <p className="mt-2 text-sm text-mist">Load a tile first.</p>}
        <div className="mt-4"><ErrorNotice error={action.error} retry={run} /></div>
        {result && (
          <div className="mt-5">
            <div className="mb-4 flex flex-wrap gap-2">
              <Pill tone="warn">Experimental</Pill><Pill>Model {result.model_version}</Pill>
              <Pill tone="info">{fmt(waterShare * 100, 1)}% of pixels flagged as water</Pill>
            </div>
            <div className="flex flex-wrap gap-6">
              <Figure title="Water mask" note={`Pixels with confidence ≥ ${result.threshold}`}><GridImage grid={result.mask} ramp={RAMPS.mask} range={[0, 1]} size={220} label="Predicted water mask" /></Figure>
              <Figure title="Model confidence" note="Uncalibrated score, 0 to 1"><GridImage grid={result.confidence_map} ramp={RAMPS.water} range={[0, 1]} size={220} label="Confidence map" /></Figure>
            </div>
            <p className="mt-4 text-sm text-mist">Class mapping: {typeof result.class_mapping === 'object' && result.class_mapping ? Object.entries(result.class_mapping).map(([k, v]) => `${k} = ${v}`).join('; ') : String(result.class_mapping)}</p>
            <Notes items={result.limitations} />
            <Raw data={{ ...result, mask: `[128 × 128 binary grid]`, confidence_map: `[128 × 128 grid]` }} label="Response metadata" />
          </div>
        )}
      </Panel>
      <p className="text-xs text-mist">Sample tile from STURM-Flood, Notarangelo, N.; WEO SAS (2024), doi:10.5281/zenodo.12748983, CC BY 4.0. No endorsement by the dataset creators is implied.</p>
    </Page>
  );
}
