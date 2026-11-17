import React from 'react';
import { api, bytes } from '../api.js';
import { useQuery } from '../hooks.js';
import { Grid, Notes, Origin, Page, Panel, Pill, Query, Stat, Table } from '../components/ui.jsx';

export default function Satellite() {
  const q = useQuery('satellite', api.satellite);
  return (
    <Page title="Satellite archive" intro="Sentinel-1 radar and Sentinel-2 optical scenes over Uttarakhand held in the project's raw collection. This page catalogues what exists; the flood model works on separately preprocessed benchmark tiles, not on these raw scenes."
      actions={<a href="#/flood" className="rounded-lg border border-line bg-ridge px-4 py-2 text-sm font-semibold text-snow hover:border-gold/60">Open flood segmentation</a>}>
      <Query q={q}>{data => {
        const s1 = data.scenes.filter(s => s.mission === 'sentinel1');
        const s2 = data.scenes.filter(s => s.mission === 'sentinel2');
        const total = data.scenes.reduce((a, s) => a + s.size_bytes, 0);
        const row = s => [
          s.acquisition_from_product_id ? new Date(s.acquisition_from_product_id).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }) + ' UTC' : '—',
          <span className="break-all font-mono text-xs">{s.product_id}</span>, s.files, bytes(s.size_bytes), s.license || '—',
        ];
        return (
          <>
            <Grid cols={4}>
              <Stat label="Scenes" value={data.scenes.length} />
              <Stat label="Sentinel-1 (radar)" value={s1.length} tone="water" />
              <Stat label="Sentinel-2 (optical)" value={s2.length} />
              <Stat label="Archive size" value={bytes(total)} />
            </Grid>
            {[['Sentinel-1 IW GRD scenes', s1, 'Radar sees through monsoon cloud; VV/VH backscatter.'], ['Sentinel-2 L2A tiles', s2, 'Surface reflectance; usable only when cloud-free.']].map(([title, list, desc]) => (
              <Panel key={title} title={title} description={desc} aside={<Origin data={data} />}>
                <Table columns={['Acquired (from product ID)', 'Product', 'Files', 'Size', 'License']} rows={list.map(row)} />
              </Panel>
            ))}
            <div className="flex gap-2"><Pill tone="off">Flood analysis on these scenes: not available</Pill></div>
            <Notes items={data.limitations} />
          </>
        );
      }}</Query>
    </Page>
  );
}
