import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

/** Leaflet map with coloured points, polylines and circles.
 *  points:  [{ id, lat, lon, color, radius, label, ring }]
 *  lines:   [{ coords: [[lat, lon]], color, weight, dashed, label }]
 *  circles: [{ lat, lon, radius_km, color, label }]  */
export default function LayerMap({ points = [], lines = [], circles = [], onSelect, height = 440, fitKey, label = 'Map' }) {
  const el = useRef(null);
  const map = useRef(null);
  const layer = useRef(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const lastFit = useRef(null);

  useEffect(() => {
    if (!el.current || map.current) return undefined;
    map.current = L.map(el.current, { zoomControl: true, scrollWheelZoom: false });
    layer.current = L.layerGroup().addTo(map.current);
    const m = map.current;
    fetch('/map-config.json', { cache: 'no-store' }).then(r => (r.ok ? r.json() : {})).catch(() => ({}))
      .then(cfg => {
        if (map.current !== m) return;
        const key = (cfg.carto_key || import.meta.env.VITE_CARTO_KEY || '').trim();
        L.tileLayer(`https://basemaps.cartocdn.com/rastertiles/${cfg.carto_style || 'dark_all'}/{z}/{x}/{y}{r}.png${key ? `?key=${encodeURIComponent(key)}` : ''}`,
          { maxZoom: 14, attribution: ATTRIBUTION }).addTo(m).bringToBack();
      });
    m.setView([30.1, 79.0], 7);
    return () => { map.current?.remove(); map.current = null; };
  }, []);

  useEffect(() => {
    const m = map.current; const g = layer.current;
    if (!m || !g) return;
    g.clearLayers();
    circles.forEach(c => L.circle([c.lat, c.lon], { radius: c.radius_km * 1000, color: c.color || '#e5765f', weight: 1.5, fillOpacity: 0.15, dashArray: '4 4' })
      .bindTooltip(c.label || 'Closure').addTo(g));
    lines.forEach(l => l.coords?.length && L.polyline(l.coords, { color: l.color, weight: l.weight || 4, opacity: 0.9, dashArray: l.dashed ? '8 8' : null })
      .bindTooltip(l.label || '').addTo(g));
    points.forEach(p => {
      L.circleMarker([p.lat, p.lon], { radius: p.radius || 7, weight: p.ring ? 3 : 1.5, color: p.ring ? '#ebe7dc' : p.color, fillColor: p.color, fillOpacity: 0.85 })
        .bindTooltip(p.label || p.id, { direction: 'top', offset: [0, -6] })
        .on('click', () => onSelectRef.current?.(p.id))
        .addTo(g);
    });
    const key = fitKey ?? 'default';
    if (lastFit.current !== key) {
      const pts = lines.flatMap(l => l.coords || []);
      const all = pts.length ? pts : points.map(p => [p.lat, p.lon]);
      if (all.length) { m.fitBounds(L.latLngBounds(all).pad(0.12)); lastFit.current = key; }
    }
  }, [points, lines, circles, fitKey]);

  return <div ref={el} style={{ height }} className="w-full overflow-hidden rounded-xl border border-line" aria-label={label} />;
}
