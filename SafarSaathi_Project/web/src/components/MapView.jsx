import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

/** Leaflet map of NASA POWER source points. points: [{ id, name, lat, lon, elevation }] */
export default function MapView({ points, selected, onSelect, height = 440 }) {
  const el = useRef(null);
  const map = useRef(null);
  const layer = useRef(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!el.current || map.current) return undefined;
    map.current = L.map(el.current, { zoomControl: true, attributionControl: true, scrollWheelZoom: false });
    layer.current = L.layerGroup().addTo(map.current);
    const m = map.current;
    // CARTO basemaps need a free key: put it in /map-config.json (web/dist and web/public) or VITE_CARTO_KEY.
    fetch('/map-config.json', { cache: 'no-store' }).then(r => (r.ok ? r.json() : {})).catch(() => ({}))
      .then(cfg => {
        if (map.current !== m) return;
        const key = (cfg.carto_key || import.meta.env.VITE_CARTO_KEY || '').trim();
        const style = cfg.carto_style || 'dark_all';
        L.tileLayer(`https://basemaps.cartocdn.com/rastertiles/${style}/{z}/{x}/{y}{r}.png${key ? `?key=${encodeURIComponent(key)}` : ''}`, {
          maxZoom: 14,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        }).addTo(m).bringToBack();
      });
    return () => { map.current?.remove(); map.current = null; };
  }, []);

  useEffect(() => {
    if (!map.current || !layer.current) return;
    layer.current.clearLayers();
    points.forEach(p => {
      const active = p.id === selected;
      L.circleMarker([p.lat, p.lon], {
        radius: active ? 9 : 6, weight: active ? 3 : 1.5,
        color: active ? '#ebe7dc' : '#e8bd4f', fillColor: '#e8bd4f', fillOpacity: active ? 0.95 : 0.6,
      }).bindTooltip(`${p.name}${Number.isFinite(p.elevation) ? ` · ${Math.round(p.elevation)} m` : ''}`, { direction: 'top', offset: [0, -6] })
        .on('click', () => onSelectRef.current?.(p.id))
        .on('keypress', () => onSelectRef.current?.(p.id))
        .addTo(layer.current);
    });
    if (points.length && !map.current._fitted) {
      map.current.fitBounds(L.latLngBounds(points.map(p => [p.lat, p.lon])).pad(0.15));
      map.current._fitted = true;
    }
  }, [points, selected]);

  return <div ref={el} style={{ height }} className="w-full overflow-hidden rounded-xl border border-line" aria-label="Map of source locations" />;
}
