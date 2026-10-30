import React from 'react';
import { projectLocations } from '../services/api/adapters.js';

export default function SourceLocationOverlay({ features, selected, onSelect }) {
  const points = projectLocations(features, 400, 260);
  if (!points.length) return null;
  const xs = points.map(p => p.geometry.coordinates[0]), ys = points.map(p => p.geometry.coordinates[1]);
  return <svg x="20" y="20" width="460" height="300" viewBox="0 0 400 260" aria-label="Static NASA POWER source coordinate inset">
    <rect x="0" y="0" width="400" height="260" rx="10" fill="#080a0f" fillOpacity="0.96" stroke="#d4af37" strokeOpacity="0.5" />
    <text x="12" y="20" fill="#f2ca50" fontSize="10">STATIC SOURCE COORDINATES · INDEPENDENT FRAME</text>
    <text x="12" y="34" fill="#aab2c0" fontSize="8">Not registered to the demonstration roads / contours beneath</text>
    {points.map(p => <g key={p.id} role="button" tabIndex="0" aria-label={`Select source ${p.properties.name}`}
      onClick={() => onSelect(p.id)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(p.id); } }} style={{ cursor: 'pointer' }}>
      <title>{p.properties.name}: longitude {p.geometry.coordinates[0]}, latitude {p.geometry.coordinates[1]}</title>
      <circle cx={p.x} cy={p.y} r={selected === p.id ? 6 : 3} fill={selected === p.id ? '#ffe088' : '#d4af37'} />
    </g>)}
    <text x="10" y="250" fill="#aab2c0" fontSize="8">LON {Math.min(...xs).toFixed(3)}–{Math.max(...xs).toFixed(3)} · LAT {Math.min(...ys).toFixed(3)}–{Math.max(...ys).toFixed(3)} · ↑ N</text>
  </svg>;
}
