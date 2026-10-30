import React, { useState } from 'react';
import { api } from '../services/api/resources.js';
import { useApiQuery } from '../hooks/useApi.js';
import ApiState, { Limitations } from '../components/ApiState.jsx';
import SourceLocationOverlay from '../components/SourceLocationOverlay.jsx';

export default function DestinationDigitalTwin({ onNavigate, showToast }) {
  const query = useApiQuery('twin-sources', () => Promise.all([api.destinations(), api.layers()]).then(([locations, layers]) => ({ locations, layers })));
  const [selectedId, setSelectedId] = useState('rishikesh');
  const sectors = (query.data?.locations.destinations || []).map(location => ({
    ...location, sub: `${location.source} · static grid point`, status: 'ARCHIVED',
    pax: location.coverage_start, cap: location.coverage_end,
    density: `Lon ${location.geometry.coordinates[0]} · Lat ${location.geometry.coordinates[1]}`,
    hotel: String(location.geometry.coordinates[0]), water: String(location.geometry.coordinates[1]),
    power: location.coverage_start,
  }));
  const activeSector = sectors.find(s => s.id === selectedId) || sectors[0] || {
    id: '', name: query.loading ? 'Loading source metadata…' : 'DATA UNAVAILABLE',
    pax: '—', cap: '—', hotel: '—', water: '—', power: '—', density: '—',
  };
  const setActiveSector = sector => setSelectedId(sector.id);
  const [activeLayers, setActiveLayers] = useState({
    topo: true,
    bts: true,
    hydro: true,
    fleet: false,
  });
  const [throttleVal, setThrottleVal] = useState(15); // 15% reduction

  const toggleLayer = (key) => {
    setActiveLayers(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const applyIngressThrottle = () => {
    showToast({
      title: 'Demo control — no gate service',
      message: `Selected throttle ${throttleVal}% is local demo context only. No barrier or dispatch command was transmitted.`,
      type: 'success',
    });
  };

  return (
    <div data-page="destination-twin" className="flex flex-col w-full bg-surface text-on-surface">
      {/* Header Bar */}
      <div className="px-gutter-lg pt-space-md pb-space-sm flex flex-col md:flex-row md:items-center justify-between gap-space-sm border-b border-white/5">
        <div className="flex items-center gap-space-sm flex-wrap">
          <div className="flex items-center gap-space-xs px-2 py-0.5 rounded bg-surface-container-high text-primary font-telemetry-sm text-telemetry-sm tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
            <span>STATIC LOCATIONS // DEMO SCHEMATIC</span>
          </div>
          <span className="text-on-surface-variant font-telemetry-sm text-telemetry-sm tracking-widest text-xs">
            // NO LIVE GPS, IOT OR SATELLITE SYNC
          </span>
        </div>

        {/* Multi-Layer Toggles */}
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="text-slate-400 text-xs hidden sm:inline">LAYERS:</span>
          {[
            { key: 'topo', label: 'Topography' },
            { key: 'bts', label: 'Cellular BTS' },
            { key: 'hydro', label: 'Hydrology' },
            { key: 'fleet', label: 'Transit Fleet' },
          ].map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => toggleLayer(key)}
              className={`px-2.5 py-1 rounded transition-all border ${
                activeLayers[key]
                  ? 'bg-primary/20 text-primary border-primary/50 shadow-[0_0_10px_rgba(212,175,55,0.25)] font-bold'
                  : 'bg-surface-container text-slate-400 border-white/5 hover:text-white'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="px-gutter-lg py-2"><ApiState {...query} /><Limitations items={query.data?.layers.limitations || []} /></div>
      {/* Main Workspace: Left Sector Rail + Center 3D Vector Map + Right Intelligence Panel */}
      <div className="px-gutter-lg py-space-md pb-12">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-md">
          
          {/* Left Rail: 3 Cols - Sectors */}
          <div className="lg:col-span-3 flex flex-col gap-2 max-h-[720px] overflow-y-auto">
            <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-xs mb-1">
              ARCHIVED SOURCE LOCATIONS
            </span>

            {sectors.map((sector) => {
              const isSelected = activeSector.id === sector.id;
              const isCritical = sector.status === 'CRITICAL';
              const isSaturated = sector.status === 'SATURATED';

              return (
                <div
                  key={sector.id}
                  onClick={() => setActiveSector(sector)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer flex flex-col gap-1.5 ${
                    isSelected
                      ? 'bg-surface-container-highest border-[#d4af37] shadow-[0_0_20px_rgba(212,175,55,0.2)]'
                      : 'bg-surface-container border-white/5 hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className={`text-xs font-bold ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                      {sector.name}
                    </span>
                    <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded font-bold uppercase ${
                      isCritical
                        ? 'bg-red-950 text-red-400 border border-red-500/40'
                        : isSaturated
                        ? 'bg-amber-950 text-amber-400 border border-amber-500/40'
                        : 'bg-emerald-950 text-emerald-400 border border-emerald-500/40'
                    }`}>
                      {sector.status}
                    </span>
                  </div>

                  <p className="text-[10px] text-slate-400 leading-tight">{sector.sub}</p>

                  <div className="mt-1 flex items-center justify-between font-mono text-[10px] pt-1 border-t border-white/5">
                    <span className="text-slate-400">{sector.pax} – {sector.cap}</span>
                    <span className="text-primary font-semibold">{sector.density}</span>
                  </div>
                </div>
              );
            })}

            {/* Quick Stats Pill */}
            <div className="mt-2 p-3 rounded-lg bg-surface-container-low border border-white/5 text-[10px] font-mono text-slate-400 flex flex-col gap-1">
              <div>SOURCE: NASA POWER ARCHIVED REANALYSIS</div>
              <div>CRS: SOURCE DOES NOT DECLARE EPSG</div>
              <div>ROADS / SENSORS / CONTOURS: DEMO DATA</div>
            </div>
          </div>

          {/* Center 3D Vector Digital Twin: 6 Cols */}
          <div className="lg:col-span-6 flex flex-col bg-[#07090e] rounded-xl border border-[#d4af37]/25 overflow-hidden shadow-2xl relative">
            
            {/* Viewport Header */}
            <div className="p-space-sm bg-surface-container-low border-b border-white/5 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px] text-primary">view_in_ar</span>
                <span className="text-xs font-bold text-white uppercase font-mono">
                  STATIC SOURCE // {activeSector.name}
                </span>
              </div>
              <span className="text-[10px] font-mono text-slate-400">
                DEMO SCHEMATIC + SOURCE INSET
              </span>
            </div>

            {/* Topographic 3D SVG Canvas */}
            <div className="relative w-full h-[520px] subtle-grid overflow-hidden">
              <svg 
                className="absolute inset-0 w-full h-full" 
                preserveAspectRatio="none" 
                viewBox="0 0 1000 700" 
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  <radialGradient id="chokeGlow" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#f2ca50" stopOpacity="0.8" />
                    <stop offset="100%" stopColor="#f2ca50" stopOpacity="0" />
                  </radialGradient>
                  
                  <linearGradient id="slopeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#d4af37" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="#080a0f" stopOpacity="0.8" />
                  </linearGradient>
                </defs>

                {/* Topographic Elevation Contour Lines */}
                {activeLayers.topo && (
                  <g stroke="#d4af37" strokeOpacity="0.2" fill="none" strokeWidth="1.2">
                    <path d="M 50 650 Q 250 500 500 550 T 950 500" />
                    <path d="M 70 580 Q 270 430 520 480 T 930 430" />
                    <path d="M 100 510 Q 300 360 550 410 T 900 360" />
                    <path d="M 140 440 Q 340 290 590 340 T 870 290" />
                    <path d="M 190 370 Q 390 220 640 270 T 830 220" />
                    <path d="M 250 300 Q 450 150 700 200 T 800 150" />
                  </g>
                )}

                {/* Hydrologic River Zone */}
                {activeLayers.hydro && (
                  <path
                    d="M 120 700 Q 300 520 450 480 T 650 380 T 900 300"
                    fill="none"
                    stroke="#0284c7"
                    strokeWidth="32"
                    strokeOpacity="0.45"
                    strokeLinecap="round"
                  />
                )}

                {/* Pedestrian Chokepoint Heatmap Area */}
                <ellipse cx="480" cy="420" rx="140" ry="70" fill="url(#chokeGlow)" opacity="0.6" />

                {/* Ingress Road Artery */}
                <path
                  d="M 80 620 Q 320 480 480 420 T 820 280"
                  fill="none"
                  stroke="#f2ca50"
                  strokeWidth="4"
                  strokeLinecap="round"
                />

                {/* Active Cellular BTS Towers */}
                {activeLayers.bts && (
                  <g>
                    <circle cx="340" cy="460" r="4" fill="#38bdf8" />
                    <circle cx="340" cy="460" r="14" fill="none" stroke="#38bdf8" strokeWidth="0.8" strokeDasharray="3 3" />
                    <text x="320" y="490" fill="#38bdf8" fontSize="10" fontFamily="JetBrains Mono">BTS-01 (94% LOAD)</text>

                    <circle cx="620" cy="380" r="4" fill="#38bdf8" />
                    <circle cx="620" cy="380" r="14" fill="none" stroke="#38bdf8" strokeWidth="0.8" strokeDasharray="3 3" />
                    <text x="600" y="410" fill="#38bdf8" fontSize="10" fontFamily="JetBrains Mono">BTS-02 (78% LOAD)</text>
                  </g>
                )}

                {/* Transit Fleet GPS Vectors */}
                {activeLayers.fleet && (
                  <g>
                    <rect x="390" y="440" width="8" height="14" rx="2" fill="#10b981" />
                    <rect x="520" y="390" width="8" height="14" rx="2" fill="#10b981" />
                    <text x="360" y="435" fill="#10b981" fontSize="9" fontFamily="JetBrains Mono">EVAC BUS 04</text>
                  </g>
                )}

                {/* Focal Pin for Active Sector */}
                <g transform="translate(480, 420)">
                  <circle cx="0" cy="0" r="8" fill="#ffd700" className="animate-ping" opacity="0.7" />
                  <circle cx="0" cy="0" r="6" fill="#f2ca50" />
                  <circle cx="0" cy="0" r="2" fill="#080a0f" />
                </g>
                <SourceLocationOverlay features={query.data?.layers.features || []} selected={activeSector.id} onSelect={setSelectedId} />
              </svg>

              {/* Viewport Floating Info */}
              <div className="absolute top-4 left-4 z-20 bg-surface-container-lowest/90 border border-white/10 rounded px-2.5 py-1 font-mono text-[10px] text-slate-300 backdrop-blur-md">
                <span>DEMO TERRAIN</span> | <span className="text-primary font-bold">{activeSector.name}</span>
              </div>
            </div>

            {/* Viewport Status Footer */}
            <div className="p-space-sm bg-surface-container-low border-t border-white/5 flex items-center justify-between text-xs font-mono text-slate-400">
              <span>STATIC ARCHIVE · NO LIVE SYNC</span>
              <button 
                type="button" 
                onClick={() => onNavigate('what-if-simulator')}
                className="text-primary hover:underline flex items-center gap-1"
              >
                <span>Run Scenario Simulator</span>
                <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
              </button>
            </div>
          </div>

          {/* Right Panel: 3 Cols - Deep Sector Telemetry & Ingress Throttle */}
          <div className="lg:col-span-3 flex flex-col gap-space-md">
            
            {/* Sector Deep Telemetry */}
            <div className="bg-surface-container-lowest rounded-xl border border-[#d4af37]/25 p-space-md shadow-xl flex flex-col gap-3">
              <div className="flex items-center justify-between border-b border-white/5 pb-2">
                <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-xs font-bold">
                  SOURCE METADATA
                </span>
                <span className="text-[9px] font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                  ARCHIVED
                </span>
              </div>

              {/* Carrying Capacity Gauge */}
              <div>
                <div className="flex justify-between text-xs font-mono mb-1">
                  <span className="text-slate-400">Source coverage:</span>
                  <span className="text-white font-bold">{activeSector.pax} / {activeSector.cap}</span>
                </div>
                <div className="w-full bg-surface-container-highest h-2 rounded overflow-hidden">
                  <div 
                    className="bg-primary h-full rounded transition-all duration-300"
                    style={{ width: '0%' }}
                  ></div>
                </div>
              </div>

              {/* Resource Reserves */}
              <div className="grid grid-cols-2 gap-2 font-mono text-xs pt-1">
                <div className="bg-surface-container p-2 rounded">
                  <span className="text-[9px] text-slate-400 block">LONGITUDE</span>
                  <span className="text-primary font-bold text-sm">{activeSector.hotel}</span>
                </div>
                <div className="bg-surface-container p-2 rounded">
                  <span className="text-[9px] text-slate-400 block">LATITUDE</span>
                  <span className="text-emerald-400 font-bold text-sm">{activeSector.water}</span>
                </div>
                <div className="bg-surface-container p-2 rounded">
                  <span className="text-[9px] text-slate-400 block">COVERAGE START</span>
                  <span className="text-amber-400 font-bold text-sm">{activeSector.power}</span>
                </div>
                <div className="bg-surface-container p-2 rounded">
                  <span className="text-[9px] text-slate-400 block">QUERY LOCATION</span>
                  <span className="text-primary font-bold text-sm">{activeSector.query_coordinates ? `${activeSector.query_coordinates.longitude}, ${activeSector.query_coordinates.latitude}` : '—'}</span>
                </div>
              </div>
            </div>

            {/* Ingress Throttle Control */}
            <div className="bg-surface-container-lowest rounded-xl border border-[#d4af37]/25 p-space-md shadow-xl flex flex-col gap-3">
              <span className="font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider text-xs font-bold">
                DEMO INGRESS THROTTLE
              </span>
              <p className="text-[11px] text-slate-400">
                Demonstration control only. Visitor capacity, live infrastructure and gate dispatch are unavailable.
              </p>

              <div>
                <div className="flex justify-between text-xs font-mono mb-1.5">
                  <span className="text-slate-400">Throttle Ingress:</span>
                  <span className="text-primary font-bold">-{throttleVal}%</span>
                </div>
                <input 
                  type="range" 
                  min="0" 
                  max="50" 
                  value={throttleVal}
                  onChange={(e) => setThrottleVal(Number(e.target.value))}
                  className="w-full accent-primary bg-surface-container-highest cursor-pointer h-1.5 rounded"
                />
              </div>

              <button
                type="button"
                onClick={applyIngressThrottle}
                className="w-full mt-1 py-2 rounded bg-primary/20 border border-primary/50 text-primary hover:bg-primary hover:text-on-primary transition-all font-mono text-xs font-bold"
              >
                Preview Demo Gate Protocol
              </button>
            </div>

          </div>

        </div>
      </div>
    </div>
  );
}
